# backend/app/routers/submissions.py
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
from .. import schemas, models
from ..crud import daily_problems, submissions
from ..services.baekjoon_crawler import get_latest_solved_submission
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(
    prefix="/submissions",
    tags=["submissions"],
    responses={404: {"description": "Not found"}},
)

@router.post("/register", response_model=schemas.Submission)
async def register_submission_result(
    submission_request: schemas.SubmissionRegisterRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. 일일 문제 확인
    daily_problem = daily_problems.get_daily_problem_by_id(db, submission_request.daily_problem_id)
    if not daily_problem:
        raise HTTPException(status_code=404, detail="Daily problem not found.")

    # 2. 백준에서 제출 결과 확인 및 크롤링
    # 사용자 백준 ID가 설정되어 있어야 함
    if not current_user.baekjoon_id:
        raise HTTPException(status_code=400, detail="Baekjoon ID not set in profile.")

    print(f"Checking submission for user {current_user.baekjoon_id}, problem {daily_problem.baekjoon_problem_id}")
    
    # 제공해주신 유틸리티 로직 기반으로 최신 성공 기록 가져오기
    crawled_result = get_latest_solved_submission(
        current_user.baekjoon_id,
        daily_problem.baekjoon_problem_id
    )
    
    if not crawled_result:
        raise HTTPException(
            status_code=400, 
            detail=f"No 'Accepted' submission found for problem {daily_problem.baekjoon_problem_id} on Baekjoon for user {current_user.baekjoon_id}."
        )

    # 3. Submission 객체 생성 및 저장
    submission_create = schemas.SubmissionCreate(
        daily_problem_id=submission_request.daily_problem_id,
        baekjoon_submission_id=crawled_result["baekjoon_submission_id"],
        language=crawled_result["language"],
        code=None, # 코드 크롤링은 일단 생략
        status=crawled_result["status"],
        result_message=crawled_result["result_message"],
        runtime_ms=crawled_result["runtime_ms"],
        memory_usage_kb=crawled_result["memory_usage_kb"],
        submitted_at=crawled_result["submitted_at"]
    )
    
    # 이미 등록된 제출인지 확인 (중복 방지)
    # submissions.py에 중복 체크 로직이 없으므로 일단 생성 시도. DB의 unique constraint가 잡아줄 것임.
    try:
        db_submission = submissions.create_submission(
            db=db,
            user_id=current_user.id,
            submission=submission_create,
            baekjoon_problem_id=daily_problem.baekjoon_problem_id
        )
        return db_submission
    except Exception as e:
        # 중복 등록인 경우 등 예외 처리
        if "unique constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="This submission has already been registered.")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/{submission_id}", response_model=schemas.Submission)
def get_single_submission(
    submission_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_submission = submissions.get_submission(db, submission_id)
    if not db_submission or db_submission.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Submission not found or not authorized.")
    return db_submission

@router.get("/problem/{daily_problem_id}", response_model=List[schemas.Submission])
def get_user_submissions_for_problem(
    daily_problem_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_submissions = submissions.get_user_submissions_for_problem(db, current_user.id, daily_problem_id)
    return db_submissions
