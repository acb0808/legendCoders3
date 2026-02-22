# backend/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from . import schemas, models
from .crud import crud as user_crud # app.crud.crud 모듈을 user_crud로 임포트
from .database import get_db

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = 14 # 리프레시 토큰은 14일간 유효

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_token(data: dict, expires_delta: timedelta):
    """Access 또는 Refresh 토큰 생성 공용 함수"""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    if not expires_delta:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_token(data, expires_delta)

def create_refresh_token(data: dict):
    expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return create_token(data, expires_delta)

def get_user_from_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            print(f"WS Auth Error: No email in payload")
            return None
        user = user_crud.get_user_by_email(db, email=email)
        if not user:
            print(f"WS Auth Error: User with email {email} not found")
        return user
    except JWTError as e:
        print(f"WS Auth Error: JWT Decoding failed - {e}")
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = user_crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user
