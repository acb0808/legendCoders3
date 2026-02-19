# backend/app/routers/comments.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import schemas, models
from ..crud import comments, posts
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/comments",
    tags=["comments"],
)

@router.post("/", response_model=schemas.Comment)
def create_new_comment(
    comment: schemas.CommentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 게시글 존재 여부 확인
    post = posts.get_post(db, comment.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    
    db_comment = comments.create_comment(db=db, user_id=current_user.id, comment=comment)
    # 응답 모델을 위해 닉네임 매핑
    db_comment.nickname = current_user.nickname
    return db_comment

@router.delete("/{comment_id}")
def delete_existing_comment(
    comment_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = comments.delete_comment(db, comment_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Comment not found or not authorized to delete.")
    return {"message": "Successfully deleted comment"}
