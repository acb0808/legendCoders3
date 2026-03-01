from app.database import engine
from sqlalchemy import text

def add_is_admin_column():
    with engine.connect() as conn:
        print("Adding 'is_admin' column to 'users' table...")
        try:
            # 1. 컬럼 추가 (기본값 False)
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;"))
            
            # 2. 기존 테스트 계정(test@test.com)을 관리자로 승격
            conn.execute(text("UPDATE users SET is_admin = TRUE WHERE email = 'test@test.com';"))
            
            conn.commit()
            print("Successfully updated database schema and assigned admin role!")
        except Exception as e:
            print(f"Error updating database: {e}")
            conn.rollback()

if __name__ == "__main__":
    add_is_admin_column()
