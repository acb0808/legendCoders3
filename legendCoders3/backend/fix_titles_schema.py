import os
import sys
from sqlalchemy import text

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models import Title, UserTitle # 테이블 생성 확인을 위해 임포트

def fix_schema():
    with engine.connect() as conn:
        print("--- Force fixing 'users' table schema for Titles ---")
        try:
            # 1. 먼저 titles 테이블이 있는지 확인하고 없으면 생성
            Base.metadata.create_all(bind=engine)
            
            # 2. equipped_title_id 컬럼 추가
            # ALTER TABLE users ADD COLUMN IF NOT EXISTS equipped_title_id UUID
            # (PostgreSQL 문법에 맞춰 분리 실행)
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS equipped_title_id UUID"))
            
            # 3. 제약 조건 추가 (이미 존재할 수 있으므로 try-except)
            try:
                conn.execute(text("ALTER TABLE users ADD CONSTRAINT fk_user_equipped_title FOREIGN KEY (equipped_title_id) REFERENCES titles(id)"))
            except:
                print("Note: Constraint might already exist, skipping.")
            
            conn.commit()
            print("Successfully fixed database schema.")
        except Exception as e:
            print(f"Error updating schema: {e}")
            conn.rollback()

if __name__ == "__main__":
    fix_schema()
