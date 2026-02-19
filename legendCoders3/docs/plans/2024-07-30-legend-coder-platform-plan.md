# 레전드 코더 플랫폼 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** AI 기반 백준 문제 추천, 크롤링 기반 채점 결과 연동, 커뮤니티 및 랭킹 기능을 포함하는 레전드 코더 플랫폼을 구축합니다.

**Architecture:** 프론트엔드(React/Next.js), 백엔드(Python FastAPI), PostgreSQL 데이터베이스로 분리된 API 기반 마이크로서비스 아키텍처를 채택합니다.

**Tech Stack:** React.js (TypeScript), Next.js, Tailwind CSS, Python (FastAPI), PostgreSQL, BeautifulSoup/requests/Selenium (웹 크롤링), Pandas/scikit-learn (AI 문제 선정).

---

### Task 1: 백엔드 프로젝트 초기 설정 (Python FastAPI)

**Goal:** FastAPI 프로젝트의 기본 구조를 설정하고, 가상 환경을 구축하며, 필요한 초기 의존성 라이브러리를 설치합니다.

**Files:**
- Create: `backend/README.md`
- Create: `backend/requirements.txt`
- Create: `backend/main.py`
- Create: `backend/.env`
- Create: `backend/app/` (directory)

**Step 1: 백엔드 디렉토리 생성 및 가상 환경 설정**

```bash
mkdir backend
cd backend
python -m venv venv
./venv/Scripts/activate # Windows
# source venv/bin/activate # Linux/macOS
```
Expected: `backend` 디렉토리와 그 안에 `venv` 디렉토리가 생성됩니다.

**Step 2: 초기 의존성 설치**

```bash
pip install fastapi uvicorn python-dotenv
```
Expected: `fastapi`, `uvicorn`, `python-dotenv` 라이브러리가 설치됩니다.

**Step 3: `requirements.txt` 파일 생성**

```bash
pip freeze > requirements.txt
```
Expected: `requirements.txt` 파일에 현재 가상 환경의 의존성 목록이 기록됩니다.

**Step 4: `main.py` (FastAPI 앱 엔트리 포인트) 생성**

```python
# backend/main.py
from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv() # .env 파일에서 환경 변수 로드

app = FastAPI(title="Legend Coder Platform API")

@app.get("/")
async def root():
    return {"message": "Welcome to Legend Coder Platform API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```
Expected: `main.py` 파일이 생성됩니다.

**Step 5: `.env` 파일 생성**

```bash
# backend/.env
PORT=8000
DATABASE_URL="postgresql://user:password@localhost:5432/legendcoder"
```
Expected: `.env` 파일이 생성되며 기본 환경 변수가 포함됩니다.

**Step 6: FastAPI 애플리케이션 실행 및 테스트**

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Expected: FastAPI 서버가 시작되고, 웹 브라우저에서 `http://localhost:8000`에 접속하면 `{"message": "Welcome to Legend Coder Platform API"}` 메시지가 표시됩니다. (Ctrl+C로 종료)

**Step 7: `README.md` 파일 생성**

```markdown
# Legend Coder Platform Backend

This is the backend for the Legend Coder Platform, built with FastAPI.

## Setup

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # Windows
    ./venv/Scripts/activate
    # Linux/macOS
    # source venv/bin/activate
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure environment variables:**
    Create a `.env` file in the `backend` directory with the following content:
    ```
    PORT=8000
    DATABASE_URL="postgresql://user:password@localhost:5432/legendcoder"
    ```
4.  **Run the application:**
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    The API documentation will be available at `http://localhost:8000/docs`.

---
```
Expected: `backend/README.md` 파일이 생성됩니다.

**Step 8: Commit**

```bash
git add backend/
git commit -m "feat: Initial backend project setup with FastAPI"
```

### Task 2: 데이터베이스 및 ORM 설정 (PostgreSQL & SQLAlchemy)

**Goal:** PostgreSQL 데이터베이스 연결을 설정하고, SQLAlchemy를 ORM으로 사용하여 데이터베이스 모델을 정의하고 마이그레이션 도구(Alembic)를 통합합니다.

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/database.py`
- Create: `backend/models.py`
- Create: `alembic.ini`
- Create: `backend/alembic/` (directory for migrations)

**Step 1: 필요한 의존성 설치**

```bash
pip install sqlalchemy psycopg2-binary alembic
```
Expected: `sqlalchemy`, `psycopg2-binary`, `alembic` 라이브러리가 설치됩니다.

**Step 2: `requirements.txt` 업데이트**

```bash
pip freeze > requirements.txt
```
Expected: `requirements.txt` 파일에 새로 설치된 의존성이 추가됩니다.

**Step 3: `database.py` 파일 생성 (DB 연결 및 세션 관리)**

