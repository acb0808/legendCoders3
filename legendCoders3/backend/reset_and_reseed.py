import os
import sys
import time
from datetime import date, timedelta

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import DailyProblem, Submission, Post, Comment
from app.services.problem_selector import select_daily_problem, fetch_problems_from_solved_ac, get_problem_details_from_baekjoon, get_tier_name
from app.schemas import DailyProblemCreate
from app import crud

def select_with_retry(db, for_date, tier_range, tags, min_solved):
    """지연 시간을 두고 문제를 선정하며, 실패 시 조건을 완화하여 재시도합니다."""
    # 1. 원래 조건으로 시도
    query = f"tier:{tier_range} lang:ko s#{min_solved}.. ({tags})"
    print(f"[{for_date}] Trying: {query}")
    
    candidates = fetch_problems_from_solved_ac(query)
    
    # 만약 결과가 없으면 태그 없이 다시 검색
    if not candidates:
        print(f"[{for_date}] No results with tags. Trying without tags...")
        query = f"tier:{tier_range} lang:ko s#{max(10, min_solved//2)}.."
        candidates = fetch_problems_from_solved_ac(query)

    for cand in candidates:
        problem_id = cand["problemId"]
        if crud.daily_problems.get_daily_problem_by_baekjoon_id(db, problem_id): continue
            
        # 크롤링 전 지연
        print(f"Waiting 10s before crawling #{problem_id}...")
        time.sleep(10)
        
        details = get_problem_details_from_baekjoon(problem_id)
        if not details: continue
            
        new_problem = crud.daily_problems.create_daily_problem(db, DailyProblemCreate(
            problem_date=for_date,
            baekjoon_problem_id=problem_id,
            difficulty_level=get_tier_name(cand["level"]),
            algorithm_type=[tag["key"] for tag in cand.get("tags", [])],
            **details
        ))
        print(f"SUCCESS: {for_date} -> #{problem_id} {new_problem.title}")
        return True
    
    return False

def reset_and_reseed_safe():
    db = SessionLocal()
    
    print("--- Resetting Data ---")
    try:
        db.query(Comment).delete()
        db.query(Post).delete()
        db.query(Submission).delete()
        db.query(DailyProblem).delete()
        db.commit()
        print("Cleared.")
    except Exception as e:
        db.rollback()
        print("Error:", str(e))
        return

    # 2026-02-15 is Sunday
    start_date = date(2026, 2, 15) 
    
    # 요일별 설정
    day_configs = {
        0: {"tier": "3..5",   "tags": "math|implementation", "min_solved": 300}, 
        1: {"tier": "6..8",   "tags": "greedy|string",       "min_solved": 200}, 
        2: {"tier": "9..10",  "tags": "bruteforce|sorting",  "min_solved": 150}, 
        3: {"tier": "11..12", "tags": "bfs|dfs",             "min_solved": 100}, 
        4: {"tier": "13..14", "tags": "dp|binary_search",    "min_solved": 80},  
        5: {"tier": "15..16", "tags": "graphs|data_structures", "min_solved": 50}, 
        6: {"tier": "17..18", "tags": "segment_tree|dijkstra",  "min_solved": 30}  
    }

    print("--- Reseeding Week Safely (10s delay) ---")
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        config = day_configs.get(current_date.weekday())
        
        success = select_with_retry(
            db, 
            current_date, 
            config["tier"], 
            config["tags"], 
            config["min_solved"]
        )
        
        if not success:
            print(f"CRITICAL FAIL: Could not find any problem for {current_date}")
        
        # 날짜 사이에도 추가 지연
        print("Cooling down 5s...")
        time.sleep(5)
            
    db.close()
    print("\n--- Safe Seeding Done ---")

if __name__ == "__main__":
    reset_and_reseed_safe()
