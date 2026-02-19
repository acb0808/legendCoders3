import os
import sys
from datetime import date

# backend 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.services.problem_selector import select_daily_problem

def seed():
    db = SessionLocal()
    try:
        today = date.today()
        print(f"Selecting problem for {today}...")
        problem = select_daily_problem(db, today)
        if problem:
            print(f"Successfully added problem: {problem.title} ({problem.baekjoon_problem_id})")
        else:
            print("Failed to select problem. Check logs for details.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