```python
# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
Expected: `backend/database.py` 파일이 생성됩니다.

**Step 4: `models.py` 파일 생성 (데이터베이스 모델 정의)**

```python
# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import uuid

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nickname = Column(String, unique=True, index=True, nullable=False)
    baekjoon_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    submissions = relationship("Submission", back_populates="user")
    posts = relationship("Post", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")

class DailyProblem(Base):
    __tablename__ = "daily_problems"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_date = Column(DateTime(timezone=True), unique=True, index=True, nullable=False)
    baekjoon_problem_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    input_example = Column(Text, nullable=False)
    output_example = Column(Text, nullable=False)
    time_limit_ms = Column(Integer, nullable=False)
    memory_limit_mb = Column(Integer, nullable=False)
    difficulty_level = Column(String, nullable=False)
    algorithm_type = Column(ARRAY(String), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    submissions = relationship("Submission", back_populates="daily_problem")
    posts = relationship("Post", back_populates="daily_problem")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    daily_problem_id = Column(UUID(as_uuid=True), ForeignKey("daily_problems.id"), nullable=False)
    baekjoon_problem_id = Column(Integer, nullable=False)
    baekjoon_submission_id = Column(Integer, unique=True, index=True, nullable=False)
    language = Column(String, nullable=False)
    code = Column(Text, nullable=True) # 크롤링 실패 시 None 가능
    status = Column(String, nullable=False)
    result_message = Column(String, nullable=True)
    runtime_ms = Column(Integer, nullable=True)
    memory_usage_kb = Column(Integer, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now()) # 플랫폼 등록 시각

    user = relationship("User", back_populates="submissions")
    daily_problem = relationship("DailyProblem", back_populates="submissions")

class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    daily_problem_id = Column(UUID(as_uuid=True), ForeignKey("daily_problems.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(ARRAY(String), nullable=True)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="posts")
    daily_problem = relationship("DailyProblem", back_populates="posts")
    comments = relationship("Comment", back_populates="post")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True) # Self-referencing for replies
    content = Column(Text, nullable=False)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    replies = relationship("Comment", backref="parent_comment", remote_side=[id]) # for replies

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=False)
    criteria = Column(JSON, nullable=False) # {'type': 'solved_count', 'value': 1}
    icon_url = Column(String, nullable=True)

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    achievement_id = Column(UUID(as_uuid=True), ForeignKey("achievements.id"), primary_key=True)
    achieved_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")

# UserStats는 User 모델에 통합하거나 별도 테이블로 관리 가능. 여기서는 User 모델 내부에 필드로 추가하는 것으로 간주.
# 복잡도 관리 및 랭킹 성능을 위해 User 모델에 관련 필드를 직접 추가하는 것을 고려합니다.
# 예를 들어, User 모델에 total_solved_count, consecutive_days 등을 추가.
# 또는 UserStats 테이블을 별도로 만들어 user_id와 1대1 관계를 맺을 수 있습니다.
# 현재 모델에서는 User.submissions 를 통해 통계 계산이 가능하므로 별도 테이블은 우선 생략.
# 랭킹 시스템 구현 시 효율적인 쿼리를 위해 통계성 필드는 필요에 따라 추가될 수 있음.

```
Expected: `backend/models.py` 파일이 생성됩니다.

**Step 5: Alembic 초기화 및 설정**

```bash
alembic init alembic
```
Expected: `alembic` 디렉토리와 `alembic.ini` 파일이 생성됩니다.

**Step 6: `alembic.ini` 수정하여 `target_metadata` 설정**

`alembic.ini` 파일을 열고 `sqlalchemy.url`을 `DATABASE_URL` 환경 변수를 사용하도록 변경합니다 (이 부분은 Alembic 환경 스크립트에서 처리).
또한, `env.py` 파일에서 `target_metadata`를 `models.Base.metadata`로 지정하도록 수정해야 합니다.

`alembic/env.py` 파일을 열고 다음 라인을 찾습니다:
```python
# target_metadata = None
```
이것을 다음으로 변경합니다:
```python
from app.models import Base
target_metadata = Base.metadata
```
그리고 `run_migrations_online` 함수 내에서 `config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))` 라인을 추가합니다.

**Step 7: 첫 번째 마이그레이션 생성**

```bash
alembic revision --autogenerate -m "Create initial tables"
```
Expected: `alembic/versions/` 디렉토리에 첫 번째 마이그레이션 파일이 생성됩니다.

**Step 8: 데이터베이스 스키마 적용**

(PostgreSQL 서버가 실행 중이어야 합니다. `.env`의 `DATABASE_URL`을 실제 DB 설정에 맞게 변경해야 합니다.)

```bash
alembic upgrade head
```
Expected: 데이터베이스에 `users`, `daily_problems`, `submissions`, `posts`, `comments`, `achievements`, `user_achievements` 테이블이 생성됩니다.

**Step 9: Commit**

```bash
git add backend/requirements.txt backend/database.py backend/models.py alembic/ alembic.ini
git commit -m "feat: Setup PostgreSQL, SQLAlchemy ORM, and Alembic migrations"
```

### Task 3: 사용자 인증 API 구현

**Goal:** 사용자 회원가입, 로그인, 현재 사용자 정보 조회 API 엔드포인트를 구현합니다. JWT(JSON Web Token)를 사용하여 사용자 인증을 처리합니다.

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/schemas.py`
- Create: `backend/crud.py`
- Create: `backend/auth.py`
- Create: `backend/routers/users.py`
- Modify: `backend/main.py`
- Modify: `backend/.env`

**Step 1: 필요한 의존성 설치**

```bash
pip install passlib[bcrypt] python-jose[cryptography]
```
Expected: `passlib` (bcrypt 포함), `python-jose` (cryptography 포함) 라이브러리가 설치됩니다.

**Step 2: `requirements.txt` 업데이트**

```bash
pip freeze > requirements.txt
```
Expected: `requirements.txt` 파일에 새로 설치된 의존성이 추가됩니다.

**Step 3: `schemas.py` 파일 생성 (Pydantic 모델 정의)**

```python
# backend/schemas.py
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import uuid

class UserBase(BaseModel):
    email: EmailStr
    nickname: str
    baekjoon_id: str

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None
    email: Optional[EmailStr] = None
    nickname: Optional[str] = None
    baekjoon_id: Optional[str] = None

class User(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# DailyProblem, Submission, Post, Comment 등에 대한 스키마도 추가 예정
```
Expected: `backend/schemas.py` 파일이 생성됩니다.

**Step 4: `crud.py` 파일 생성 (데이터베이스 작업 함수 정의)**

```python
# backend/crud.py
from sqlalchemy.orm import Session
from . import models, schemas
from .auth import get_password_hash # get_password_hash는 auth.py에서 가져옴

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_nickname(db: Session, nickname: str):
    return db.query(models.User).filter(models.User.nickname == nickname).first()

def get_user(db: Session, user_id: uuid.UUID):
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        password_hash=hashed_password,
        nickname=user.nickname,
        baekjoon_id=user.baekjoon_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
```
Expected: `backend/crud.py` 파일이 생성됩니다.

