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
from .titles import grant_title_if_not_exists

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

    # --- 추가: 이미 해결한 문제인지 먼저 확인 ---
    existing_solve = db.query(models.Submission).filter(
        models.Submission.user_id == current_user.id,
        models.Submission.daily_problem_id == daily_problem.id
    ).first()
    if existing_solve:
        raise HTTPException(status_code=400, detail="이미 이 문제를 해결하여 등록을 완료했습니다.")

    # 2. 백준에서 제출 결과 확인 및 크롤링
    if not current_user.baekjoon_id:
        raise HTTPException(status_code=400, detail="Baekjoon ID not set in profile.")

    print(f"Checking submission for user {current_user.baekjoon_id}, problem {daily_problem.baekjoon_problem_id}")
    
    crawled_result = get_latest_solved_submission(
        current_user.baekjoon_id,
        daily_problem.baekjoon_problem_id
    )
    
    if not crawled_result:
        raise HTTPException(
            status_code=400, 
            detail=f"백준 아이디({current_user.baekjoon_id})로 {daily_problem.baekjoon_problem_id}번 문제에 대한 '맞았습니다!!' 기록을 찾을 수 없습니다. 백준에서 먼저 문제를 해결한 후 다시 시도해주세요."
        )

    # 3. Submission 객체 생성 및 저장
    submission_create = schemas.SubmissionCreate(
        daily_problem_id=submission_request.daily_problem_id,
        baekjoon_submission_id=crawled_result["baekjoon_submission_id"],
        language=crawled_result["language"],
        code=None,
        status=crawled_result["status"],
        result_message=crawled_result["result_message"],
        runtime_ms=crawled_result["runtime_ms"],
        memory_usage_kb=crawled_result["memory_usage_kb"],
        submitted_at=crawled_result["submitted_at"]
    )
    
    try:
        db_submission = submissions.create_submission(
            db=db,
            user_id=current_user.id,
            submission=submission_create,
            baekjoon_problem_id=daily_problem.baekjoon_problem_id
        )
        
        # --- 칭호 자동 부여 로직 ---
        try:
            # 1. 퍼스트 블러드 체크
            first_solve = db.query(models.Submission).filter(
                models.Submission.daily_problem_id == daily_problem.id
            ).order_by(models.Submission.submitted_at.asc()).first()
            
            if first_solve and first_solve.user_id == current_user.id:
                grant_title_if_not_exists(db, current_user.id, "퍼스트 블러드")

            # 2. 얼리버드 체크 (06:00 ~ 09:00)
            now_hour = datetime.now().hour
            if 6 <= now_hour < 9:
                grant_title_if_not_exists(db, current_user.id, "얼리버드")

            # 3. 난이도별 칭호
            if "Bronze" in daily_problem.difficulty_level:
                grant_title_if_not_exists(db, current_user.id, "브론즈 마스터")
            elif "Platinum" in daily_problem.difficulty_level:
                grant_title_if_not_exists(db, current_user.id, "플래티넘 헌터")
        except Exception as title_err:
            print(f"Title grant error: {title_err}")

        return db_submission
    except Exception as e:
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
