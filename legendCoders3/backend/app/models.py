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
    is_pro = Column(Boolean, default=False)
    pro_expires_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    streak_freeze_count = Column(Integer, default=0) # 스트릭 보호권 개수 추가
    equipped_title_id = Column(UUID(as_uuid=True), ForeignKey("titles.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    submissions = relationship("Submission", back_populates="user")
    posts = relationship("Post", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    equipped_title = relationship("Title", foreign_keys=[equipped_title_id])
    unlocked_titles = relationship("UserTitle", back_populates="user")

class Title(Base):
    __tablename__ = "titles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=False)
    color_code = Column(String, default="blue") # Tailwind color name or hex
    is_pro_only = Column(Boolean, default=False)
    has_glow = Column(Boolean, default=False)
    animation_type = Column(String, nullable=True) # None, "pulse", "shimmer"
    icon = Column(String, nullable=True) # Lucide icon name or emoji

class UserTitle(Base):
    __tablename__ = "user_titles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    title_id = Column(UUID(as_uuid=True), ForeignKey("titles.id"), primary_key=True)
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="unlocked_titles")
    title = relationship("Title")

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

class Arena(Base):
    __tablename__ = "arenas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    guest_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    baekjoon_problem_id = Column(Integer, nullable=True) # 대결 문제 (시작 시 확정)
    
    status = Column(String, default="WAITING") # WAITING, PLAYING, FINISHED, CANCELLED
    difficulty = Column(String, nullable=False) # BRONZE, SILVER, GOLD, PLATINUM, DIAMOND, RANDOM

    host_ready = Column(Boolean, default=False)
    guest_ready = Column(Boolean, default=False)
    host_surrender = Column(Boolean, default=False)
    guest_surrender = Column(Boolean, default=False)
    
    host_draw_agreed = Column(Boolean, default=False)
    guest_draw_agreed = Column(Boolean, default=False)
    host_skip_agreed = Column(Boolean, default=False)
    guest_skip_agreed = Column(Boolean, default=False)
    
    draw_agreed = Column(Boolean, default=False) # Legacy/Combined flag
    skip_agreed = Column(Boolean, default=False) # Legacy/Combined flag
    
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    winner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    host = relationship("User", foreign_keys=[host_id])
    guest = relationship("User", foreign_keys=[guest_id])
    winner = relationship("User", foreign_keys=[winner_id])

