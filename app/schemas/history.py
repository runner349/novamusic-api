from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.song import SongResponse


class HistoryCreate(BaseModel):
    song_id: int
    seconds_listened: int = Field(ge=0)


class HistoryItemResponse(BaseModel):
    id: int
    user_id: int
    song_id: int
    played_at: datetime
    seconds_listened: int
    song: SongResponse

    model_config = ConfigDict(from_attributes=True)