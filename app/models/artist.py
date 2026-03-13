from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False, unique=True, index=True)
    bio = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    albums = relationship("Album", back_populates="artist", cascade="all, delete-orphan")