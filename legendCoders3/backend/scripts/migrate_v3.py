import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

sql = """
ALTER TABLE arenas
ADD COLUMN host_draw_agreed BOOLEAN DEFAULT FALSE,
ADD COLUMN guest_draw_agreed BOOLEAN DEFAULT FALSE,
ADD COLUMN host_skip_agreed BOOLEAN DEFAULT FALSE,
ADD COLUMN guest_skip_agreed BOOLEAN DEFAULT FALSE;
"""

with engine.connect() as conn:
    with conn.begin():
        conn.execute(text(sql))
    print("Migration successful!")
