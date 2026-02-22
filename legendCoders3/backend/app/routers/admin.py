import uuid
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime, timedelta
from .. import schemas, models
from ..database import get_db
from ..auth import get_current_user
from ..crud import crud as user_crud, daily_problems
from ..services.problem_selector import select_daily_problem, get_problem_details_from_baekjoon, get_tier_name

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)

def verify_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.email != "test@test.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 없습니다."
        )
    return current_user

# --- 사용자 관리 ---

@router.get("/users", response_model=List[schemas.User])
def get_all_users(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    return db.query(models.User).all()

@router.delete("/users/{user_id}")
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    db.delete(db_user)
    db.commit()
    return {"message": "사용자가 삭제되었습니다."}

@router.put("/users/{user_id}", response_model=schemas.User)
def update_user_admin(user_id: uuid.UUID, user_update: schemas.UserUpdate, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    if user_update.nickname is not None:
        db_user.nickname = user_update.nickname
    if user_update.baekjoon_id is not None:
        db_user.baekjoon_id = user_update.baekjoon_id
    if user_update.streak_freeze_count is not None:
        db_user.streak_freeze_count = user_update.streak_freeze_count
    
    if hasattr(user_update, 'is_pro') and user_update.is_pro is not None:
        if user_update.is_pro and not db_user.is_pro:
            db_user.is_pro = True
            db_user.pro_expires_at = datetime.now() + timedelta(days=30)
            db_user.streak_freeze_count = 5 # 5개 지급
        elif not user_update.is_pro:
            db_user.is_pro = False
            db_user.pro_expires_at = None
            db_user.streak_freeze_count = 0
        
    db.commit()
    db.refresh(db_user)
    return db_user

# --- 문제 관리 ---

@router.get("/problems", response_model=List[schemas.DailyProblem])
def get_all_problems(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    return db.query(models.DailyProblem).order_by(models.DailyProblem.problem_date.desc()).all()

@router.post("/problems/force")
def force_update_problem(problem_date: date, baekjoon_problem_id: int, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    target_problem = db.query(models.DailyProblem).filter(models.DailyProblem.problem_date == problem_date).first()
    if target_problem:
        post_ids = db.query(models.Post.id).filter(models.Post.daily_problem_id == target_problem.id).all()
        post_ids = [p[0] for p in post_ids]
        if post_ids:
            db.query(models.Comment).filter(models.Comment.post_id.in_(post_ids)).delete(synchronize_session=False)
            db.query(models.Post).filter(models.Post.id.in_(post_ids)).delete(synchronize_session=False)
        db.query(models.Submission).filter(models.Submission.daily_problem_id == target_problem.id).delete(synchronize_session=False)
        db.delete(target_problem)
        db.commit()

    details = get_problem_details_from_baekjoon(baekjoon_problem_id)
    if not details:
        raise HTTPException(status_code=400, detail="백준 문제 정보를 가져올 수 없습니다.")

    try:
        res = requests.get(f"https://solved.ac/api/v3/problem/show?problemId={baekjoon_problem_id}")
        solved_data = res.json()
        tier_name = get_tier_name(solved_data["level"])
        tags = [tag["key"] for tag in solved_data.get("tags", [])]
    except:
        tier_name = "Unknown"
        tags = ["Unknown"]

    new_problem = models.DailyProblem(
        problem_date=datetime.combine(problem_date, datetime.min.time()),
        baekjoon_problem_id=baekjoon_problem_id,
        difficulty_level=tier_name,
        algorithm_type=tags,
        **details
    )
    db.add(new_problem)
    db.commit()
    db.refresh(new_problem)
    return new_problem

@router.post("/problems/{problem_id}/reseed")
def reseed_problem(problem_id: uuid.UUID, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    target_problem = db.query(models.DailyProblem).filter(models.DailyProblem.id == problem_id).first()
    if not target_problem:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    target_date = target_problem.problem_date
    
    post_ids = db.query(models.Post.id).filter(models.Post.daily_problem_id == target_problem.id).all()
    post_ids = [p[0] for p in post_ids]
    if post_ids:
        db.query(models.Comment).filter(models.Comment.post_id.in_(post_ids)).delete(synchronize_session=False)
        db.query(models.Post).filter(models.Post.id.in_(post_ids)).delete(synchronize_session=False)
    db.query(models.Submission).filter(models.Submission.daily_problem_id == target_problem.id).delete(synchronize_session=False)
    
    db.delete(target_problem)
    db.commit()
    
    new_problem = select_daily_problem(db, target_date)
    if not new_problem:
        raise HTTPException(status_code=500, detail="문제 재선정에 실패했습니다.")
    return new_problem

@router.post("/problems/reset-today")
def reset_today_problem(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    today = date.today()
    target_problem = db.query(models.DailyProblem).filter(models.DailyProblem.problem_date == today).first()
    if not target_problem:
        return select_daily_problem(db, today)
    return reseed_problem(target_problem.id, db, admin)

@router.post("/problems/seed")
def seed_specific_date(problem_date: date, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    problem = select_daily_problem(db, problem_date)
    if not problem:
        raise HTTPException(status_code=500, detail="문제 선정에 실패했습니다.")
    return problem

# --- 칭호 관리 ---

@router.post("/titles", response_model=schemas.Title)
def create_new_title(title_data: schemas.TitleBase, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    """운영자가 새로운 특수 칭호를 생성합니다."""
    db_title = models.Title(**title_data.dict())
    db.add(db_title)
    db.commit()
    db.refresh(db_title)
    return db_title

@router.post("/users/{user_id}/titles/{title_id}")
def grant_user_title(user_id: uuid.UUID, title_id: uuid.UUID, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    """특정 사용자에게 칭호를 직접 부여합니다."""
    # 이미 가지고 있는지 확인
    existing = db.query(models.UserTitle).filter(
        models.UserTitle.user_id == user_id,
        models.UserTitle.title_id == title_id
    ).first()
    
    if not existing:
        new_ut = models.UserTitle(user_id=user_id, title_id=title_id)
        db.add(new_ut)
        db.commit()
        return {"message": "칭호가 성공적으로 부여되었습니다."}
    
    return {"message": "이미 보유 중인 칭호입니다."}

@router.delete("/problems/{problem_id}")
def delete_problem(problem_id: uuid.UUID, db: Session = Depends(get_db), admin=Depends(verify_admin)):
    db_problem = db.query(models.DailyProblem).filter(models.DailyProblem.id == problem_id).first()
    if not db_problem:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    db.delete(db_problem)
    db.commit()
    return {"message": "문제가 삭제되었습니다."}
