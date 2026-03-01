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

@router.get("/activity/{user_id}", response_model=List[schemas.Activity])
def get_user_activity(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    _, _, history = stats.get_user_solved_stats(db, user_id)
    return [
        {
            "date": d,
            "type": "SOLVED",
            "solved_count": 1
        }
        for d in history
    ]

@router.get("/weekly", response_model=List[schemas.WeeklyStatus])
def get_weekly_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from datetime import date, timedelta, datetime
    
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    results = []
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    
    for i in range(7):
        target_date = monday + timedelta(days=i)
        problem = db.query(models.DailyProblem).filter(
            models.DailyProblem.problem_date >= datetime.combine(target_date, datetime.min.time()),
            models.DailyProblem.problem_date <= datetime.combine(target_date, datetime.max.time())
        ).first()
        
        is_solved = False
        if problem:
            submission = db.query(models.Submission).filter(
                models.Submission.user_id == current_user.id,
                models.Submission.daily_problem_id == problem.id
            ).first()
            is_solved = submission is not None
            
        results.append({
            "date": target_date,
            "day_name": day_names[i],
            "is_solved": is_solved,
            "has_problem": problem is not None
        })
        
    return results

@router.get("/weekly/all", response_model=List[schemas.UserWeeklyLeaderboard])
def get_all_weekly_status(
    db: Session = Depends(get_db)
):
    from datetime import date, timedelta, datetime
    from sqlalchemy.orm import joinedload
    
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    
    # 1. 이번 주 문제들 미리 가져오기
    problems = []
    for i in range(7):
        target_date = monday + timedelta(days=i)
        prob = db.query(models.DailyProblem).filter(
            models.DailyProblem.problem_date >= datetime.combine(target_date, datetime.min.time()),
            models.DailyProblem.problem_date <= datetime.combine(target_date, datetime.max.time())
        ).first()
        problems.append(prob)
    
    # 2. 모든 유저 가져오기
    users = db.query(models.User).options(joinedload(models.User.equipped_title)).all()
    
    all_results = []
    for user in users:
        user_status = []
        for i in range(7):
            target_date = monday + timedelta(days=i)
            prob = problems[i]
            
            is_solved = False
            if prob:
                submission = db.query(models.Submission).filter(
                    models.Submission.user_id == user.id,
                    models.Submission.daily_problem_id == prob.id
                ).first()
                is_solved = submission is not None
            
            user_status.append({
                "date": target_date,
                "day_name": day_names[i],
                "is_solved": is_solved,
                "has_problem": prob is not None
            })
            
        all_results.append({
            "user_id": user.id,
            "nickname": user.nickname,
            "equipped_title": user.equipped_title,
            "status": user_status
        })
        
    return all_results
