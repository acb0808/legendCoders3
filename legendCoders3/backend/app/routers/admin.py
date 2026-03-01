import uuid
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime, timedelta
from .. import schemas, models
from ..database import get_db
from ..auth import get_current_user, get_current_admin
from ..crud import crud as user_crud, daily_problems
from ..services.problem_selector import select_daily_problem, get_problem_details_from_baekjoon, get_tier_name
import secrets

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)

# 모든 엔드포인트에서 Depends(get_current_admin)을 사용하여 보안 강화

# --- 사용자 관리 ---

@router.get("/users", response_model=List[schemas.User])
def get_all_users(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """관리자가 모든 사용자 목록을 조회합니다."""
    return db.query(models.User).order_by(models.User.created_at.desc()).all()

@router.put("/users/{user_id}", response_model=schemas.User)
def update_user_by_admin(
    user_id: uuid.UUID,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """관리자가 특정 사용자의 정보를 수정합니다. (어드민 여부, 프로 여부 등 포함)"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    update_data = user_update.dict(exclude_unset=True)
    
    # 비밀번호 변경 처리
    if "password" in update_data and update_data["password"]:
        from ..auth import get_password_hash
        db_user.password_hash = get_password_hash(update_data["password"])
        del update_data["password"]
    
    # 나머지 필드 업데이트
    for key, value in update_data.items():
        if key == "is_pro" and value and not db_user.is_pro:
            db_user.pro_expires_at = datetime.now() + timedelta(days=30)
            db_user.streak_freeze_count = max(db_user.streak_freeze_count, 5)
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/users/{user_id}")
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """관리자가 특정 사용자를 영구 삭제합니다."""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 관리자 본인 삭제 방지
    if db_user.id == admin.id:
        raise HTTPException(status_code=400, detail="관리자 본인 계정은 삭제할 수 없습니다.")

    db.delete(db_user)
    db.commit()
    return {"message": "사용자가 삭제되었습니다."}

# --- 문제 관리 ---

@router.get("/problems", response_model=List[schemas.DailyProblem])
def get_all_problems(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    return db.query(models.DailyProblem).order_by(models.DailyProblem.problem_date.desc()).all()

@router.post("/problems/force", response_model=schemas.DailyProblem)
def force_update_problem(
    problem_date: date, 
    baekjoon_problem_id: int, 
    db: Session = Depends(get_db), 
    admin=Depends(get_current_admin)
):
    """특정 날짜의 문제를 강제로 지정합니다."""
    target_problem = db.query(models.DailyProblem).filter(
        models.DailyProblem.problem_date >= datetime.combine(problem_date, datetime.min.time()),
        models.DailyProblem.problem_date <= datetime.combine(problem_date, datetime.max.time())
    ).first()
    
    if target_problem:
        # 연관 데이터 삭제 (게시글, 댓글, 제출 등)
        db.query(models.Submission).filter(models.Submission.daily_problem_id == target_problem.id).delete()
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
def reseed_problem(problem_id: uuid.UUID, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """문제를 AI가 다시 선정하도록 합니다."""
    target_problem = db.query(models.DailyProblem).filter(models.DailyProblem.id == problem_id).first()
    if not target_problem:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    
    target_date = target_problem.problem_date
    db.query(models.Submission).filter(models.Submission.daily_problem_id == target_problem.id).delete()
    db.delete(target_problem)
    db.commit()
    
    new_problem = select_daily_problem(db, target_date)
    if not new_problem:
        raise HTTPException(status_code=500, detail="문제 재선정에 실패했습니다.")
    return new_problem

@router.delete("/problems/{problem_id}")
def delete_problem(problem_id: uuid.UUID, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    db_problem = db.query(models.DailyProblem).filter(models.DailyProblem.id == problem_id).first()
    if not db_problem:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    db.delete(db_problem)
    db.commit()
    return {"message": "문제가 삭제되었습니다."}

# --- 칭호 관리 ---

@router.post("/titles", response_model=schemas.Title)
def create_new_title(title_data: schemas.TitleBase, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """운영자가 새로운 특수 칭호를 생성합니다."""
    db_title = models.Title(**title_data.dict())
    db.add(db_title)
    db.commit()
    db.refresh(db_title)
    return db_title

@router.post("/users/{user_id}/titles/{title_id}")
def grant_user_title(user_id: uuid.UUID, title_id: uuid.UUID, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """특정 사용자에게 칭호를 직접 부여합니다."""
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

# --- 초대 코드 관리 ---

@router.post("/invitations", response_model=schemas.InvitationCodeResponse)
def generate_invitation_code(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """관리자가 새로운 8자리 초대 코드를 생성합니다."""
    code = secrets.token_hex(4).upper()
    db_invitation = models.InvitationCode(code=code)
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)
    return db_invitation

@router.get("/invitations", response_model=List[schemas.InvitationCodeResponse])
def get_all_invitation_codes(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """관리자가 전체 초대 코드 목록과 사용 현황을 확인합니다."""
    invitations = db.query(models.InvitationCode).order_by(models.InvitationCode.created_at.desc()).all()
    results = []
    for inv in invitations:
        nickname = None
        if inv.used_by_user_id:
            user = db.query(models.User).filter(models.User.id == inv.used_by_user_id).first()
            nickname = user.nickname if user else "Unknown"
        
        results.append({
            "id": inv.id,
            "code": inv.code,
            "is_used": inv.is_used,
            "used_by_user_id": inv.used_by_user_id,
            "created_at": inv.created_at,
            "used_at": inv.used_at,
            "nickname": nickname
        })
    return results

@router.delete("/invitations/{code_id}")
def delete_invitation_code(code_id: uuid.UUID, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    db_inv = db.query(models.InvitationCode).filter(models.InvitationCode.id == code_id).first()
    if not db_inv:
        raise HTTPException(status_code=404, detail="코드를 찾을 수 없습니다.")
    db.delete(db_inv)
    db.commit()
    return {"message": "초대 코드가 삭제되었습니다."}
