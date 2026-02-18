# backend/crud.py
import uuid
from sqlalchemy.orm import Session
from . import models, schemas
from .auth import get_password_hash # get_password_hash는 auth.py에서 가져옴

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_nickname(db: Session, nickname: str):
    return db.query(models.User).filter(models.User.nickname == nickname).first()

def get_user(db: Session, user_id: uuid.UUID):
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        password_hash=hashed_password,
        nickname=user.nickname,
        baekjoon_id=user.baekjoon_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
