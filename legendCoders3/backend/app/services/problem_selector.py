# backend/app/services/problem_selector.py
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
import random
import os
from dotenv import load_dotenv

from .. import crud # crud 패키지 전체 임포트
from ..schemas import DailyProblemCreate

load_dotenv()

BAEKJOON_URL = "https://www.acmicpc.net/problem/"

# 임시 방편: 난이도별 문제 ID 목록 (실제로는 동적으로 가져오거나 더 정교한 DB 쿼리 사용)
# 여기서는 간단한 예시로 고정된 문제 ID 사용
# 실제 AI 로직은 난이도, 유형, 최근 출제 이력 등을 고려하여 구현됨
HARDCODED_PROBLEM_IDS_GOLD = [1000, 1001, 1002, 1003, 1004, 1005] # 예시
HARDCODED_PROBLEM_IDS_SILVER = [2000, 2001, 2002, 2003, 2004, 2005] # 예시

def get_problem_details_from_baekjoon(problem_id: int):
    url = f"{BAEKJOON_URL}{problem_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
    except requests.exceptions.RequestException as e:
        print(f"Error fetching problem {problem_id} from Baekjoon: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.select_one("#problem_title").get_text(strip=True) if soup.select_one("#problem_title") else "제목 없음"
    description = str(soup.select_one("#problem_description")) if soup.select_one("#problem_description") else "설명 없음"
    # 예시 입출력 파싱 (복잡하므로 간단히 첫 번째 예시만 가져오거나 더 정교하게 처리 필요)
    input_example_elem = soup.select_one(".sampledata[id^='sample-input']")
    input_example = input_example_elem.get_text(strip=True) if input_example_elem else "입력 예시 없음"

    output_example_elem = soup.select_one(".sampledata[id^='sample-output']")
    output_example = output_example_elem.get_text(strip=True) if output_example_elem else "출력 예시 없음"

    # 시간/메모리 제한 (파싱 로직은 백준 페이지 구조에 따라 달라질 수 있음)
    time_limit_ms = 2000 # 기본값 (파싱 어려우면 고정값 사용)
    memory_limit_mb = 512 # 기본값

    # 난이도 및 알고리즘 유형 (파싱이 복잡하므로 임시 값 사용)
    difficulty_level = "Gold V" # 임시
    algorithm_type = ["DP", "Graph"] # 임시

    return {
        "baekjoon_problem_id": problem_id,
        "title": title,
        "description": description,
        "input_example": input_example,
        "output_example": output_example,
        "time_limit_ms": time_limit_ms,
        "memory_limit_mb": memory_limit_mb,
        "difficulty_level": difficulty_level,
        "algorithm_type": algorithm_type,
    }


def select_daily_problem(db: Session, for_date: date):
    # 오늘 또는 이미 선정된 문제가 있는지 확인
    existing_problem = crud.daily_problems.get_daily_problem_by_date(db, for_date)
    if existing_problem:
        print(f"Problem already selected for {for_date}: {existing_problem.baekjoon_problem_id}")
        return existing_problem

    # AI 로직 (임시: 무작위 문제 선정)
    # 실제로는 난이도, 유형, 최근 출제 이력 등을 고려
    problem_ids_to_consider = HARDCODED_PROBLEM_IDS_GOLD + HARDCODED_PROBLEM_IDS_SILVER
    selected_id = random.choice(problem_ids_to_consider)
    
    # 문제 상세 정보 크롤링
    problem_details = get_problem_details_from_baekjoon(selected_id)
    
    if problem_details:
        daily_problem_create = DailyProblemCreate(
            problem_date=datetime.combine(for_date, datetime.min.time()),
            **problem_details
        )
        new_problem = crud.daily_problems.create_daily_problem(db, daily_problem_create)
        print(f"Successfully selected and saved problem {new_problem.baekjoon_problem_id} for {for_date}")
        return new_problem
    else:
        print(f"Failed to get details for problem {selected_id}. Skipping selection for {for_date}.")
        return None