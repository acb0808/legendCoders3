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
    baekjoon_submission_id: Optional[int] = None # 사용자가 직접 입력하거나 생략 가능