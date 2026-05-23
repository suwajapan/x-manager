from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
import enum


class Genre(str, enum.Enum):
    food = "food"
    beauty = "beauty"
    fashion = "fashion"


class PostStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    published = "published"
    failed = "failed"


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    profile_image_url = Column(String)
    genre = Column(Enum(Genre), nullable=False)
    access_token = Column(Text)
    access_token_secret = Column(Text)
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    tweet_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts = relationship("ScheduledPost", back_populates="account")
    analytics = relationship("Analytics", back_populates="account")


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Enum(PostStatus), default=PostStatus.draft)
    scheduled_at = Column(DateTime)
    published_at = Column(DateTime)
    tweet_id = Column(String)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="posts")


class TrendPost(Base):
    __tablename__ = "trend_posts"

    id = Column(Integer, primary_key=True)
    tweet_id = Column(String, unique=True)
    genre = Column(Enum(Genre), nullable=False)
    text = Column(Text)
    author_username = Column(String)
    author_name = Column(String)
    author_image = Column(String)
    likes = Column(Integer, default=0)
    retweets = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    posted_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)


class Influencer(Base):
    __tablename__ = "influencers"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    profile_image_url = Column(String)
    genre = Column(Enum(Genre))
    followers = Column(Integer, default=0)
    user_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    posts = relationship("InfluencerPost", back_populates="influencer", cascade="all, delete-orphan")


class InfluencerPost(Base):
    __tablename__ = "influencer_posts"

    id = Column(Integer, primary_key=True)
    influencer_id = Column(Integer, ForeignKey("influencers.id"), nullable=False)
    tweet_id = Column(String, unique=True)
    text = Column(Text)
    likes = Column(Integer, default=0)
    retweets = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    posted_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    influencer = relationship("Influencer", back_populates="posts")


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(Integer, primary_key=True)
    service = Column(String, nullable=False)    # "anthropic" | "x_read" | "x_write"
    operation = Column(String, nullable=False)  # "generate_post" | "generate_caption" | "fetch_trends" etc.
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Integer, default=0)       # マイクロドル (1 = $0.000001) で整数保存
    called_at = Column(DateTime, default=datetime.utcnow)


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    followers = Column(Integer)
    following = Column(Integer)
    tweet_count = Column(Integer)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="analytics")
