from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class FavoriteSong(Base):
    __tablename__ = "favorite_songs"

    __table_args__ = (
        UniqueConstraint("user_id", "song_id", name="uq_favorite_songs_user_song"),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="favorite_songs")
    song = relationship("Song", back_populates="favorite_songs")