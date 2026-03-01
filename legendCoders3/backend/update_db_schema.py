import os
import sys
from sqlalchemy import text

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine

def update_schema():
    with engine.connect() as conn:
        print("--- Adding streak_freeze_count to users ---")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS streak_freeze_count INTEGER DEFAULT 0"))
            conn.commit()
            print("Successfully added column.")
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()

if __name__ == "__main__":
    update_schema()
