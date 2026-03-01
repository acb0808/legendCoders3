import os
import sys
from sqlalchemy import text

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine

def fix_schema():
    with engine.connect() as conn:
        print("--- Force adding streak_freeze_count to 'users' table ---")
        try:
            # 1. 컬럼 추가
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS streak_freeze_count INTEGER DEFAULT 0"))
            
            # 2. 기존 데이터가 있다면 0으로 초기화 (혹시 모르니)
            conn.execute(text("UPDATE users SET streak_freeze_count = 0 WHERE streak_freeze_count IS NULL"))
            
            conn.commit()
            print("Successfully updated database schema.")
        except Exception as e:
            print(f"Error updating schema: {e}")
            conn.rollback()

if __name__ == "__main__":
    fix_schema()
