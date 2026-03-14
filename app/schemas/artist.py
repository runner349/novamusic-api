from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ArtistCreate(BaseModel):
    user_id: Optional[int] = None
    name: str
    bio: Optional[str] = None
    photo_url: Optional[str] = None


class ArtistUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None


class ArtistResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    name: str
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True