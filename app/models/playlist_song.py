from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class PlaylistSong(Base):
    __tablename__ = "playlist_songs"

    __table_args__ = (
        UniqueConstraint("playlist_id", "song_id", name="uq_playlist_songs_playlist_song"),
        UniqueConstraint("playlist_id", "position", name="uq_playlist_songs_playlist_position"),
    )

    id = Column(Integer, primary_key=True, index=True)

    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False)

    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    playlist = relationship("Playlist", back_populates="playlist_songs")
    song = relationship("Song", back_populates="playlist_songs")