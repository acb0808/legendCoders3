# backend/crud/arena.py
from sqlalchemy.orm import Session
from .. import models, schemas
import uuid
from datetime import datetime
import pytz

def get_kst_now():
    return datetime.now(pytz.timezone('Asia/Seoul'))

def create_arena(db: Session, arena: schemas.ArenaCreate, host_id: uuid.UUID):
    db_arena = models.Arena(
        host_id=host_id,
        difficulty=arena.difficulty,
        status="WAITING",
        created_at=get_kst_now()
    )
    db.add(db_arena)
    db.commit()
    db.refresh(db_arena)
    return db_arena

def get_arena(db: Session, arena_id: uuid.UUID):
    return db.query(models.Arena).filter(models.Arena.id == arena_id).first()

def get_open_arenas(db: Session, skip: int = 0, limit: int = 20):
    return db.query(models.Arena).filter(
        models.Arena.status == "WAITING",
        models.Arena.guest_id == None
    ).order_by(models.Arena.created_at.desc()).offset(skip).limit(limit).all()

def join_arena(db: Session, arena_id: uuid.UUID, guest_id: uuid.UUID):
    arena = get_arena(db, arena_id)
    if not arena: return None
    # If user is already the guest, just return the arena
    if arena.guest_id == guest_id:
        return arena
    if arena.status != "WAITING": return None
    if arena.host_id == guest_id: return None # Cannot join own arena
    
    arena.guest_id = guest_id
    arena.status = "READY"
    db.commit()
    db.refresh(arena)
    return arena

def start_arena(db: Session, arena_id: uuid.UUID, problem_id: int):
    arena = get_arena(db, arena_id)
    if not arena: return None
    
    arena.baekjoon_problem_id = problem_id
    arena.status = "PLAYING"
    arena.start_time = get_kst_now()
    db.commit()
    db.refresh(arena)
    return arena

def finish_arena(db: Session, arena_id: uuid.UUID, winner_id: uuid.UUID):
    arena = get_arena(db, arena_id)
    if not arena: return None
    
    arena.winner_id = winner_id
    arena.status = "FINISHED"
    arena.end_time = get_kst_now()
    db.commit()
    db.refresh(arena)
    return arena

def get_active_arena_by_user(db: Session, user_id: uuid.UUID):
    return db.query(models.Arena).filter(
        (models.Arena.host_id == user_id) | (models.Arena.guest_id == user_id),
        models.Arena.status.in_(["WAITING", "READY", "PLAYING"])
    ).first()
