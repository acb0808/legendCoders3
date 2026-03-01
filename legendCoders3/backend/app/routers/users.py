import uuid
import re
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import schemas, models
from ..crud import crud as user_crud
from ..database import get_db
from ..auth import get_current_user, verify_password, create_access_token, create_refresh_token, ALGORITHM, SECRET_KEY
from datetime import timedelta
from jose import JWTError, jwt
import os
from .titles import grant_title_if_not_exists
from ..limiter import limiter

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# 백준 ID 검증 정규식 (알파벳, 숫자, 언더바만 허용, 2~20자)
BOJ_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_]{2,20}$")

@router.post("/", response_model=schemas.User)
@limiter.limit("5/minute")
async def create_user(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1. 백준 ID 형식 검증 (보안 및 데이터 무결성)
    if not BOJ_ID_PATTERN.match(user.baekjoon_id):
        raise HTTPException(status_code=400, detail="유효하지 않은 백준 아이디 형식입니다.")

    db_user = user_crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    db_user = user_crud.get_user_by_nickname(db, nickname=user.nickname)
    if db_user:
        raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다.")
    
    return user_crud.create_user(db=db, user=user)

@router.post("/token", response_model=schemas.Token)
@limiter.limit("10/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = user_crud.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=schemas.Token)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    user = user_crud.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
        
    new_access_token = create_access_token(data={"sub": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.get("/me/", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.is_pro:
        grant_title_if_not_exists(db, current_user.id, "레전드 프로")
    return current_user

@router.put("/me/", response_model=schemas.User)
async def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 관리자가 아닌 경우 baekjoon_id 수정을 제한
    if not current_user.is_admin:
        user_update.baekjoon_id = None
        
    return user_crud.update_user(db=db, user_id=current_user.id, user_update=user_update)
