from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class AlbumCreate(BaseModel):
    artist_id: int
    title: str = Field(min_length=1, max_length=255)
    cover_url: Optional[str] = None
    release_date: Optional[date] = None


class AlbumUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    cover_url: Optional[str] = None
    release_date: Optional[date] = None


class AlbumResponse(BaseModel):
    id: int
    artist_id: int
    title: str
    cover_url: Optional[str] = None
    release_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)