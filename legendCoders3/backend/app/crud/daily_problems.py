# backend/app/crud/daily_problems.py
import uuid # 추가
from sqlalchemy.orm import Session
from datetime import date, datetime
from .. import models, schemas

def get_daily_problem_by_id(db: Session, problem_id: uuid.UUID):
    return db.query(models.DailyProblem).filter(models.DailyProblem.id == problem_id).first()

def get_daily_problem_by_date(db: Session, problem_date: date):
    return db.query(models.DailyProblem).filter(
        models.DailyProblem.problem_date == problem_date
    ).first()

def get_daily_problem_by_baekjoon_id(db: Session, baekjoon_problem_id: int):
    return db.query(models.DailyProblem).filter(
        models.DailyProblem.baekjoon_problem_id == baekjoon_problem_id
    ).first()

def create_daily_problem(db: Session, daily_problem: schemas.DailyProblemCreate):
    db_problem = models.DailyProblem(
        problem_date=daily_problem.problem_date,
        baekjoon_problem_id=daily_problem.baekjoon_problem_id,
        title=daily_problem.title,
        description=daily_problem.description,
        input_example=daily_problem.input_example,
        output_example=daily_problem.output_example,
        time_limit_ms=daily_problem.time_limit_ms,
        memory_limit_mb=daily_problem.memory_limit_mb,
        difficulty_level=daily_problem.difficulty_level,
        algorithm_type=daily_problem.algorithm_type,
    )
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)
    return db_problem
