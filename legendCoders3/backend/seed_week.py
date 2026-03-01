import os
import sys
from datetime import date, timedelta

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.services.problem_selector import select_daily_problem

def seed_week():
    db = SessionLocal()
    # 2026-02-15 is Sunday
    start_date = date(2026, 2, 15) 
    
    print(f"--- Seeding Week: {start_date} ---")
    
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        try:
            problem = select_daily_problem(db, current_date)
            if problem:
                print(f"OK: {current_date} -> {problem.title} ({problem.difficulty_level})")
            else:
                print(f"FAIL: {current_date}")
        except Exception as e:
            print(f"ERROR: {current_date} -> {str(e)}")
            
    db.close()
    print("--- Done ---")

if __name__ == "__main__":
    seed_week()
