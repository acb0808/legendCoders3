# backend/routers/arena.py
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from ..discord_bot.bot import notify_new_arena
from fastapi.encoders import jsonable_encoder 
import json # Added this
import uuid
from sqlalchemy.orm import Session, joinedload
from typing import List
from .. import models, schemas, crud
from ..database import get_db, SessionLocal # Added SessionLocal
from ..auth import get_current_user, get_user_from_token # Added get_user_from_token
from ..services import arena_service as service # Use alias to avoid conflict
import uuid
from typing import Optional, Any # Added Any
from fastapi import Query # Added Query
from starlette import status # Import status from starlette
from starlette.websockets import WebSocket, WebSocketDisconnect
from ..websockets.manager import manager # Import globally
from ..services.arena_ws_service import ArenaWsService

router = APIRouter(
    prefix="/api/arena",
    tags=["arena"]
)

@router.websocket("/{arena_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    arena_id: uuid.UUID,
    token: Optional[str] = Query(None)
):
    # 1. Immediate Accept to finish handshake and allow error reporting
    await websocket.accept()
    
    ws_service = ArenaWsService()
    current_user_id = None

    # 2. Setup & Auth with robust error handling
    try:
        with SessionLocal() as db:
            if not token:
                await websocket.send_text(json.dumps({"type": "ERROR", "payload": "인증 정보가 필요합니다."}))
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            current_user = get_user_from_token(token, db)
            if not current_user:
                await websocket.send_text(json.dumps({"type": "ERROR", "payload": "인증에 실패했습니다."}))
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            current_user_id = current_user.id

            arena = db.query(models.Arena).filter(models.Arena.id == arena_id).first()
            if not arena:
                await websocket.send_text(json.dumps({"type": "ERROR", "payload": "존재하지 않는 경기장입니다."}))
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            if current_user_id != arena.host_id and current_user_id != arena.guest_id:
                await websocket.send_text(json.dumps({"type": "ERROR", "payload": "권한이 없습니다."}))
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

        # 3. Join Room
        await manager.connect(str(arena_id), websocket)
        await ws_service._broadcast_arena_state(arena_id)

        # 4. Main Message Loop
        while True:
            data = await websocket.receive_text()
            await ws_service.handle_message(arena_id, current_user_id, data)

    except WebSocketDisconnect:
        manager.disconnect(str(arena_id), websocket)
        await ws_service.handle_disconnect(arena_id, current_user_id)
    except Exception as e:
        print(f"CRITICAL WS ERROR [Arena:{arena_id}]: {e}")
        try:
            # Try to inform the client before closing
            await websocket.send_text(json.dumps({"type": "ERROR", "payload": "연결 중 오류가 발생했습니다."}))
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
        manager.disconnect(str(arena_id), websocket)


@router.post("/", response_model=schemas.ArenaResponse)
def create_arena(
    arena: schemas.ArenaCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Enforce single room policy
    active_arena = crud.arena.get_active_arena_by_user(db, current_user.id)
    if active_arena:
        raise HTTPException(
            status_code=400,
            detail=f"User is already in an active arena ({active_arena.id}). Redirect to /arena/{active_arena.id}"
        )

    # Host creates arena
    created_arena = crud.arena.create_arena(db, arena, current_user.id)
    # Eager load relationships for response model
    db.refresh(created_arena, attribute_names=['host'])
    
    # Notify Discord if public
    if created_arena.mode == "OPEN":
        background_tasks.add_task(notify_new_arena, created_arena)
        
    return created_arena

@router.get("/", response_model=List[schemas.ArenaResponse])
def get_open_arenas(
    skip: int = 0, 
    limit: int = 20, 
    db: Session = Depends(get_db)
):
    arenas = db.query(models.Arena).options(joinedload(models.Arena.host), joinedload(models.Arena.guest)).filter(
        models.Arena.status == "WAITING",
        models.Arena.guest_id == None,
        models.Arena.mode == "OPEN" # Only list OPEN arenas
    ).order_by(models.Arena.created_at.desc()).offset(skip).limit(limit).all()
    return arenas

@router.get("/active", response_model=Optional[schemas.ArenaResponse])
def get_user_active_arena(
    current_user: models.User = Depends(get_current_user)
):
    # Use a fresh session to avoid stale data from the request-scoped dependency
    with SessionLocal() as db:
        active_arena = db.query(models.Arena).options(
            joinedload(models.Arena.host), 
            joinedload(models.Arena.guest), 
            joinedload(models.Arena.winner)
        ).filter(
            (models.Arena.host_id == current_user.id) | (models.Arena.guest_id == current_user.id),
            models.Arena.status.in_(["WAITING", "READY", "PLAYING"])
        ).first()

        if active_arena:
            # Important: We must load the data before the session closes
            # Since we are using schemas.ArenaResponse, FastAPI will handle serialization
            # but we need to ensure the relationships are available.
            return jsonable_encoder(active_arena)
    return None

@router.get("/{arena_id}", response_model=schemas.ArenaResponse)
def get_arena(
    arena_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    arena = db.query(models.Arena).options(joinedload(models.Arena.host), joinedload(models.Arena.guest), joinedload(models.Arena.winner)).filter(models.Arena.id == arena_id).first()
    if not arena: raise HTTPException(status_code=404, detail="Arena not found")
    
    return arena

@router.post("/{arena_id}/join", response_model=schemas.ArenaResponse)
def join_arena(
    arena_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if user is already in an active arena
    active_arena = crud.arena.get_active_arena_by_user(db, current_user.id)
    if active_arena and active_arena.id != arena_id:
        raise HTTPException(
            status_code=400,
            detail=f"User is already in an active arena ({active_arena.id})"
        )

    arena = crud.arena.join_arena(db, arena_id, current_user.id)
    if not arena:
        raise HTTPException(status_code=404, detail="Arena not found or already full")
    
    # Eager load for response
    return db.query(models.Arena).options(
        joinedload(models.Arena.host), 
        joinedload(models.Arena.guest)
    ).filter(models.Arena.id == arena_id).first()

@router.post("/{arena_id}/submit")
async def check_submission(
    arena_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    success, message = service.verify_and_end_match(db, arena_id, current_user.id)
    
    if success:
        # Broadcast the winner to everyone
        ws_service = ArenaWsService()
        await ws_service._broadcast_arena_state(arena_id)
        await manager.broadcast_to_room(
            str(arena_id), 
            json.dumps({
                "type": "GAME_OVER", 
                "payload": {
                    "winner_id": str(current_user.id), 
                    "reason": "문제 해결!"
                }
            })
        )
        return {"success": True, "message": message}
    
    return {"success": False, "message": message}
