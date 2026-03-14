from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class SongCreate(BaseModel):
    album_id: int
    title: str = Field(min_length=1, max_length=255)
    duration_seconds: int = Field(gt=0)
    track_number: int = Field(gt=0)
    audio_path: str = Field(min_length=3)
    cover_url: Optional[str] = None


class SongUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    duration_seconds: Optional[int] = Field(default=None, gt=0)
    track_number: Optional[int] = Field(default=None, gt=0)
    audio_path: Optional[str] = Field(default=None, min_length=3)
    cover_url: Optional[str] = None


class SongResponse(BaseModel):
    id: int
    album_id: int
    title: str
    duration_seconds: int
    track_number: int
    audio_path: str
    cover_url: Optional[str] = None
    plays_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SongListItemResponse(BaseModel):
    id: int
    album_id: int
    album_title: str
    artist_id: int
    artist_name: str
    title: str
    duration_seconds: int
    track_number: int
    cover_url: Optional[str] = None
    plays_count: int