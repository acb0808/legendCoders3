import os
import sys
import time
from datetime import date

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.services.problem_selector import fetch_problems_from_solved_ac, get_problem_details_from_baekjoon, get_tier_name
from app.schemas import DailyProblemCreate
from app import crud

def fill_date(db, for_date, tier_range, tags, min_solved):
    print(f"[{for_date}] Filling empty date...")
    # 1. Try with tags
    query = f"tier:{tier_range} lang:ko s#{min_solved}.. ({tags})"
    candidates = fetch_problems_from_solved_ac(query)
    
    # 2. If no results, try without tags
    if not candidates:
        query = f"tier:{tier_range} lang:ko s#{max(10, min_solved//2)}.."
        candidates = fetch_problems_from_solved_ac(query)

    for cand in candidates:
        problem_id = cand["problemId"]
        if crud.daily_problems.get_daily_problem_by_baekjoon_id(db, problem_id): continue
            
        print(f"Waiting 10s for #{problem_id}...")
        time.sleep(10)
        
        details = get_problem_details_from_baekjoon(problem_id)
        if not details: continue
            
        crud.daily_problems.create_daily_problem(db, DailyProblemCreate(
            problem_date=for_date,
            baekjoon_problem_id=problem_id,
            difficulty_level=get_tier_name(cand["level"]),
            algorithm_type=[tag["key"] for tag in cand.get("tags", [])],
            **details
        ))
        print(f"SUCCESS: {for_date} -> #{problem_id}")
        return True
    return False

def main():
    db = SessionLocal()
    
    # Fri: Gold 3..2 (13..14)
    if not crud.daily_problems.get_daily_problem_by_date(db, date(2026, 2, 20)):
        fill_date(db, date(2026, 2, 20), "13..14", "dp|binary_search", 80)
        time.sleep(5)
        
    # Sat: Gold 1..Plat 5 (15..16)
    if not crud.daily_problems.get_daily_problem_by_date(db, date(2026, 2, 21)):
        fill_date(db, date(2026, 2, 21), "15..16", "graphs|data_structures", 50)
        
    db.close()
    print("Done.")

if __name__ == "__main__":
    main()
