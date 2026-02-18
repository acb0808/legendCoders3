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

