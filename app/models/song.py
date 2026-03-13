from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Song(Base):
    __tablename__ = "songs"

    __table_args__ = (
        UniqueConstraint("album_id", "track_number", name="uq_songs_album_track_number"),
    )

    id = Column(Integer, primary_key=True, index=True)

    album_id = Column(Integer, ForeignKey("albums.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False, index=True)
    duration_seconds = Column(Integer, nullable=False)
    track_number = Column(Integer, nullable=False)

    audio_path = Column(String, nullable=False)
    cover_url = Column(String, nullable=True)

    plays_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    album = relationship("Album", back_populates="songs")
    playlist_songs = relationship("PlaylistSong", back_populates="song", cascade="all, delete-orphan")
    favorite_songs = relationship("FavoriteSong", back_populates="song", cascade="all, delete-orphan")
    play_history = relationship("PlayHistory", back_populates="song", cascade="all, delete-orphan")