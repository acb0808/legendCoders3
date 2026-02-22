# backend/app/services/arena_service.py
from sqlalchemy.orm import Session
from .. import crud, models
import uuid
from .problem_selector import fetch_problems_from_solved_ac
from .baekjoon_crawler import get_latest_solved_submission
import random
from datetime import datetime, timedelta # Added timedelta
import pytz

TIER_MAP = {
    "BRONZE": "1..5",
    "SILVER": "6..10",
    "GOLD": "11..15",
    "PLATINUM": "16..20",
    "DIAMOND": "21..25",
    "RUBY": "26..30",
    "RANDOM": "1..30"
}

def get_kst_now():
    return datetime.now(pytz.timezone('Asia/Seoul'))

def find_fair_problem_id(host_baekjoon_id: str, guest_baekjoon_id: str, difficulty: str):
    tier_range = TIER_MAP.get(difficulty)
    
    if difficulty == "RANDOM":
        # Random: Pick between Bronze~Platinum for fun
        tier_range = random.choice(["1..5", "6..10", "11..15", "16..20"])
    
    if not tier_range:
        tier_range = "6..10" # Default Silver

    # Query: Specific tier, Korean language, minimum 50 solves
    # AND NOT solved by host AND NOT solved by guest
    query = f"tier:{tier_range} lang:ko s#50.. !solved_by:{host_baekjoon_id} !solved_by:{guest_baekjoon_id}"
    print(f"[Arena] Searching: {query}")
    
    candidates = fetch_problems_from_solved_ac(query)
    
    if not candidates:
        # Fallback 1: Relax solved count
        query = f"tier:{tier_range} lang:ko !solved_by:{host_baekjoon_id} !solved_by:{guest_baekjoon_id}"
        print(f"[Arena] Retry 1: {query}")
        candidates = fetch_problems_from_solved_ac(query)
        
    if not candidates:
        # Fallback 2: Relax tier constraint slightly (not implemented for safety, just fail or pick really easy one)
        # Maybe just pick any unsolved by them?
        return None

    selected = random.choice(candidates)
    return selected["problemId"]

def verify_and_end_match(db: Session, arena_id: uuid.UUID, user_id: uuid.UUID):
    arena = crud.arena.get_arena(db, arena_id)
    if not arena or arena.status != "PLAYING":
        return False, "진행 중인 경기가 아닙니다."
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return False, "유저를 찾을 수 없습니다."
        
    # Check Baekjoon
    submission = get_latest_solved_submission(user.baekjoon_id, arena.baekjoon_problem_id)
    
    if submission and submission.get("status") == "Accepted":
        submit_time = submission.get("submitted_at")
        
        # Timezone handling
        if submit_time:
            if submit_time.tzinfo is None:
                submit_time = pytz.timezone('Asia/Seoul').localize(submit_time)
            
            arena_start = arena.start_time
            if arena_start.tzinfo is None:
                arena_start = pytz.timezone('Asia/Seoul').localize(arena_start)
                
            # Allow a 5-minute buffer for clock drift and slow starts
            verification_threshold = arena_start - timedelta(minutes=5)
                
            if submit_time >= verification_threshold:
                # Winner!
                updated_arena = crud.arena.finish_arena(db, arena_id, user_id)
                return True, "정답입니다! 승리하셨습니다!"
            else:
                print(f"[Arena] Submit time {submit_time} is before threshold {verification_threshold}")
                return False, "경기 시작 전에 제출된 기록입니다."
        else:
             return False, "제출 시간을 확인할 수 없습니다."

    return False, "아직 해결하지 못했습니다. (백준 반영에 시간이 걸릴 수 있습니다)"
