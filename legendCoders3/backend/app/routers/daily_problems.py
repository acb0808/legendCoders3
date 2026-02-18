# backend/app/routers/daily_problems.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime
from .. import schemas
from ..crud import daily_problems # daily_problems crud 모듈 임포트
from ..database import get_db

router = APIRouter(
    prefix="/daily-problems",
    tags=["daily-problems"],
    responses={404: {"description": "Not found"}},
)

@router.get("/today", response_model=schemas.DailyProblem)
def get_today_problem(db: Session = Depends(get_db)):
    today = date.today()
    problem = daily_problems.get_daily_problem_by_date(db, today)
    if not problem:
        # TODO: AI 문제 선정 로직을 여기서 트리거하거나 스케줄러가 이미 실행했다고 가정
        # for_date = datetime.utcnow().date() + timedelta(days=1) # 다음날 문제 선정
        raise HTTPException(status_code=404, detail="No problem selected for today yet.")
    return problem

@router.get("/{problem_date}", response_model=schemas.DailyProblem)
def get_problem_by_date(problem_date: date, db: Session = Depends(get_db)):
    problem = daily_problems.get_daily_problem_by_date(db, problem_date)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found for this date.")
    return problem
