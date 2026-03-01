from app.database import engine
from sqlalchemy import text

def update_foreign_key():
    with engine.connect() as conn:
        print("Updating foreign key constraint for invitation_codes...")
        # 기존 제약 조건 삭제 후 ON DELETE SET NULL 추가
        conn.execute(text("""
            ALTER TABLE invitation_codes 
            DROP CONSTRAINT IF EXISTS invitation_codes_used_by_user_id_fkey;
        """))
        conn.execute(text("""
            ALTER TABLE invitation_codes 
            ADD CONSTRAINT invitation_codes_used_by_user_id_fkey 
            FOREIGN KEY (used_by_user_id) REFERENCES users(id) 
            ON DELETE SET NULL;
        """))
        conn.commit()
        print("Successfully updated constraint!")

if __name__ == "__main__":
    update_foreign_key()
