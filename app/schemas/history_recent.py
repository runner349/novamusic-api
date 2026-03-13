from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.song import SongResponse


class RecentHistoryItemResponse(BaseModel):
    song: SongResponse
    last_played_at: datetime
    total_plays: int
    last_seconds_listened: Optional[int] = None