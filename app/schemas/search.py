from typing import List, Optional

from pydantic import BaseModel

from app.schemas.song import SongResponse


class ArtistSearch(BaseModel):
    id: int
    name: str
    photo_url: Optional[str] = None


class AlbumSearch(BaseModel):
    id: int
    title: str
    cover_url: Optional[str] = None
    artist_id: int


class SearchResponse(BaseModel):
    songs: List[SongResponse]
    artists: List[ArtistSearch]
    albums: List[AlbumSearch]