# backend/app/stats.py
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from .. import models, schemas
from datetime import date, timedelta, datetime

def get_user_solved_stats(db: Session, user_id: uuid.UUID):
    """
    사용자의 총 해결 문제 수와 연속 해결 일수를 계산합니다.
    """
    # 성공한 제출물 가져오기 (날짜 기준 정렬)
    submissions = db.query(models.Submission).filter(
        models.Submission.user_id == user_id,
        models.Submission.status == "Accepted"
    ).order_by(desc(models.Submission.submitted_at)).all()
    
    total_solved = len(set(s.baekjoon_problem_id for s in submissions))
    
    # 연속 해결 일수 (Streak) 계산
    streak = 0
    if submissions:
        solve_dates = sorted(list(set(s.submitted_at.date() for s in submissions)), reverse=True)
        
        current_date = date.today()
        # 오늘 풀었거나 어제 풀었어야 스트릭 유지
        if solve_dates[0] >= current_date - timedelta(days=1):
            streak = 1
            for i in range(len(solve_dates) - 1):
                if solve_dates[i] - timedelta(days=1) == solve_dates[i+1]:
                    streak += 1
                else:
                    break
        else:
            streak = 0
            
    return total_solved, streak, [s.submitted_at.date() for s in submissions]

def get_global_ranking(db: Session, limit: int = 10):
    """
    전체 사용자 랭킹을 가져옵니다. (해결 문제 수 기준)
    """
    # 닉네임과 함께 해결 문제 수 집계
    # 실제 프로덕션에서는 성능을 위해 통계 테이블을 따로 두는 것이 좋음
    users = db.query(models.User).all()
    ranking_data = []
    
    for user in users:
        total_solved, streak, _ = get_user_solved_stats(db, user.id)
        ranking_data.append({
            "user_id": user.id,
            "nickname": user.nickname,
            "solved_count": total_solved,
            "consecutive_days": streak
        })
        
    # 해결 문제 수 내림차순 정렬
    ranking_data.sort(key=lambda x: x["solved_count"], reverse=True)
    
    return ranking_data[:limit]
