# backend/app/routers/stats.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..crud import stats
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/stats",
    tags=["statistics"],
)

@router.get("/ranking", response_model=List[schemas.UserRanking])
def get_ranking(db: Session = Depends(get_db), limit: int = 10):
    return stats.get_global_ranking(db, limit=limit)

@router.get("/me", response_model=schemas.UserDashboard)
def get_my_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total_solved, streak, history = stats.get_user_solved_stats(db, current_user.id)
    return {
        "total_solved": total_solved,
        "streak_days": streak,
        "solve_history": history
    }
