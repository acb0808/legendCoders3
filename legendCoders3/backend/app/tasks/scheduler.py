# backend/app/tasks/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, timedelta
import pytz # 시간대 처리를 위해 필요
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..services.problem_selector import select_daily_problem
from ..crud import daily_problems # crud.daily_problems 임포트

# 한국 시간대 설정
SEOUL_TZ = pytz.timezone("Asia/Seoul")

def schedule_daily_problem_selection():
    """매일 정해진 시간에 문제 선정을 스케줄링하는 함수."""
    # Scheduler 인스턴스 생성
    scheduler = BackgroundScheduler(timezone=SEOUL_TZ)

    # 매일 12시 KST에 다음 날 문제 선정 (예: 오늘 12시에 내일 문제 선정)
    # CronTrigger: year, month, day, week, day_of_week, hour, minute, second
    # hour=12, minute=0, second=0
    trigger = CronTrigger(hour=12, minute=0, second=0, timezone=SEOUL_TZ)
    
    # job_id를 명시하여 중복 등록 방지
    scheduler.add_job(
        select_and_save_problem,
        trigger,
        id="daily_problem_selection_job",
        replace_existing=True,
        args=[] # 이 잡은 직접 DB 세션을 생성하여 사용
    )

    # 스케줄러 시작
    scheduler.start()
    print("Scheduler started for daily problem selection.")
    return scheduler

def select_and_save_problem():
    """스케줄링된 작업: 다음 날의 문제를 선정하고 DB에 저장."""
    db: Session = SessionLocal()
    try:
        # 오늘 날짜를 기준으로 다음 날의 문제를 선정 (예: 7/30 12시 -> 7/31 문제 선정)
        target_date = datetime.now(SEOUL_TZ).date() + timedelta(days=1)
        print(f"Attempting to select daily problem for {target_date}...")
        select_daily_problem(db, for_date=target_date)
    except Exception as e:
        print(f"Error in scheduled daily problem selection: {e}")
    finally:
        db.close()

def start_scheduler():
    # 애플리케이션 시작 시 스케줄러 초기화 및 시작
    global scheduler_instance
    scheduler_instance = schedule_daily_problem_selection()
    # 애플리케이션 시작 시 오늘 문제가 없으면 오늘 문제도 한번 선정 시도 (선택 사항)
    # db_temp: Session = SessionLocal()
    # try:
    #     today = datetime.now(SEOUL_TZ).date()
    #     if not daily_problems.get_daily_problem_by_date(db_temp, today):
    #         print(f"No problem for today ({today}). Attempting to select it now...")
    #         select_daily_problem(db_temp, for_date=today)
    # except Exception as e:
    #     print(f"Error selecting today's problem at startup: {e}")
    # finally:
    #     db_temp.close()