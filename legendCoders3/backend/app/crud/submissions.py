# backend/app/crud/submissions.py
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from .. import models, schemas
from datetime import datetime
import uuid

def get_submission(db: Session, submission_id: uuid.UUID):
    return db.query(models.Submission).filter(models.Submission.id == submission_id).first()

def get_user_submissions_for_problem(db: Session, user_id: uuid.UUID, daily_problem_id: uuid.UUID):
    return db.query(models.Submission).filter(
        models.Submission.user_id == user_id,
        models.Submission.daily_problem_id == daily_problem_id
    ).all()

def create_submission(db: Session, user_id: uuid.UUID, submission: schemas.SubmissionCreate, baekjoon_problem_id: int):
    db_submission = models.Submission(
        user_id=user_id,
        daily_problem_id=submission.daily_problem_id,
        baekjoon_problem_id=baekjoon_problem_id,
        baekjoon_submission_id=submission.baekjoon_submission_id,
        language=submission.language,
        code=submission.code,
        status=submission.status,
        result_message=submission.result_message,
        runtime_ms=submission.runtime_ms,
        memory_usage_kb=submission.memory_usage_kb,
        submitted_at=submission.submitted_at
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission

def update_submission_status(db: Session, submission_id: uuid.UUID, status: str, result_message: Optional[str] = None, runtime_ms: Optional[int] = None, memory_usage_kb: Optional[int] = None, code: Optional[str] = None):
    db_submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if db_submission:
        db_submission.status = status
        db_submission.result_message = result_message
        db_submission.runtime_ms = runtime_ms
        db_submission.memory_usage_kb = memory_usage_kb
        if code:
            db_submission.code = code
        db.commit()
        db.refresh(db_submission)
    return db_submission
