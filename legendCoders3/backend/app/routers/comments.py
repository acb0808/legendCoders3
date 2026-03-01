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
    db_comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    
    # 본인이거나 관리자인 경우만 허용
    if db_comment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="삭제 권한이 없습니다."
        )
    
    db.delete(db_comment)
    db.commit()
    return {"message": "Successfully deleted comment"}
