# backend/app/routers/posts.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..crud import posts, daily_problems
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/posts",
    tags=["posts"],
)

@router.post("/", response_model=schemas.Post)
def create_new_post(
    post: schemas.PostCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 문제 존재 여부 확인
    problem = daily_problems.get_daily_problem_by_id(db, post.daily_problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Daily problem not found.")
    
    db_post = posts.create_post(db=db, user_id=current_user.id, post=post)
    # 응답 모델을 위해 닉네임 수동 매핑 (ORM 객체에 임시 속성 추가)
    db_post.nickname = current_user.nickname
    return db_post

@router.get("/problem/{daily_problem_id}", response_model=List[schemas.Post])
def read_posts_by_problem(
    daily_problem_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    db_posts = posts.get_posts_by_problem(db, daily_problem_id)
    # 작성자 정보를 포함하도록 처리 (실제 서비스에서는 join 쿼리나 lazy loading 활용)
    for p in db_posts:
        if p.user:
            p.nickname = p.user.nickname
    return db_posts

@router.get("/{post_id}", response_model=schemas.Post)
def read_single_post(
    post_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    db_post = posts.get_post(db, post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found.")
    
    # 조회수 증가
    posts.increment_view_count(db, post_id)
    
    # 작성자 닉네임 및 댓글 작성자 닉네임 매핑
    if db_post.user:
        db_post.nickname = db_post.user.nickname
    
    for c in db_post.comments:
        if c.user:
            c.nickname = c.user.nickname
            
    return db_post

@router.delete("/{post_id}")
def delete_existing_post(
    post_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = posts.delete_post(db, post_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found or not authorized to delete.")
    return {"message": "Successfully deleted post"}