**Step 5: `auth.py` 파일 생성 (인증 헬퍼 함수 및 JWT 로직 정의)**

```python
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

from . import schemas, crud, models
from .database import get_db

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user
```
Expected: `backend/auth.py` 파일이 생성됩니다.

**Step 6: `routers/users.py` 파일 생성 (사용자 관련 API 엔드포인트)**

```python
# backend/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import schemas, crud, models
from ..database import get_db
from ..auth import get_current_user, verify_password, create_access_token
from datetime import timedelta
import os

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

@router.post("/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = crud.get_user_by_nickname(db, nickname=user.nickname)
    if db_user:
        raise HTTPException(status_code=400, detail="Nickname already taken")
    return crud.create_user(db=db, user=user)

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: schemas.UserCreate, db: Session = Depends(get_db)): # Simplified for now
    user = crud.get_user_by_email(db, email=form_data.email)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me/", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user
```
Expected: `backend/routers/users.py` 파일이 생성됩니다.

**Step 7: `main.py`에 라우터 포함**

`backend/main.py` 파일을 열고 다음 라인을 추가하여 `users` 라우터를 앱에 포함시킵니다:

```python
# backend/main.py
from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv

from .routers import users # 추가

load_dotenv()

app = FastAPI(title="Legend Coder Platform API")

app.include_router(users.router) # 추가

@app.get("/")
async def root():
    return {"message": "Welcome to Legend Coder Platform API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```
Expected: `main.py`가 업데이트되어 사용자 라우터를 포함합니다.

**Step 8: `.env` 파일에 JWT 비밀 키 추가**

```bash
# backend/.env
PORT=8000
DATABASE_URL="postgresql://user:password@localhost:5432/legendcoder"
SECRET_KEY="your-super-secret-key" # 실제 배포 시에는 더 강력한 키 사용 권장
ACCESS_TOKEN_EXPIRE_MINUTES=30
```
Expected: `.env` 파일에 `SECRET_KEY` 및 `ACCESS_TOKEN_EXPIRE_MINUTES` 환경 변수가 추가됩니다.

**Step 9: API 테스트**

