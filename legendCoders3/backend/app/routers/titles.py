import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/titles",
    tags=["titles"],
)

@router.get("/me", response_model=List[schemas.Title])
def get_my_unlocked_titles(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """현재 사용자가 해금한 모든 칭호를 가져옵니다."""
    user_titles = db.query(models.UserTitle).filter(models.UserTitle.user_id == current_user.id).all()
    return [ut.title for ut in user_titles] # t를 ut로 수정

@router.get("/all", response_model=List[schemas.Title])
def get_all_titles(db: Session = Depends(get_db)):
    """시스템에 존재하는 모든 칭호를 가져옵니다. (도감용)"""
    return db.query(models.Title).all()

@router.post("/equip/{title_id}")
def equip_title(
    title_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """특정 칭호를 장착합니다. 해금되지 않은 칭호는 장착할 수 없습니다."""
    # 1. 해금 여부 확인
    unlocked = db.query(models.UserTitle).filter(
        models.UserTitle.user_id == current_user.id,
        models.UserTitle.title_id == title_id
    ).first()
    
    if not unlocked:
        # 특별 케이스: Legend Pro 전용 칭호는 Pro 여부만 확인해도 됨 (또는 자동 해금)
        title = db.query(models.Title).filter(models.Title.id == title_id).first()
        if title and title.is_pro_only:
            if not current_user.is_pro:
                raise HTTPException(status_code=403, detail="Legend Pro 회원만 장착 가능한 칭호입니다.")
        else:
            raise HTTPException(status_code=403, detail="해당 칭호를 아직 획득하지 못했습니다.")

    # 2. 장착
    current_user.equipped_title_id = title_id
    db.commit()
    return {"message": "칭호가 성공적으로 장착되었습니다."}

@router.post("/unequip")
def unequip_title(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """장착 중인 칭호를 해제합니다."""
    current_user.equipped_title_id = None
    db.commit()
    return {"message": "칭호가 해제되었습니다."}

# --- 칭호 획득 유틸리티 (내부 로직용) ---

def grant_title_if_not_exists(db: Session, user_id: uuid.UUID, title_name: str):
    """사용자에게 특정 칭호를 부여합니다. (이미 있으면 무시)"""
    title = db.query(models.Title).filter(models.Title.name == title_name).first()
    if not title: return False
    
    existing = db.query(models.UserTitle).filter(
        models.UserTitle.user_id == user_id,
        models.UserTitle.title_id == title.id
    ).first()
    
    if not existing:
        new_ut = models.UserTitle(user_id=user_id, title_id=title.id)
        db.add(new_ut)
        db.commit()
        return True
    return False
