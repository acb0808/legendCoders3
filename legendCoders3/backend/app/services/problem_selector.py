# backend/app/services/problem_selector.py
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
import random
import os
from dotenv import load_dotenv
from .. import crud
from ..schemas import DailyProblemCreate

load_dotenv()

BAEKJOON_URL = "https://www.acmicpc.net/problem/"
SOLVED_AC_API_URL = "https://solved.ac/api/v3/search/problem"

def get_problem_details_from_baekjoon(problem_id: int):
    """백준 사이트에서 문제의 HTML 설명을 크롤링합니다."""
    url = f"{BAEKJOON_URL}{problem_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.select_one("#problem_title").get_text(strip=True) if soup.select_one("#problem_title") else "제목 없음"
        description = str(soup.select_one("#problem_description")) if soup.select_one("#problem_description") else "설명 없음"
        input_example = soup.select_one(".sampledata[id^='sample-input']").get_text(strip=True) if soup.select_one(".sampledata[id^='sample-input']") else "입력 예시 없음"
        output_example = soup.select_one(".sampledata[id^='sample-output']").get_text(strip=True) if soup.select_one(".sampledata[id^='sample-output']") else "출력 예시 없음"

        info_table = soup.select_one("#problem-info")
        time_limit, memory_limit = 2000, 512
        if info_table:
            cols = info_table.find_all("td")
            if len(cols) >= 2:
                t_text = cols[0].get_text()
                if "초" in t_text:
                    try: time_limit = int(float(t_text.split(" ")[0]) * 1000)
                    except: pass
                m_text = cols[1].get_text()
                if "MB" in m_text:
                    try: memory_limit = int(m_text.split(" ")[0])
                    except: pass

        return {
            "title": title, "description": description,
            "input_example": input_example, "output_example": output_example,
            "time_limit_ms": time_limit, "memory_limit_mb": memory_limit,
        }
    except Exception as e:
        print(f"Baekjoon crawl error: {e}")
        return None

def fetch_problems_from_solved_ac(query: str):
    """목록을 더 많이 가져와서 강력하게 섞습니다."""
    all_items = []
    # 1~2페이지 정도를 가져와서 후보군을 넓힘
    for page in range(1, 3):
        params = {"query": query, "sort": "random", "page": page}
        try:
            response = requests.get(SOLVED_AC_API_URL, params=params, timeout=10)
            response.raise_for_status()
            items = response.json()["items"]
            if not items: break
            all_items.extend(items)
        except: break
    
    # 파이썬 레벨에서 한 번 더 무작위로 섞음
    random.shuffle(all_items)
    return all_items

def get_tier_name(level: int) -> str:
    if level == 0: return "Unrated"
    tiers = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Ruby"]
    
    # level 1..5 = Bronze, 6..10 = Silver, etc.
    tier_idx = (level - 1) // 5
    # sub_tier: level 1 -> 5 (V), level 5 -> 1 (I)
    sub_tier_num = 5 - (level - 1) % 5
    
    roman = ["I", "II", "III", "IV", "V"]
    # sub_tier_num 1 -> roman[0] ("I"), sub_tier_num 5 -> roman[4] ("V")
    return f"{tiers[tier_idx]} {roman[sub_tier_num - 1]}"

import time # time 임포트 추가

def select_daily_problem(db: Session, for_date: date):
    existing_problem = crud.daily_problems.get_daily_problem_by_date(db, for_date)
    if existing_problem: return existing_problem

    day_configs = {
        0: {"tier": "3..5",   "tags": "math|implementation", "min_solved": 300}, 
        1: {"tier": "6..8",   "tags": "greedy|string",       "min_solved": 200}, 
        2: {"tier": "9..10",  "tags": "bruteforce|sorting",  "min_solved": 150}, 
        3: {"tier": "11..12", "tags": "bfs|dfs",             "min_solved": 100}, 
        4: {"tier": "13..14", "tags": "dp|binary_search",    "min_solved": 80},  
        5: {"tier": "15..16", "tags": "graphs|data_structures", "min_solved": 50}, 
        6: {"tier": "17..18", "tags": "segment_tree|dijkstra",  "min_solved": 30}  
    }
    
    config = day_configs.get(for_date.weekday())
    
    # 1차 시도: 원래 조건으로 검색
    query = f"tier:{config['tier']} lang:ko s#{config['min_solved']}.. ({config['tags']})"
    print(f"[{for_date}] Attempt 1: {query}")
    candidates = fetch_problems_from_solved_ac(query)
    
    # 2차 시도: 실패 시 태그 제거 및 해결 수 기준 완화
    if not candidates:
        relaxed_min = max(10, config['min_solved'] // 3)
        query = f"tier:{config['tier']} lang:ko s#{relaxed_min}.."
        print(f"[{for_date}] Attempt 2 (Relaxed): {query}")
        candidates = fetch_problems_from_solved_ac(query)
    
    for cand in candidates:
        problem_id = cand["problemId"]
        if crud.daily_problems.get_daily_problem_by_baekjoon_id(db, problem_id): continue
            
        # 크롤링 전 매너 지연 (2초)
        time.sleep(2)
        
        details = get_problem_details_from_baekjoon(problem_id)
        if not details: continue
            
        new_problem = crud.daily_problems.create_daily_problem(db, DailyProblemCreate(
            problem_date=datetime.combine(for_date, datetime.min.time()),
            baekjoon_problem_id=problem_id,
            difficulty_level=get_tier_name(cand["level"]),
            algorithm_type=[tag["key"] for tag in cand.get("tags", [])],
            **details
        ))
        print(f"SUCCESS: {for_date} -> #{problem_id} {new_problem.title}")
        return new_problem
    
    return None
