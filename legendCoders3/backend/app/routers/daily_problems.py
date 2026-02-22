# backend/app/routers/daily_problems.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional 
import json # Added this
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
        raise HTTPException(status_code=404, detail="No problem selected for today yet.")
    return problem

@router.get("/id/{problem_id}", response_model=schemas.DailyProblem)
def get_problem_by_uuid(problem_id: uuid.UUID, db: Session = Depends(get_db)):
    problem = daily_problems.get_daily_problem_by_id(db, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found with this ID.")
    return problem

import requests # Added
from ..services.problem_selector import get_problem_details_from_baekjoon, get_tier_name # Corrected import

from sqlalchemy.exc import IntegrityError # Added for handling race conditions

import time # Added for polite delay

from ..websockets.manager import manager # Added for broadcasting

@router.get("/baekjoon/{bj_id}", response_model=schemas.DailyProblem)
async def get_problem_by_baekjoon_id(
    bj_id: int, 
    arena_id: Optional[uuid.UUID] = Query(None), # Optional arena_id
    db: Session = Depends(get_db)
):
    problem = daily_problems.get_daily_problem_by_baekjoon_id(db, bj_id)
    
    if not problem:
        # On-demand caching: metadata from Solved.ac
        print(f"[DailyProblem] Problem {bj_id} not in cache. Fetching from Solved.ac...")
        try:
            solved_ac_res = requests.get(f"https://solved.ac/api/v3/problem/show?problemId={bj_id}", timeout=5)
            if solved_ac_res.status_code != 200:
                raise HTTPException(status_code=404, detail="Problem metadata not found on Solved.ac")
            
            meta = solved_ac_res.json()
            title_from_api = meta.get("titleKo") or meta.get("titleEn") or f"Problem #{bj_id}"
            
            new_problem_schema = schemas.DailyProblemCreate(
                problem_date=datetime.now(),
                baekjoon_problem_id=bj_id,
                title=title_from_api,
                description="백준에서 문제를 확인해 주세요.",
                input_example="백준 참조",
                output_example="백준 참조",
                time_limit_ms=2000, # Default
                memory_limit_mb=512, # Default
                difficulty_level=get_tier_name(meta["level"]),
                algorithm_type=[tag["key"] for tag in meta.get("tags", [])]
            )
            
            try:
                problem = daily_problems.create_daily_problem(db, new_problem_schema)
                print(f"[DailyProblem] Cached problem {bj_id}: {title_from_api}")
                
                if arena_id:
                    await manager.broadcast_to_room(
                        str(arena_id), 
                        json.dumps({"type": "PROBLEM_LOADED", "payload": {"problem_id": bj_id}})
                    )
            except IntegrityError:
                db.rollback()
                problem = daily_problems.get_daily_problem_by_baekjoon_id(db, bj_id)
            
        except Exception as e:
            print(f"[DailyProblem] Error caching {bj_id}: {e}")
            if isinstance(e, HTTPException): raise e
            raise HTTPException(status_code=500, detail=str(e))
            
    return problem

@router.get("/{problem_date}", response_model=schemas.DailyProblem)
def get_problem_by_date(problem_date: date, db: Session = Depends(get_db)):
    problem = daily_problems.get_daily_problem_by_date(db, problem_date)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found for this date.")
    return problem
