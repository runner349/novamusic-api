from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.song import SongResponse


class PlaySongResponse(BaseModel):
    message: str
    song: SongResponse
    played_at: datetime
    seconds_listened: Optional[int] = None


class PlaybackUrlResponse(BaseModel):
    song_id: int
    playback_url: str
    expires_in: int