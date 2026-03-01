# backend/schemas.py
from __future__ import annotations
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date
import uuid

class UserBase(BaseModel):
    email: EmailStr
    nickname: str
    baekjoon_id: Optional[str] = None # Changed to Optional
    is_pro: bool = False
    is_admin: bool = False # 어드민 여부 추가
    pro_expires_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    streak_freeze_count: int = 0
    equipped_title_id: Optional[uuid.UUID] = None

class TitleBase(BaseModel):
    name: str
    description: str
    color_code: str = "blue"
    is_pro_only: bool = False
    has_glow: bool = False
    animation_type: Optional[str] = None
    icon: Optional[str] = None

class Title(TitleBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

class UserCreate(UserBase):
    password: str
    invitation_code: str

class InvitationCodeBase(BaseModel):
    code: str

class InvitationCodeResponse(InvitationCodeBase):
    id: uuid.UUID
    is_used: bool
    used_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime
    used_at: Optional[datetime] = None
    nickname: Optional[str] = None # 사용한 유저 닉네임 편의상 추가

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    baekjoon_id: Optional[str] = None
    password: Optional[str] = None
    is_pro: Optional[bool] = None
    is_admin: Optional[bool] = None # 어드민 수정 추가
    streak_freeze_count: Optional[int] = None

class User(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    equipped_title: Optional[Title] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str # 리프레시 토큰 추가
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
        from_attributes = True

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
        from_attributes = True

class SubmissionRegisterRequest(BaseModel):
    daily_problem_id: uuid.UUID
    baekjoon_submission_id: Optional[int] = None # 사용자가 직접 입력하거나 생략 가능

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
        from_attributes = True

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
        from_attributes = True

class UserRanking(BaseModel):
    user_id: uuid.UUID
    nickname: str
    solved_count: int
    consecutive_days: int
    equipped_title: Optional[Title] = None

    class Config:
        from_attributes = True

class UserDashboard(BaseModel):
    total_solved: int
    streak_days: int
    solve_history: List[date]

class Activity(BaseModel):
    date: date
    type: str  # SOLVED, FROZEN, NONE
    solved_count: int

class WeeklyStatus(BaseModel):
    date: date
    day_name: str
    is_solved: bool
    has_problem: bool

class UserWeeklyLeaderboard(BaseModel):
    user_id: uuid.UUID
    nickname: str
    equipped_title: Optional[Title] = None
    status: List[WeeklyStatus]

# Arena Schemas
class ArenaCreate(BaseModel):
    difficulty: str  # BRONZE, SILVER, GOLD, PLATINUM, DIAMOND, RANDOM
    mode: str = "OPEN" # OPEN, PRIVATE

class ArenaResponse(BaseModel):
    id: uuid.UUID
    host_id: uuid.UUID
    guest_id: Optional[uuid.UUID] = None
    baekjoon_problem_id: Optional[int] = None
    status: str
    difficulty: str
    host_ready: bool = False
    guest_ready: bool = False
    host_surrender: bool = False
    guest_surrender: bool = False
    host_draw_agreed: bool = False
    guest_draw_agreed: bool = False
    host_skip_agreed: bool = False
    guest_skip_agreed: bool = False
    draw_agreed: bool = False
    skip_agreed: bool = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    winner_id: Optional[uuid.UUID] = None
    created_at: datetime
    
    host: Optional['User'] = None
    guest: Optional['User'] = None
    winner: Optional['User'] = None

    class Config:
        from_attributes = True
