# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,          # Increase base pool size
    max_overflow=10,       # Allow up to 10 extra connections
    pool_timeout=30,       # Wait up to 30s for a connection
    pool_recycle=1800,     # Recycle connections every 30m
    pool_pre_ping=True,    # Check connection validity before use
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
