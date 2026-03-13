from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ArtistCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    bio: Optional[str] = None
    photo_url: Optional[str] = None


class ArtistUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    bio: Optional[str] = None
    photo_url: Optional[str] = None


class ArtistResponse(BaseModel):
    id: int
    name: str
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)