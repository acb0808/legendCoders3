# backend/app/crud/comments.py
import uuid
from sqlalchemy.orm import Session
from .. import models, schemas
from datetime import datetime

def get_comments_by_post(db: Session, post_id: uuid.UUID):
    return db.query(models.Comment).filter(models.Comment.post_id == post_id).all()

def create_comment(db: Session, user_id: uuid.UUID, comment: schemas.CommentCreate):
    db_comment = models.Comment(
        user_id=user_id,
        post_id=comment.post_id,
        parent_comment_id=comment.parent_comment_id,
        content=comment.content
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

def delete_comment(db: Session, comment_id: uuid.UUID, user_id: uuid.UUID):
    db_comment = db.query(models.Comment).filter(models.Comment.id == comment_id, models.Comment.user_id == user_id).first()
    if db_comment:
        db.delete(db_comment)
        db.commit()
        return True
    return False
