from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.play_history import PlayHistory
from app.models.playlist import Playlist
from app.models.song import Song
from app.models.user import User
from app.schemas.album import AlbumResponse
from app.schemas.artist import ArtistResponse
from app.schemas.history_recent import RecentHistoryItemResponse
from app.schemas.home import HomeResponse
from app.schemas.playlist import PlaylistResponse
from app.schemas.song import SongListItemResponse

router = APIRouter(prefix="/home", tags=["Home"])


def build_song_list_item(db: Session, song: Song) -> SongListItemResponse:
    album = db.query(Album).filter(Album.id == song.album_id).first()
    artist = db.query(Artist).filter(Artist.id == album.artist_id).first()

    cover_url = song.cover_url or album.cover_url or settings.DEFAULT_SONG_COVER_URL

    return SongListItemResponse(
        id=song.id,
        album_id=album.id,
        album_title=album.title,
        artist_id=artist.id,
        artist_name=artist.name,
        title=song.title,
        duration_seconds=song.duration_seconds,
        track_number=song.track_number,
        cover_url=cover_url,
        plays_count=song.plays_count,
    )


def apply_album_cover_fallback(album: Album) -> Album:
    if not album.cover_url:
        album.cover_url = settings.DEFAULT_ALBUM_COVER_URL
    return album


def apply_artist_photo_fallback(artist: Artist) -> Artist:
    if not artist.photo_url:
        artist.photo_url = settings.DEFAULT_ARTIST_PHOTO_URL
    return artist


def apply_playlist_cover_fallback(playlist: Playlist) -> Playlist:
    if not playlist.cover_url:
        playlist.cover_url = settings.DEFAULT_PLAYLIST_COVER_URL
    return playlist


@router.get("", response_model=HomeResponse)
def get_home(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    songs_limit: int = Query(default=10, ge=1, le=20),
    albums_limit: int = Query(default=10, ge=1, le=20),
    artists_limit: int = Query(default=10, ge=1, le=20),
    playlists_limit: int = Query(default=10, ge=1, le=20),
    history_limit: int = Query(default=10, ge=1, le=20),
):
    popular_songs_query = (
        db.query(Song)
        .filter(Song.audio_path.is_not(None), Song.audio_path != "")
        .order_by(Song.plays_count.desc(), Song.created_at.desc())
        .limit(songs_limit)
        .all()
    )
    popular_songs = [build_song_list_item(db, song) for song in popular_songs_query]

    new_releases_query = (
        db.query(Album)
        .order_by(Album.release_date.desc(), Album.created_at.desc())
        .limit(albums_limit)
        .all()
    )
    new_releases = [
        AlbumResponse.model_validate(apply_album_cover_fallback(album))
        for album in new_releases_query
    ]

    featured_artists_query = (
        db.query(Artist)
        .order_by(Artist.created_at.desc())
        .limit(artists_limit)
        .all()
    )
    featured_artists = [
        ArtistResponse.model_validate(apply_artist_photo_fallback(artist))
        for artist in featured_artists_query
    ]

    public_playlists_query = (
        db.query(Playlist)
        .filter(Playlist.is_public == True)
        .order_by(Playlist.created_at.desc())
        .limit(playlists_limit)
        .all()
    )
    public_playlists = [
        PlaylistResponse.model_validate(apply_playlist_cover_fallback(playlist))
        for playlist in public_playlists_query
    ]

    grouped_rows = (
        db.query(
            PlayHistory.song_id,
            func.max(PlayHistory.played_at).label("last_played_at"),
            func.count(PlayHistory.id).label("total_plays"),
        )
        .filter(PlayHistory.user_id == current_user.id)
        .group_by(PlayHistory.song_id)
        .order_by(func.max(PlayHistory.played_at).desc())
        .limit(history_limit)
        .all()
    )

    recent_history = []
    if grouped_rows:
        song_ids = [row.song_id for row in grouped_rows]
        songs = db.query(Song).filter(Song.id.in_(song_ids)).all()
        songs_by_id = {song.id: song for song in songs}

        latest_history_rows = (
            db.query(PlayHistory)
            .filter(
                PlayHistory.user_id == current_user.id,
                PlayHistory.song_id.in_(song_ids),
            )
            .order_by(PlayHistory.song_id.asc(), PlayHistory.played_at.desc())
            .all()
        )

        latest_seconds_by_song_id = {}
        for row in latest_history_rows:
            if row.song_id not in latest_seconds_by_song_id:
                latest_seconds_by_song_id[row.song_id] = row.seconds_listened

        for row in grouped_rows:
            song = songs_by_id.get(row.song_id)
            if not song:
                continue

            recent_history.append(
                RecentHistoryItemResponse(
                    song=build_song_list_item(db, song),
                    last_played_at=row.last_played_at,
                    total_plays=row.total_plays,
                    last_seconds_listened=latest_seconds_by_song_id.get(row.song_id),
                )
            )

    return HomeResponse(
        popular_songs=popular_songs,
        new_releases=new_releases,
        featured_artists=featured_artists,
        public_playlists=public_playlists,
        recent_history=recent_history,
    )