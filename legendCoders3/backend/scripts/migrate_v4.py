import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

sql = """
ALTER TABLE arenas
ADD COLUMN mode VARCHAR DEFAULT 'OPEN';
"""

try:
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text(sql))
    print("Migration (add mode column) successful!")
except Exception as e:
    print(f"Migration failed or column already exists: {e}")
