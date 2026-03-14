from typing import List

from pydantic import BaseModel

from app.schemas.album import AlbumResponse
from app.schemas.artist import ArtistResponse
from app.schemas.history_recent import RecentHistoryItemResponse
from app.schemas.playlist import PlaylistResponse
from app.schemas.song import SongListItemResponse


class HomeResponse(BaseModel):
    popular_songs: List[SongListItemResponse]
    new_releases: List[AlbumResponse]
    featured_artists: List[ArtistResponse]
    public_playlists: List[PlaylistResponse]
    recent_history: List[RecentHistoryItemResponse]