(FastAPI 서버 실행: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`)
웹 브라우저에서 `http://localhost:8000/docs`에 접속하여 Swagger UI를 통해 다음을 테스트합니다:
1.  `POST /users/` (사용자 생성)
2.  `POST /users/token` (로그인 및 토큰 발급)
3.  `GET /users/me/` (토큰을 이용하여 현재 사용자 정보 조회)

**Step 10: Commit**

```bash
git add backend/requirements.txt backend/schemas.py backend/crud.py backend/auth.py backend/routers/users.py backend/main.py backend/.env
git add backend/requirements.txt backend/schemas.py backend/crud.py backend/auth.py backend/routers/users.py backend/main.py backend/.env
git commit -m "feat: Implement user authentication with registration, login, and profile"
```

### Task 4: AI 기반 문제 선정 API 구현

**Goal:** AI 기반으로 백준 문제를 선정하고 저장하며, 오늘의 문제 정보를 제공하는 API 엔드포인트를 구현합니다.

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/crud/daily_problems.py`
- Create: `backend/app/services/problem_selector.py`
- Modify: `backend/app/schemas.py` (Pydantic schemas for daily problems)
- Create: `backend/app/routers/daily_problems.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/tasks/scheduler.py` (for daily scheduling)

**Step 1: 필요한 의존성 설치**

```bash
pip install requests beautifulsoup4 apscheduler pytz
```
Expected: `requests`, `beautifulsoup4`, `apscheduler`, `pytz` 라이브러리가 설치됩니다.

**Step 2: `requirements.txt` 업데이트**

```bash
pip freeze > backend/requirements.txt
```
Expected: `backend/requirements.txt` 파일에 새로 설치된 의존성이 추가됩니다.

**Step 3: `backend/app/schemas.py` 파일 업데이트 (DailyProblem 스키마 추가)**

`backend/app/schemas.py` 파일을 열고 아래 `DailyProblemBase`, `DailyProblemCreate`, `DailyProblem` Pydantic 모델을 추가합니다.

```python
# backend/app/schemas.py (기존 내용에 추가)
# ... (기존 User, Token 등 스키마)

class DailyProblemBase(BaseModel):
    problem_date: datetime
    baekjoon_problem_id: int
    title: str
    description: str
    input_example: str
    output_example: str
    time_limit_ms: int
    memory_limit_mb: int
    difficulty_level: str
    algorithm_type: List[str]

class DailyProblemCreate(DailyProblemBase):
    pass

class DailyProblem(DailyProblemBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True
```
Expected: `backend/app/schemas.py` 파일이 업데이트됩니다.

**Step 4: `backend/app/crud/daily_problems.py` 파일 생성 (DailyProblem CRUD)**

`backend/app/crud` 디렉토리가 없으므로 먼저 생성합니다.

```bash
mkdir backend/app/crud
```

`backend/app/crud/daily_problems.py` 파일의 내용은 다음과 같습니다.

```python
# backend/app/crud/daily_problems.py
from sqlalchemy.orm import Session
from datetime import date, datetime
from .. import models, schemas

def get_daily_problem_by_date(db: Session, problem_date: date):
    return db.query(models.DailyProblem).filter(
        models.DailyProblem.problem_date == problem_date
    ).first()

def get_daily_problem_by_baekjoon_id(db: Session, baekjoon_problem_id: int):
    return db.query(models.DailyProblem).filter(
        models.DailyProblem.baekjoon_problem_id == baekjoon_problem_id
    ).first()

def create_daily_problem(db: Session, daily_problem: schemas.DailyProblemCreate):
    db_problem = models.DailyProblem(
        problem_date=daily_problem.problem_date,
        baekjoon_problem_id=daily_problem.baekjoon_problem_id,
        title=daily_problem.title,
        description=daily_problem.description,
        input_example=daily_problem.input_example,
        output_example=daily_problem.output_example,
        time_limit_ms=daily_problem.time_limit_ms,
        memory_limit_mb=daily_problem.memory_limit_mb,
        difficulty_level=daily_problem.difficulty_level,
        algorithm_type=daily_problem.algorithm_type,
    )
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)
    return db_problem
```
Expected: `backend/app/crud/daily_problems.py` 파일이 생성됩니다.

**Step 5: `backend/app/services/problem_selector.py` 파일 생성 (AI 문제 선정 로직)**

이 파일은 백준 웹사이트에서 문제 정보를 가져오고, AI 로직에 따라 문제를 선정하는 기능을 담당합니다. (최초 버전은 간단한 무작위 선택 후 상세 정보 크롤링으로 시작)

```python
# backend/app/services/problem_selector.py
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
import random
import os
from dotenv import load_dotenv

from .. import crud # crud 패키지 전체 임포트
from ..schemas import DailyProblemCreate

load_dotenv()

BAEKJOON_URL = "https://www.acmicpc.net/problem/"

# 임시 방편: 난이도별 문제 ID 목록 (실제로는 동적으로 가져오거나 더 정교한 DB 쿼리 사용)
# 여기서는 간단한 예시로 고정된 문제 ID 사용
# 실제 AI 로직은 난이도, 유형, 최근 출제 이력 등을 고려하여 구현됨
HARDCODED_PROBLEM_IDS_GOLD = [1000, 1001, 1002, 1003, 1004, 1005] # 예시
HARDCODED_PROBLEM_IDS_SILVER = [2000, 2001, 2002, 2003, 2004, 2005] # 예시

def get_problem_details_from_baekjoon(problem_id: int):
    url = f"{BAEKJOON_URL}{problem_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
    except requests.exceptions.RequestException as e:
        print(f"Error fetching problem {problem_id} from Baekjoon: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.select_one("#problem_title").get_text(strip=True) if soup.select_one("#problem_title") else "제목 없음"
    description = str(soup.select_one("#problem_description")) if soup.select_one("#problem_description") else "설명 없음"
    # 예시 입출력 파싱 (복잡하므로 간단히 첫 번째 예시만 가져오거나 더 정교하게 처리 필요)
    input_example_elem = soup.select_one(".sampledata[id^='sample-input']")
    input_example = input_example_elem.get_text(strip=True) if input_example_elem else "입력 예시 없음"

    output_example_elem = soup.select_one(".sampledata[id^='sample-output']")
    output_example = output_example_elem.get_text(strip=True) if output_example_elem else "출력 예시 없음"

    # 시간/메모리 제한 (파싱 로직은 백준 페이지 구조에 따라 달라질 수 있음)
    time_limit_ms = 2000 # 기본값 (파싱 어려우면 고정값 사용)
    memory_limit_mb = 512 # 기본값

    # 난이도 및 알고리즘 유형 (파싱이 복잡하므로 임시 값 사용)
    difficulty_level = "Gold V" # 임시
    algorithm_type = ["DP", "Graph"] # 임시

    return {
        "baekjoon_problem_id": problem_id,
        "title": title,
        "description": description,
        "input_example": input_example,
        "output_example": output_example,
        "time_limit_ms": time_limit_ms,
        "memory_limit_mb": memory_limit_mb,
        "difficulty_level": difficulty_level,
        "algorithm_type": algorithm_type,
    }


def select_daily_problem(db: Session, for_date: date):
    # 오늘 또는 이미 선정된 문제가 있는지 확인
    existing_problem = crud.daily_problems.get_daily_problem_by_date(db, for_date)
    if existing_problem:
        print(f"Problem already selected for {for_date}: {existing_problem.baekjoon_problem_id}")
        return existing_problem

    # AI 로직 (임시: 무작위 문제 선정)
    # 실제로는 난이도, 유형, 최근 출제 이력 등을 고려
    problem_ids_to_consider = HARDCODED_PROBLEM_IDS_GOLD + HARDCODED_PROBLEM_IDS_SILVER
    selected_id = random.choice(problem_ids_to_consider)
    
    # 문제 상세 정보 크롤링
    problem_details = get_problem_details_from_baekjoon(selected_id)
    
    if problem_details:
        daily_problem_create = DailyProblemCreate(
            problem_date=datetime.combine(for_date, datetime.min.time()),
            **problem_details
        )
        new_problem = crud.daily_problems.create_daily_problem(db, daily_problem_create)
        print(f"Successfully selected and saved problem {new_problem.baekjoon_problem_id} for {for_date}")
        return new_problem
    else:
        print(f"Failed to get details for problem {selected_id}. Skipping selection for {for_date}.")
        return None
```
Expected: `backend/app/services/problem_selector.py` 파일이 생성됩니다.

**Step 6: `backend/app/routers/daily_problems.py` 파일 생성 (일일 문제 API 엔드포인트)**

`backend/app/routers` 디렉토리는 이미 존재합니다.

```python
# backend/app/routers/daily_problems.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime
from .. import schemas, crud
from ..database import get_db

router = APIRouter(
    prefix="/daily-problems",
    tags=["daily-problems"],
    responses={404: {"description": "Not found"}},
)

@router.get("/today", response_model=schemas.DailyProblem)
def get_today_problem(db: Session = Depends(get_db)):
    today = date.today()
    problem = crud.daily_problems.get_daily_problem_by_date(db, today)
    if not problem:
        # TODO: AI 문제 선정 로직을 여기서 트리거하거나 스케줄러가 이미 실행했다고 가정
        # for_date = datetime.utcnow().date() + timedelta(days=1) # 다음날 문제 선정
        raise HTTPException(status_code=404, detail="No problem selected for today yet.")
    return problem

@router.get("/{problem_date}", response_model=schemas.DailyProblem)
def get_problem_by_date(problem_date: date, db: Session = Depends(get_db)):
    problem = crud.daily_problems.get_daily_problem_by_date(db, problem_date)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found for this date.")
    return problem
```
Expected: `backend/app/routers/daily_problems.py` 파일이 생성됩니다.

**Step 7: `backend/app/main.py` 파일 업데이트 (daily_problems 라우터 포함)**

`backend/app/main.py` 파일을 열고 `daily_problems` 라우터를 앱에 포함시킵니다.

```python
# backend/app/main.py (기존 내용에 추가)
from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv

from .routers import users, daily_problems # daily_problems 추가

load_dotenv()

app = FastAPI(title="Legend Coder Platform API")

app.include_router(users.router)
app.include_router(daily_problems.router) # daily_problems 라우터 포함

@app.get("/")
async def root():
    return {"message": "Welcome to Legend Coder Platform API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```
Expected: `backend/app/main.py` 파일이 업데이트됩니다.

**Step 8: `backend/app/tasks/scheduler.py` 파일 생성 (일일 문제 선정 스케줄러)**

```python
# backend/app/tasks/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, timedelta
import pytz # 시간대 처리를 위해 필요
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..services.problem_selector import select_daily_problem

# 한국 시간대 설정
SEOUL_TZ = pytz.timezone("Asia/Seoul")

def schedule_daily_problem_selection():
    """매일 정해진 시간에 문제 선정을 스케줄링하는 함수."""
    # Scheduler 인스턴스 생성
    scheduler = BackgroundScheduler(timezone=SEOUL_TZ)

    # 매일 12시 KST에 다음 날 문제 선정 (예: 오늘 12시에 내일 문제 선정)
    # CronTrigger: year, month, day, week, day_of_week, hour, minute, second
    # hour=12, minute=0, second=0
    trigger = CronTrigger(hour=12, minute=0, second=0, timezone=SEOUL_TZ)
    
    # job_id를 명시하여 중복 등록 방지
    scheduler.add_job(
        select_and_save_problem,
        trigger,
        id="daily_problem_selection_job",
        replace_existing=True,
        args=[] # 이 잡은 직접 DB 세션을 생성하여 사용
    )

    # 스케줄러 시작
    scheduler.start()
    print("Scheduler started for daily problem selection.")
    return scheduler

def select_and_save_problem():
    """스케줄링된 작업: 다음 날의 문제를 선정하고 DB에 저장."""
    db: Session = SessionLocal()
    try:
        # 오늘 날짜를 기준으로 다음 날의 문제를 선정 (예: 7/30 12시 -> 7/31 문제 선정)
        target_date = datetime.now(SEOUL_TZ).date() + timedelta(days=1)
        print(f"Attempting to select daily problem for {target_date}...")
        select_daily_problem(db, for_date=target_date)
    except Exception as e:
        print(f"Error in scheduled daily problem selection: {e}")
    finally:
        db.close()

def start_scheduler():
    # 애플리케이션 시작 시 스케줄러 초기화 및 시작
    global scheduler_instance
    scheduler_instance = schedule_daily_problem_selection()
    # 애플리케이션 시작 시 오늘 문제가 없으면 오늘 문제도 한번 선정 시도 (선택 사항)
    # db_temp: Session = SessionLocal()
    # try:
    #     today = datetime.now(SEOUL_TZ).date()
    #     if not crud.daily_problems.get_daily_problem_by_date(db_temp, today):
    #         print(f"No problem for today ({today}). Attempting to select it now...")
    #         select_daily_problem(db_temp, for_date=today)
    # except Exception as e:
    #     print(f"Error selecting today's problem at startup: {e}")
    # finally:
    #     db_temp.close()


```
Expected: `backend/app/tasks/scheduler.py` 파일이 생성됩니다.

**Step 9: `backend/app/main.py` 파일 업데이트 (스케줄러 시작)**

`backend/app/main.py` 파일을 열고 애플리케이션 시작 시 스케줄러를 시작하도록 수정합니다.

```python
# backend/app/main.py (기존 내용에 추가)
from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv

from .routers import users, daily_problems
from .tasks.scheduler import start_scheduler # 스케줄러 임포트

load_dotenv()

app = FastAPI(title="Legend Coder Platform API")

app.include_router(users.router)
app.include_router(daily_problems.router)

@app.on_event("startup")
async def startup_event():
    print("Starting up application...")
    start_scheduler() # 애플리케이션 시작 시 스케줄러 시작

@app.get("/")
async def root():
    return {"message": "Welcome to Legend Coder Platform API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```
Expected: `backend/app/main.py` 파일이 업데이트됩니다.

**Step 10: API 테스트**

(FastAPI 서버 실행: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`)
웹 브라우저에서 `http://localhost:8000/docs`에 접속하여 Swagger UI를 통해 다음을 테스트합니다:
1.  `GET /daily-problems/today` (오늘의 문제 조회)
2.  `GET /daily-problems/{problem_date}` (특정 날짜 문제 조회)

(참고: `select_daily_problem`은 매일 12시에 실행되므로, 테스트를 위해 수동으로 DB에 문제를 삽입하거나 `select_and_save_problem()` 함수를 한 번 실행해볼 수 있습니다.)

**Step 11: Commit**

```bash
git add backend/requirements.txt backend/app/schemas.py backend/app/crud/daily_problems.py backend/app/services/problem_selector.py backend/app/routers/daily_problems.py backend/app/main.py backend/app/tasks/scheduler.py backend/app/crud/
git commit -m "feat: Implement AI-driven daily problem selection and API"
```

### Task 5: 제출 결과 등록 및 채점 (Submission Result Registration & Judging)

**Goal:** 사용자가 백준에 직접 제출한 문제의 결과를 플랫폼에 등록하고, 백준 웹사이트를 크롤링하여 채점 결과를 가져와 저장하는 API 엔드포인트를 구현합니다.

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/crud/submissions.py`
- Create: `backend/app/services/baekjoon_crawler.py`
- Modify: `backend/app/schemas.py` (Pydantic schemas for submissions)
- Create: `backend/app/routers/submissions.py`
- Modify: `backend/app/main.py`
- Create: `backend/app/tasks/submission_processor.py` (Optional: for background processing of submission results)

**Step 1: 필요한 의존성 설치**

```bash
pip install requests beautifulsoup4 # 이미 설치됨. 필요 시 재확인.
```
Expected: `requests`, `beautifulsoup4` 라이브러리가 설치되어 있거나 최신 상태입니다.

**Step 2: `backend/app/schemas.py` 파일 업데이트 (Submission 스키마 추가)**

`backend/app/schemas.py` 파일을 열고 아래 `SubmissionBase`, `SubmissionCreate`, `Submission` Pydantic 모델을 추가합니다.

```python
# backend/app/schemas.py (기존 내용에 추가)
# ... (기존 User, DailyProblem 등 스키마)

class SubmissionBase(BaseModel):
    daily_problem_id: uuid.UUID
    baekjoon_submission_id: int
    language: str
    code: Optional[str] = None # 크롤링 실패 시 None 가능
    status: str
    result_message: Optional[str] = None
    runtime_ms: Optional[int] = None
    memory_usage_kb: Optional[int] = None
    submitted_at: datetime # 백준 제출 시각 또는 플랫폼 등록 시각

class SubmissionCreate(SubmissionBase):
    pass

class Submission(SubmissionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    baekjoon_problem_id: int # Submission 모델에 baekjoon_problem_id 추가 (편의상)
    
    class Config:
        orm_mode = True

class SubmissionRegisterRequest(BaseModel):
    daily_problem_id: uuid.UUID
    baekjoon_submission_id: int # 사용자가 직접 입력하는 백준 제출 ID
```
Expected: `backend/app/schemas.py` 파일이 업데이트됩니다.

**Step 3: `backend/app/crud/submissions.py` 파일 생성 (Submission CRUD)**

`backend/app/crud` 디렉토리는 이미 존재합니다.

```python
# backend/app/crud/submissions.py
from sqlalchemy.orm import Session
from .. import models, schemas
from datetime import datetime
import uuid

def get_submission(db: Session, submission_id: uuid.UUID):
    return db.query(models.Submission).filter(models.Submission.id == submission_id).first()

def get_user_submissions_for_problem(db: Session, user_id: uuid.UUID, daily_problem_id: uuid.UUID):
    return db.query(models.Submission).filter(
        models.Submission.user_id == user_id,
        models.Submission.daily_problem_id == daily_problem_id
    ).all()

def create_submission(db: Session, user_id: uuid.UUID, submission: schemas.SubmissionCreate, baekjoon_problem_id: int):
    db_submission = models.Submission(
        user_id=user_id,
        daily_problem_id=submission.daily_problem_id,
        baekjoon_problem_id=baekjoon_problem_id,
        baekjoon_submission_id=submission.baekjoon_submission_id,
        language=submission.language,
        code=submission.code,
        status=submission.status,
        result_message=submission.result_message,
        runtime_ms=submission.runtime_ms,
        memory_usage_kb=submission.memory_usage_kb,
        submitted_at=submission.submitted_at
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission

def update_submission_status(db: Session, submission_id: uuid.UUID, status: str, result_message: Optional[str] = None, runtime_ms: Optional[int] = None, memory_usage_kb: Optional[int] = None, code: Optional[str] = None):
    db_submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if db_submission:
        db_submission.status = status
        db_submission.result_message = result_message
        db_submission.runtime_ms = runtime_ms
        db_submission.memory_usage_kb = memory_usage_kb
        if code:
            db_submission.code = code
        db.commit()
        db.refresh(db_submission)
    return db_submission
```
Expected: `backend/app/crud/submissions.py` 파일이 생성됩니다.

**Step 4: `backend/app/services/baekjoon_crawler.py` 파일 생성 (백준 제출 결과 크롤러)**

이 파일은 백준 웹사이트에서 사용자 제출 결과를 크롤링하는 기능을 담당합니다.

```python
# backend/app/services/baekjoon_crawler.py
import requests
from bs4 import BeautifulSoup
import time
from typing import Dict, Any, Optional

BAEKJOON_SUBMISSION_STATUS_URL = "https://www.acmicpc.net/status"
BAEKJOON_SUBMISSION_DETAIL_URL = "https://www.acmicpc.net/source/download/" # submission_id

def get_submission_result_from_baekjoon(baekjoon_submission_id: int, baekjoon_username: str) -> Optional[Dict[str, Any]]:
    """
    백준 제출 ID와 사용자 이름으로 제출 결과를 크롤링합니다.
    """
    params = {
        "user_id": baekjoon_username,
        "result_id": baekjoon_submission_id
    }
    
    # 제출 결과 페이지 요청
    try:
        response = requests.get(BAEKJOON_SUBMISSION_STATUS_URL, params=params, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching submission status for ID {baekjoon_submission_id} and user {baekjoon_username}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    
    # 결과 파싱 (백준 사이트 구조 변경에 따라 수정 필요)
    # 테이블에서 해당 제출 ID의 결과 행 찾기
    result_row = soup.select_one(f"tr#solution-{baekjoon_submission_id}")
    
    if not result_row:
        print(f"Submission ID {baekjoon_submission_id} not found in status page for user {baekjoon_username}.")
        return None

    columns = result_row.find_all("td")
    
    if len(columns) < 9: # 예상 컬럼 수보다 적으면 파싱 불가
        print(f"Not enough columns in submission row for ID {baekjoon_submission_id}.")
        return None
    
    # 컬럼 인덱스를 기반으로 데이터 추출 (순서가 고정적이라는 가정 하에)
    # 보통 컬럼 순서: 제출번호, 아이디, 문제, 결과, 메모리, 시간, 언어, 코드 길이, 제출시간
    status_text = columns[3].get_text(strip=True)
    memory_usage_kb = int(columns[4].get_text(strip=True).replace('KB', '')) if 'KB' in columns[4].get_text(strip=True) else None
    runtime_ms = int(columns[5].get_text(strip=True).replace('ms', '')) if 'ms' in columns[5].get_text(strip=True) else None
    language = columns[6].get_text(strip=True)
    # 제출 시간은 복잡하므로 일단 현재 시각으로 대체
    submitted_at = datetime.utcnow()

    # 결과 매핑 (백준 결과 텍스트를 내부 상태로 매핑)
    status_map = {
        "맞았습니다!!": "Accepted",
        "런타임 에러": "Runtime Error",
        "컴파일 에러": "Compile Error",
        "시간 초과": "Time Limit Exceeded",
        "메모리 초과": "Memory Limit Exceeded",
        "출력 형식 틀렸습니다": "Wrong Answer", # 백준은 "틀렸습니다"로 표시될 수도 있음
        "틀렸습니다": "Wrong Answer",
        "채점 중": "Judging",
        # ... 추가적인 상태 매핑
    }
    mapped_status = status_map.get(status_text, "Unknown")
    
    result_message = status_text # 일단 백준 원본 메시지 그대로 저장

    return {
        "language": language,
        "status": mapped_status,
        "result_message": result_message,
        "runtime_ms": runtime_ms,
        "memory_usage_kb": memory_usage_kb,
        "submitted_at": submitted_at
    }

def get_submission_code_from_baekjoon(baekjoon_submission_id: int) -> Optional[str]:
    """
    백준 제출 ID로 코드 내용을 크롤링합니다.
    """
    url = f"{BAEKJOON_SUBMISSION_DETAIL_URL}{baekjoon_submission_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        # 백준은 코드 다운로드 시 텍스트 파일로 직접 응답하는 경우가 많음
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching submission code for ID {baekjoon_submission_id}: {e}")
        return None

```
Expected: `backend/app/services/baekjoon_crawler.py` 파일이 생성됩니다.

**Step 5: `backend/app/routers/submissions.py` 파일 생성 (제출 API 엔드포인트)**

`backend/app/routers` 디렉토리는 이미 존재합니다.

```python
# backend/app/routers/submissions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from .. import schemas
from ..crud import daily_problems, submissions # crud.submissions 추가
from ..services.baekjoon_crawler import get_submission_result_from_baekjoon, get_submission_code_from_baekjoon
from ..database import get_db
from ..auth import get_current_user
from ..models import User
import asyncio # 비동기 작업을 위해 필요

router = APIRouter(
    prefix="/submissions",
    tags=["submissions"],
    responses={404: {"description": "Not found"}},
)

@router.post("/register", response_model=schemas.Submission)
async def register_submission_result(
    submission_request: schemas.SubmissionRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. 일일 문제 확인
    daily_problem = daily_problems.get_daily_problem_by_id(db, submission_request.daily_problem_id)
    if not daily_problem:
        raise HTTPException(status_code=404, detail="Daily problem not found.")

    # 2. 백준에서 제출 결과 크롤링
    crawled_result = get_submission_result_from_baekjoon(
        submission_request.baekjoon_submission_id,
        current_user.baekjoon_id
    )
    if not crawled_result:
        raise HTTPException(status_code=500, detail="Failed to crawl submission result from Baekjoon.")

    # 3. 크롤링된 코드 내용 가져오기 (비동기 처리 필요)
    # 현재는 Blocking Call이므로 주의. 실제 서비스에서는 백그라운드 태스크로 분리하여 처리.
    crawled_code = get_submission_code_from_baekjoon(submission_request.baekjoon_submission_id)
    
    # 4. Submission 객체 생성 및 저장
    submission_create = schemas.SubmissionCreate(
        daily_problem_id=submission_request.daily_problem_id,
        baekjoon_submission_id=submission_request.baekjoon_submission_id,
        baekjoon_problem_id=daily_problem.baekjoon_problem_id, # 일일 문제에서 가져옴
        language=crawled_result.get("language", "Unknown"),
        code=crawled_code,
        status=crawled_result.get("status", "Unknown"),
        result_message=crawled_result.get("result_message"),
        runtime_ms=crawled_result.get("runtime_ms"),
        memory_usage_kb=crawled_result.get("memory_usage_kb"),
        submitted_at=crawled_result.get("submitted_at", datetime.utcnow())
    )
    db_submission = submissions.create_submission(
        db=db,
        user_id=current_user.id,
        submission=submission_create,
        baekjoon_problem_id=daily_problem.baekjoon_problem_id
    )
    return db_submission

@router.get("/{submission_id}", response_model=schemas.Submission)
def get_single_submission(
    submission_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_submission = submissions.get_submission(db, submission_id)
    if not db_submission or db_submission.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Submission not found or not authorized.")
    return db_submission

@router.get("/problem/{daily_problem_id}", response_model=List[schemas.Submission])
def get_user_submissions_for_problem(
    daily_problem_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_submissions = submissions.get_user_submissions_for_problem(db, current_user.id, daily_problem_id)
    return db_submissions
```
Expected: `backend/app/routers/submissions.py` 파일이 생성됩니다.

**Step 6: `backend/app/main.py` 파일 업데이트 (submissions 라우터 포함)**

`backend/app/main.py` 파일을 열고 `submissions` 라우터를 앱에 포함시킵니다.

```python
# backend/app/main.py (기존 내용에 추가)
from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv

from .routers import users, daily_problems, submissions # submissions 추가
from .tasks.scheduler import start_scheduler

load_dotenv()

app = FastAPI(title="Legend Coder Platform API")

app.include_router(users.router)
app.include_router(daily_problems.router)
app.include_router(submissions.router) # submissions 라우터 포함

@app.on_event("startup")
async def startup_event():
    print("Starting up application...")
    start_scheduler()

@app.get("/")
async def root():
    return {"message": "Welcome to Legend Coder Platform API"}

```
Expected: `backend/app/main.py` 파일이 업데이트됩니다.

**Step 7: `backend/app/crud/__init__.py` 파일 업데이트 (submissions crud 모듈 임포트)**

`backend/app/crud/__init__.py` 파일을 열고 `submissions` 모듈을 임포트합니다.

```python
# backend/app/crud/__init__.py (기존 내용에 추가)
from . import daily_problems
from . import submissions # submissions 모듈 임포트
```
Expected: `backend/app/crud/__init__.py` 파일이 업데이트됩니다.

**Step 8: API 테스트**

(FastAPI 서버 실행: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`)
웹 브라우저에서 `http://localhost:8000/docs`에 접속하여 Swagger UI를 통해 다음을 테스트합니다:
1.  **사용자 생성 및 로그인하여 토큰 획득.**
2.  **`GET /daily-problems/today`를 통해 오늘의 문제 `daily_problem_id`를 획득합니다.**
3.  **백준 웹사이트에서 해당 `baekjoon_problem_id` 문제를 풀고, 제출한 후 `baekjoon_submission_id`를 복사합니다.**
4.  **`POST /submissions/register`를 통해 `daily_problem_id`와 `baekjoon_submission_id`를 제출합니다.**
    *   Response body를 확인하여 제출 결과가 올바르게 등록되었는지 확인합니다.
5.  **`GET /submissions/{submission_id}` 또는 `GET /submissions/problem/{daily_problem_id}`를 통해 등록된 제출 결과를 조회합니다.**

**Step 9: Commit**

```bash
git add backend/requirements.txt backend/app/schemas.py backend/app/crud/submissions.py backend/app/services/baekjoon_crawler.py backend/app/routers/submissions.py backend/app/main.py backend/app/crud/__init__.py
git commit -m "feat: Implement submission result registration and judging via Baekjoon crawling"
```

### Task 6: 커뮤니티 및 토론 기능 (Community & Discussion)

**Goal:** 각 문제에 대해 사용자들이 풀이 아이디어를 공유하고 질문할 수 있는 게시글(Post) 및 댓글(Comment) CRUD API를 구현합니다.

**Files:**
- Create: `backend/app/crud/posts.py`
- Create: `backend/app/crud/comments.py`
- Modify: `backend/app/schemas.py` (Pydantic schemas for posts and comments)
- Create: `backend/app/routers/posts.py`
- Create: `backend/app/routers/comments.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/crud/__init__.py`

**Step 1: `backend/app/schemas.py` 업데이트 (Post, Comment 스키마 추가)**

`backend/app/schemas.py` 파일의 마지막에 다음 내용을 추가합니다.

```python
class CommentBase(BaseModel):
    content: str
    parent_comment_id: Optional[uuid.UUID] = None

class CommentCreate(CommentBase):
    post_id: uuid.UUID

class Comment(CommentBase):
    id: uuid.UUID
    user_id: uuid.UUID
    post_id: uuid.UUID
    like_count: int
    created_at: datetime
    updated_at: datetime
    nickname: Optional[str] = None

    class Config:
        orm_mode = True

class PostBase(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = None

class PostCreate(PostBase):
    daily_problem_id: uuid.UUID

class Post(PostBase):
    id: uuid.UUID
    user_id: uuid.UUID
    daily_problem_id: uuid.UUID
    view_count: int
    like_count: int
    created_at: datetime
    updated_at: datetime
    nickname: Optional[str] = None
    comments: List[Comment] = []

    class Config:
        orm_mode = True
```

**Step 2: `backend/app/crud/posts.py` 및 `comments.py` 생성**

사용자 정의 CRUD 로직을 작성합니다. (게시글 목록 조회 시 닉네임 포함 join 처리 등)

**Step 3: `backend/app/routers/posts.py` 및 `comments.py` 생성**

FastAPI 라우터를 생성하여 API 엔드포인트를 정의합니다.

**Step 4: `backend/app/main.py`에 라우터 등록**

**Step 5: API 테스트 및 커밋**

```bash
git add ...
git commit -m "feat: Implement community features (posts and comments)"
```

### Task 7: 랭킹 및 대시보드 API (Ranking & Dashboard)

**Goal:** 사용자들의 문제 해결 통계를 기반으로 한 랭킹 시스템과 개인별 학습 진행 상황을 보여주는 대시보드 API를 구현합니다.

**Files:**
- Create: `backend/app/crud/stats.py`
- Modify: `backend/app/schemas.py` (Pydantic schemas for stats and rankings)
- Create: `backend/app/routers/stats.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/crud/__init__.py`

**Step 1: `backend/app/schemas.py` 업데이트 (Ranking, Stats 스키마 추가)**

```python
class UserRanking(BaseModel):
    user_id: uuid.UUID
    nickname: str
    solved_count: int
    consecutive_days: int

class UserDashboard(BaseModel):
    total_solved: int
    streak_days: int
    solve_history: List[date] # 해결한 날짜 목록 (달력용)
```

**Step 2: `backend/app/crud/stats.py` 생성**

사용자별 해결 문제 수 계산, 연속 해결 일수(Streak) 계산 로직을 작성합니다.

**Step 3: `backend/app/routers/stats.py` 생성**

`/stats/ranking` 및 `/stats/me` 엔드포인트를 구현합니다.

**Step 4: `backend/app/main.py`에 라우터 등록**

**Step 5: API 테스트 및 커밋**

```bash
git add ...
git commit -m "feat: Implement ranking and dashboard statistics API"
```


```
