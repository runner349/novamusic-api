from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class PlayHistory(Base):
    __tablename__ = "play_history"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)

    played_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    seconds_listened = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="play_history")
    song = relationship("Song", back_populates="play_history")