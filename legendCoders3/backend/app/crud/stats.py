import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from .. import models, schemas
from datetime import date, timedelta, datetime
import pytz

def get_kst_now():
    return datetime.now(pytz.timezone('Asia/Seoul'))

def get_user_solved_stats(db: Session, user_id: uuid.UUID):
    """
    사용자의 통계를 계산합니다. (스트릭 보호권 논리 정밀화)
    """
    # 1. 실제 푼 문제들 (중복 제거)
    actual_submissions = db.query(models.Submission).filter(
        models.Submission.user_id == user_id,
        models.Submission.status == "Accepted"
    ).all()
    unique_problem_ids = set(s.baekjoon_problem_id for s in actual_submissions)
    actual_solved_count = len(unique_problem_ids)

    # 2. 해결 날짜 리스트 (KST 기준, 내림차순)
    problem_dates_query = db.query(models.DailyProblem.problem_date).join(
        models.Submission, models.Submission.daily_problem_id == models.DailyProblem.id
    ).filter(
        models.Submission.user_id == user_id,
        models.Submission.status == "Accepted"
    ).all()
    solve_dates = sorted(list(set(d[0].date() for d in problem_dates_query)), reverse=True)
    
    # 3. 스트릭 계산
    user = db.query(models.User).filter(models.User.id == user_id).first()
    remaining_freeze = user.streak_freeze_count if user else 0
    
    today = get_kst_now().date()
    streak = 0
    
    if solve_dates:
        temp_freeze = remaining_freeze
        check_date = today
        idx = 0
        current_streak = 0
        
        # 가장 오래된 해결 날짜를 찾음 (이 날짜보다 더 과거로 보호권을 쓸 수는 없음)
        oldest_solve_date = solve_dates[-1]

        while check_date >= oldest_solve_date:
            if idx < len(solve_dates) and solve_dates[idx] == check_date:
                # 실제로 해결한 날
                current_streak += 1
                idx += 1
                check_date -= timedelta(days=1)
            elif temp_freeze > 0:
                # 해결 기록은 없지만 보호권이 있음
                current_streak += 1
                temp_freeze -= 1
                check_date -= timedelta(days=1)
            else:
                # 기록도 없고 보호권도 다 씀 -> 여기서 중단
                break
        
        # 만약 오늘/어제 기준으로 시작조차 못했다면 스트릭은 0
        # (예: 한 달 전에 풀고 보호권 5개 있어도 오늘 스트릭은 0이어야 함)
        if solve_dates[0] < today - timedelta(days=remaining_freeze + 1):
            streak = 0
        else:
            streak = current_streak
    
    print(f"[FINAL DEBUG] User: {user.nickname}, Solved: {actual_solved_count}, Streak: {streak}, Freezes: {remaining_freeze}")
    return actual_solved_count, streak, solve_dates

def get_global_ranking(db: Session, limit: int = 10):
    users = db.query(models.User).all()
    ranking_data = []
    for user in users:
        actual_count, streak, _ = get_user_solved_stats(db, user.id)
        ranking_data.append({
            "user_id": user.id,
            "nickname": user.nickname,
            "solved_count": actual_count,
            "consecutive_days": streak,
            "equipped_title": user.equipped_title
        })
    ranking_data.sort(key=lambda x: (x["solved_count"], x["consecutive_days"]), reverse=True)
    return ranking_data[:limit]
