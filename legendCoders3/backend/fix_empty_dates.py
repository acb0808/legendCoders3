import os
import sys
from datetime import date
import requests
from bs4 import BeautifulSoup

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.services.problem_selector import select_daily_problem, fetch_problems_from_solved_ac, get_problem_details_from_baekjoon, get_tier_name
from app.schemas import DailyProblemCreate
from app import crud

def force_select_problem(db, for_date, tier_range, min_solved=50):
    """조건을 대폭 완화하여 문제를 선정합니다."""
    query = f"tier:{tier_range} lang:ko s#{min_solved}.."
    print(f"[{for_date}] Re-trying with relaxed query: {query}")
    
    candidates = fetch_problems_from_solved_ac(query)
    for cand in candidates:
        problem_id = cand["problemId"]
        if crud.daily_problems.get_daily_problem_by_baekjoon_id(db, problem_id):
            continue
            
        details = get_problem_details_from_baekjoon(problem_id)
        if not details:
            continue
            
        tags = [tag["key"] for tag in cand.get("tags", [])]
        new_problem = crud.daily_problems.create_daily_problem(db, DailyProblemCreate(
            problem_date=for_date,
            baekjoon_problem_id=problem_id,
            difficulty_level=get_tier_name(cand["level"]),
            algorithm_type=tags if tags else ["Unknown"],
            **details
        ))
        print(f"FIXED: {for_date} -> {new_problem.title} ({new_problem.difficulty_level})")
        return True
    return False

def main():
    db = SessionLocal()
    
    # 2월 15일 (일요일): 플래티넘 4~3 (17~18)
    if not crud.daily_problems.get_daily_problem_by_date(db, date(2026, 2, 15)):
        force_select_problem(db, date(2026, 2, 15), "17..18", min_solved=30)
        
    # 2월 18일 (수요일): 실버 2~1 (9..10)
    if not crud.daily_problems.get_daily_problem_by_date(db, date(2026, 2, 18)):
        force_select_problem(db, date(2026, 2, 18), "9..10", min_solved=100)
        
    db.close()

if __name__ == "__main__":
    main()
