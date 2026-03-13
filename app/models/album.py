from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class Album(Base):
    __tablename__ = "albums"

    __table_args__ = (
        UniqueConstraint("artist_id", "title", name="uq_albums_artist_title"),
    )

    id = Column(Integer, primary_key=True, index=True)

    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    cover_url = Column(String, nullable=True)
    release_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    artist = relationship("Artist", back_populates="albums")
    songs = relationship("Song", back_populates="album", cascade="all, delete-orphan")