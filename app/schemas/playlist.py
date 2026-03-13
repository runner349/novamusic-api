from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.song import SongResponse


class PlaylistCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    cover_url: Optional[str] = None
    is_public: bool = True


class PlaylistUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    cover_url: Optional[str] = None
    is_public: Optional[bool] = None


class PlaylistReorderItem(BaseModel):
    song_id: int
    position: int = Field(gt=0)


class PlaylistReorderRequest(BaseModel):
    items: List[PlaylistReorderItem]


class PlaylistResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    is_public: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaylistDetailResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    is_public: bool
    created_at: datetime
    updated_at: datetime
    songs: List[SongResponse]