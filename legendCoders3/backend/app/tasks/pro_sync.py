import asyncio
import anyio
import time
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from ..database import SessionLocal
from .. import models, crud
from ..services.baekjoon_crawler import get_latest_solved_submission
from ..routers.titles import grant_title_if_not_exists

def sync_pro_users_sync():
    """DB와 크롤링을 수행하는 동기 함수 (스레드에서 실행됨)"""
    db = SessionLocal()
    print(f"[{datetime.now()}] --- Executing Pro Auto-Sync Cycle ---")
    try:
        today = date.today()
        daily_problem = db.query(models.DailyProblem).filter(
            models.DailyProblem.problem_date >= datetime.combine(today, datetime.min.time()),
            models.DailyProblem.problem_date <= datetime.combine(today, datetime.max.time())
        ).first()
        
        if not daily_problem:
            print(f"[{datetime.now()}] No daily problem found. Skipping.")
            return "No problem"

        pro_users = db.query(models.User).filter(
            models.User.is_pro == True,
            (models.User.pro_expires_at > datetime.now()) | (models.User.pro_expires_at == None)
        ).all()

        for user in pro_users:
            existing_sub = db.query(models.Submission).filter(
                models.Submission.user_id == user.id,
                models.Submission.daily_problem_id == daily_problem.id
            ).first()
            
            if existing_sub:
                continue

            print(f"[{datetime.now()}] Checking Baekjoon for Pro User: {user.nickname}")
            
            try:
                crawled_data = get_latest_solved_submission(user.baekjoon_id, daily_problem.baekjoon_problem_id)
                
                if crawled_data:
                    new_sub = models.Submission(
                        user_id=user.id,
                        daily_problem_id=daily_problem.id,
                        baekjoon_problem_id=daily_problem.baekjoon_problem_id,
                        **crawled_data
                    )
                    db.add(new_sub)
                    user.last_sync_at = datetime.now()
                    db.commit()
                    print(f"[{datetime.now()}] AUTO-SYNC SUCCESS: {user.nickname} solved {daily_problem.baekjoon_problem_id}")
                    
                    # --- 칭호 부여 로직 ---
                    try:
                        # 퍼스트 블러드 체크
                        other_solves = db.query(models.Submission).filter(
                            models.Submission.daily_problem_id == daily_problem.id,
                            models.Submission.id != new_sub.id
                        ).count()
                        if other_solves == 0:
                            grant_title_if_not_exists(db, user.id, "퍼스트 블러드")
                        
                        # 얼리버드 체크
                        if 6 <= datetime.now().hour < 9:
                            grant_title_if_not_exists(db, user.id, "얼리버드")
                            
                        # 난이도별 칭호
                        if "Bronze" in daily_problem.difficulty_level:
                            grant_title_if_not_exists(db, user.id, "브론즈 마스터")
                        elif "Platinum" in daily_problem.difficulty_level:
                            grant_title_if_not_exists(db, user.id, "플래티넘 헌터")
                    except Exception as title_err:
                        print(f"Title grant error in sync: {title_err}")
            except Exception as e:
                print(f"[{datetime.now()}] Sync error for {user.nickname}: {e}")
                db.rollback()
            
            time.sleep(1)
            
        return "Done"
    except Exception as e:
        print(f"[{datetime.now()}] Critical error in sync_pro_users_sync: {e}")
    finally:
        db.close()

async def pro_sync_loop():
    print(f"[{datetime.now()}] Pro Auto-Sync Loop STARTED.")
    now = datetime.now()
    minutes_to_next_cycle = 5 - (now.minute % 5)
    seconds_to_sleep = (minutes_to_next_cycle * 60) - now.second
    if seconds_to_sleep <= 0: seconds_to_sleep = 300
    
    print(f"[{datetime.now()}] Aligning with clock: Waiting {seconds_to_sleep}s...")
    await asyncio.sleep(seconds_to_sleep)

    while True:
        try:
            await anyio.to_thread.run_sync(sync_pro_users_sync)
        except Exception as e:
            print(f"[{datetime.now()}] Error in pro_sync_loop: {e}")
        
        now = datetime.now()
        minutes_to_next_cycle = 5 - (now.minute % 5)
        seconds_to_sleep = (minutes_to_next_cycle * 60) - now.second
        if seconds_to_sleep <= 0: seconds_to_sleep = 300
        await asyncio.sleep(seconds_to_sleep)
