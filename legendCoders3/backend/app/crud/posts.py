# backend/app/crud/posts.py
import uuid
from sqlalchemy.orm import Session
from .. import models, schemas
from datetime import datetime

from sqlalchemy import desc # desc 임포트 추가

def get_posts_by_problem(db: Session, daily_problem_id: uuid.UUID):
    # 최신순으로 정렬하여 반환
    return db.query(models.Post)\
             .filter(models.Post.daily_problem_id == daily_problem_id)\
             .order_by(desc(models.Post.created_at))\
             .all()

def get_post(db: Session, post_id: uuid.UUID):
    return db.query(models.Post).filter(models.Post.id == post_id).first()

def create_post(db: Session, user_id: uuid.UUID, post: schemas.PostCreate):
    db_post = models.Post(
        user_id=user_id,
        daily_problem_id=post.daily_problem_id,
        title=post.title,
        content=post.content,
        tags=post.tags
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

def increment_view_count(db: Session, post_id: uuid.UUID):
    db_post = get_post(db, post_id)
    if db_post:
        db_post.view_count += 1
        db.commit()
        db.refresh(db_post)
    return db_post

def delete_post(db: Session, post_id: uuid.UUID, user_id: uuid.UUID):
    db_post = db.query(models.Post).filter(models.Post.id == post_id, models.Post.user_id == user_id).first()
    if db_post:
        db.delete(db_post)
        db.commit()
        return True
    return False
