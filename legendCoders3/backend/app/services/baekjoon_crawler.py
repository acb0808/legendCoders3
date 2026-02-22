# backend/app/services/baekjoon_crawler.py
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from datetime import datetime, date, timedelta

BAEKJOON_STATUS_URL = "https://www.acmicpc.net/status"

import time # Added for timestamp cache busting

def get_latest_solved_submission(baekjoon_id: str, problem_id: int) -> Optional[Dict[str, Any]]:
    # 1. Restore result_id=4 for instant BOJ-side filtering (Fastest)
    # 2. Add cache buster to ensure fresh data
    timestamp = int(time.time() * 1000)
    url = f"{BAEKJOON_STATUS_URL}?user_id={baekjoon_id}&problem_id={problem_id}&result_id=4&_={timestamp}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    try:
        print(f"[BOJ Crawler] Fast-checking status for {baekjoon_id}...")
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        status_table = soup.find("table", {"id": "status-table"})
        
        if not status_table: return None
        tbody = status_table.find("tbody")
        if not tbody: return None
            
        rows = tbody.find_all("tr")
        if not rows:
            print(f"[BOJ Crawler] No 'Accepted' results yet for {baekjoon_id}")
            return None
        
        # Since we filtered by result_id=4, the first row IS the latest success
        cols = rows[0].find_all("td")
        if len(cols) < 9: return None
        
        status_text = cols[3].get_text(strip=True)
        # Extra safety check using BOJ's specific success class
        is_success = "맞았습니다" in status_text or cols[3].find(class_="result-ac")
        
        if is_success:
            submission_id = int(cols[0].get_text(strip=True))
            memory_usage_kb = int(cols[4].get_text(strip=True)) if cols[4].get_text(strip=True).isdigit() else None
            runtime_ms = int(cols[5].get_text(strip=True)) if cols[5].get_text(strip=True).isdigit() else None
            language = cols[6].get_text(strip=True)
            
            time_elem = cols[8].find("a", {"class": "real-time-update"})
            submit_time = None
            if time_elem:
                try:
                    submit_time = datetime.strptime(time_elem.get("title", ""), "%Y-%m-%d %H:%M:%S")
                except: pass
            
            print(f"[BOJ Crawler] SUCCESS: Found {submission_id}")
            return {
                "baekjoon_submission_id": submission_id,
                "status": "Accepted",
                "result_message": status_text,
                "memory_usage_kb": memory_usage_kb,
                "runtime_ms": runtime_ms,
                "language": language,
                "submitted_at": submit_time or datetime.utcnow()
            }
            
        return None
    except Exception as e:
        print(f"Baekjoon fast-crawl error: {e}")
        return None
