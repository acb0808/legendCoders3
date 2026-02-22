from sqlalchemy.orm import Session, joinedload
from fastapi.encoders import jsonable_encoder
import json
import uuid
import asyncio

from .. import models, crud, schemas
from ..websockets.manager import manager
from ..services.arena_service import find_fair_problem_id
from ..crud.stats import get_kst_now
from ..database import SessionLocal

class ArenaWsService:
    def __init__(self):
        pass

    async def _broadcast_arena_state(self, arena_id: uuid.UUID):
        arena_data = None
        with SessionLocal() as db:
            arena = db.query(models.Arena).options(
                joinedload(models.Arena.host),
                joinedload(models.Arena.guest),
                joinedload(models.Arena.winner)
            ).filter(models.Arena.id == arena_id).first()

            if arena:
                try:
                    arena_data = jsonable_encoder(schemas.ArenaResponse.from_orm(arena))
                except Exception as e:
                    print(f"Error encoding arena state: {e}")
        
        if arena_data:
            await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "ARENA_STATE", "payload": arena_data}))

    async def handle_message(self, arena_id: uuid.UUID, user_id: uuid.UUID, message_json: str):
        try:
            message = json.loads(message_json)
            msg_type = message.get("type")
            payload = message.get("payload") or {}

            if msg_type == "CHAT":
                chat_payload = None
                with SessionLocal() as db:
                    user = db.query(models.User).options(joinedload(models.User.equipped_title)).filter(models.User.id == user_id).first()
                    if user:
                        chat_payload = {
                            "sender_id": str(user_id),
                            "sender_nickname": user.nickname,
                            "sender_title": user.equipped_title.name if user.equipped_title else None,
                            "content": payload.get("content"),
                            "timestamp": get_kst_now().isoformat()
                        }
                if chat_payload:
                    await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "CHAT", "payload": chat_payload}))

            elif msg_type == "READY_TOGGLE":
                should_start = False
                with SessionLocal() as db:
                    arena = db.query(models.Arena).options(joinedload(models.Arena.host), joinedload(models.Arena.guest)).filter(models.Arena.id == arena_id).first()
                    if not arena or not arena.guest_id: return
                    
                    if arena.host_id == user_id:
                        arena.host_ready = not arena.host_ready
                    elif arena.guest_id == user_id:
                        arena.guest_ready = not arena.guest_ready
                    
                    db.commit()
                    
                    if arena.host_ready and arena.guest_ready and (arena.status == "WAITING" or arena.status == "READY"):
                        should_start = True
                
                await self._broadcast_arena_state(arena_id)

                if should_start:
                    # 1. Countdown Phase
                    for i in [3, 2, 1]:
                        await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "COUNTDOWN", "payload": i}))
                        await asyncio.sleep(1)

                    # 2. Problem Selection Phase
                    problem_id = None
                    with SessionLocal() as db:
                        arena = db.query(models.Arena).options(joinedload(models.Arena.host), joinedload(models.Arena.guest)).filter(models.Arena.id == arena_id).first()
                        if arena and arena.status in ["WAITING", "READY"]:
                            # Fetch a fair problem now
                            print(f"[Arena] Finding fair problem for {arena.host.baekjoon_id} vs {arena.guest.baekjoon_id}")
                            problem_id = find_fair_problem_id(arena.host.baekjoon_id, arena.guest.baekjoon_id, arena.difficulty)
                            
                            if problem_id:
                                arena.baekjoon_problem_id = problem_id
                                arena.status = "PLAYING"
                                arena.start_time = get_kst_now()
                                db.commit()
                            else:
                                print("[Arena] Failed to find a fair problem!")
                    
                    if problem_id:
                        await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "GAME_START", "payload": {"problem_id": problem_id}}))
                        await self._broadcast_arena_state(arena_id)
                    else:
                        await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "ERROR", "payload": "적절한 문제를 찾지 못했습니다. 다시 시도해 주세요."}))
                        # Reset ready states on failure
                        with SessionLocal() as db:
                            arena = db.query(models.Arena).filter(models.Arena.id == arena_id).first()
                            if arena:
                                arena.host_ready = False
                                arena.guest_ready = False
                                db.commit()
                        await self._broadcast_arena_state(arena_id)

            elif msg_type == "SURRENDER":
                winner_id = None
                with SessionLocal() as db:
                    arena = db.query(models.Arena).filter(models.Arena.id == arena_id).first()
                    if arena and arena.status == "PLAYING":
                        winner_id = arena.guest_id if arena.host_id == user_id else arena.host_id
                        if winner_id:
                            arena.winner_id = winner_id
                            arena.status = "FINISHED"
                            arena.end_time = get_kst_now()
                            db.commit()
                
                if winner_id:
                    await self._broadcast_arena_state(arena_id)
                    await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "GAME_OVER", "payload": {"winner_id": str(winner_id), "reason": "항복"}}))

            elif msg_type == "PROPOSE_DRAW":
                game_ended = False
                with SessionLocal() as db:
                    arena = db.query(models.Arena).filter(models.Arena.id == arena_id).first()
                    if arena and arena.status == "PLAYING":
                        if arena.host_id == user_id: arena.host_draw_agreed = True
                        if arena.guest_id == user_id: arena.guest_draw_agreed = True
                        
                        if arena.host_draw_agreed and arena.guest_draw_agreed:
                            arena.status = "FINISHED"
                            arena.winner_id = None
                            arena.end_time = get_kst_now()
                            game_ended = True
                        db.commit()
                
                await self._broadcast_arena_state(arena_id)
                if game_ended:
                    await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "GAME_OVER", "payload": {"winner_id": None, "reason": "상호 합의하에 무승부로 종료되었습니다."}}))
                else:
                    await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "DRAW_PROPOSED", "payload": {"proposer_id": str(user_id)}}))

            elif msg_type == "PROPOSE_SKIP":
                problem_changed = False
                new_problem_id = None
                with SessionLocal() as db:
                    arena = db.query(models.Arena).options(joinedload(models.Arena.host), joinedload(models.Arena.guest)).filter(models.Arena.id == arena_id).first()
                    if arena and arena.status == "PLAYING":
                        if arena.host_id == user_id: arena.host_skip_agreed = True
                        if arena.guest_id == user_id: arena.guest_skip_agreed = True
                        
                        if arena.host_skip_agreed and arena.guest_skip_agreed:
                            new_id = find_fair_problem_id(arena.host.baekjoon_id, arena.guest.baekjoon_id, arena.difficulty)
                            if new_id:
                                arena.baekjoon_problem_id = new_id
                                arena.host_skip_agreed = False
                                arena.guest_skip_agreed = False
                                arena.host_draw_agreed = False
                                arena.guest_draw_agreed = False
                                arena.start_time = get_kst_now()
                                new_problem_id = new_id
                                problem_changed = True
                        db.commit()
                
                await self._broadcast_arena_state(arena_id)
                if problem_changed:
                    await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "PROBLEM_CHANGED", "payload": {"problem_id": new_problem_id}}))
                else:
                    await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "SKIP_PROPOSED", "payload": {"proposer_id": str(user_id)}}))

            elif msg_type == "LEAVE_ARENA":
                with SessionLocal() as db:
                    arena = db.query(models.Arena).filter(models.Arena.id == arena_id).first()
                    if arena:
                        if arena.status in ["WAITING", "READY"]:
                            if arena.host_id == user_id:
                                arena.status = "CANCELLED"
                            elif arena.guest_id == user_id:
                                arena.guest_id = None
                                arena.guest_ready = False
                                arena.status = "WAITING"
                            db.commit()
                
                await self._broadcast_arena_state(arena_id)
                await manager.broadcast_to_room(str(arena_id), json.dumps({"type": "GUEST_LEFT", "payload": {"reason": "상대방이 퇴장했습니다."}}))

        except Exception as e:
            print(f"ArenaWsService Error in handle_message: {e}")

    async def handle_disconnect(self, arena_id: uuid.UUID, user_id: uuid.UUID):
        try:
            with SessionLocal() as db:
                arena = db.query(models.Arena).filter(models.Arena.id == arena_id).first()
                if not arena: return

                if arena.status in ["WAITING", "READY"]:
                    return
                
                elif arena.status == "PLAYING":
                    winner_id = arena.guest_id if arena.host_id == user_id else arena.host_id
                    if winner_id:
                        arena.winner_id = winner_id
                        arena.status = "FINISHED"
                        arena.end_time = get_kst_now()
                        db.commit()
            
            await self._broadcast_arena_state(arena_id)
        except Exception as e:
            print(f"ArenaWsService Error in handle_disconnect: {e}")
