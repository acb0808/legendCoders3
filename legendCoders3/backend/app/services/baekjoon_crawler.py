# backend/app/services/baekjoon_crawler.py
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from datetime import datetime, date, timedelta

BAEKJOON_STATUS_URL = "https://www.acmicpc.net/status"

def get_latest_solved_submission(baekjoon_id: str, problem_id: int) -> Optional[Dict[str, Any]]:
    """
    백준 사용자가 특정 문제를 풀었는지 확인하고, 가장 최근의 '맞았습니다' 제출 정보를 가져옵니다.
    제공해주신 유틸리티의 result_id=4 필터링 로직을 반영했습니다.
    """
    params = {
        "user_id": baekjoon_id,
        "problem_id": problem_id,
        "result_id": 4  # 맞았습니다!!
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(BAEKJOON_STATUS_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        status_table = soup.find("table", {"id": "status-table"})
        
        if not status_table:
            return None
            
        tbody = status_table.find("tbody")
        if not tbody:
            return None
            
        rows = tbody.find_all("tr")
        if len(rows) == 0:
            return None
            
        # 첫 번째 행(가장 최근 성공 제출) 정보 파싱
        first_row = rows[0]
        cols = first_row.find_all("td")
        
        # 백준 컬럼: 제출번호(0), 아이디(1), 문제(2), 결과(3), 메모리(4), 시간(5), 언어(6), 코드길이(7), 제출시간(8)
        submission_id = int(cols[0].get_text(strip=True))
        status_text = cols[3].get_text(strip=True)
        
        # 메모리 및 시간 파싱 (숫자만 추출)
        memory_text = cols[4].get_text(strip=True)
        memory_usage_kb = int(memory_text) if memory_text.isdigit() else None
        
        runtime_text = cols[5].get_text(strip=True)
        runtime_ms = int(runtime_text) if runtime_text.isdigit() else None
        
        language = cols[6].get_text(strip=True)
        
        # 제출 시간 추출 (유틸리티 로직 반영: a.real-time-update의 title 속성)
        time_elem = cols[8].find("a", {"class": "real-time-update"})
        submit_time = None
        if time_elem:
            time_str = time_elem.get("title", "")
            try:
                # 백준 시간 형식: "2024-01-15 14:30:00"
                submit_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        return {
            "baekjoon_submission_id": submission_id,
            "status": "Accepted",
            "result_message": status_text,
            "memory_usage_kb": memory_usage_kb,
            "runtime_ms": runtime_ms,
            "language": language,
            "submitted_at": submit_time or datetime.utcnow()
        }
        
    except Exception as e:
        print(f"Baekjoon crawl error for user {baekjoon_id}, problem {problem_id}: {e}")
        return None
