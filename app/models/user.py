from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)

    password_hash = Column(String, nullable=True)

    full_name = Column(String(255), nullable=True)
    photo_url = Column(String, nullable=True)

    role = Column(String(20), nullable=False, default="user", index=True)
    auth_provider = Column(String(20), nullable=False, default="local", index=True)
    provider_user_id = Column(String(255), nullable=True, index=True)

    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    playlists = relationship("Playlist", back_populates="user", cascade="all, delete-orphan")
    favorite_songs = relationship("FavoriteSong", back_populates="user", cascade="all, delete-orphan")
    play_history = relationship("PlayHistory", back_populates="user", cascade="all, delete-orphan")
    search_history = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")