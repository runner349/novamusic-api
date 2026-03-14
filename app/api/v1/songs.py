from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.play_history import PlayHistory
from app.models.song import Song
from app.models.user import User
from app.schemas.playback import PlaySongResponse, PlaybackUrlResponse
from app.schemas.song import SongCreate, SongResponse, SongUpdate
from app.services.storage_service import storage_service

router = APIRouter(prefix="/songs", tags=["Songs"])


def apply_song_cover_fallback(db: Session, song: Song) -> Song:
    if song.cover_url:
        return song

    album = db.query(Album).filter(Album.id == song.album_id).first()

    if album and album.cover_url:
        song.cover_url = album.cover_url
    else:
        song.cover_url = settings.DEFAULT_SONG_COVER_URL

    return song


@router.get("/popular", response_model=list[SongResponse])
def get_popular_songs(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    songs = (
        db.query(Song)
        .filter(Song.audio_path.is_not(None), Song.audio_path != "")
        .order_by(Song.plays_count.desc(), Song.title.asc())
        .limit(limit)
        .all()
    )
    songs_with_cover = [apply_song_cover_fallback(db, song) for song in songs]
    return songs_with_cover


@router.post("", response_model=SongResponse, status_code=status.HTTP_201_CREATED)
def create_song(
    payload: SongCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    album = db.query(Album).filter(Album.id == payload.album_id).first()
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Álbum no encontrado",
        )

    album_artist = db.query(Artist).filter(Artist.id == album.artist_id).first()
    if not album_artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artista del álbum no encontrado",
        )

    if current_user.role == "artist":
        if album_artist.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes crear canciones en álbumes de otro artista",
            )
    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para crear canciones",
        )

    existing_track = (
        db.query(Song)
        .filter(
            Song.album_id == payload.album_id,
            Song.track_number == payload.track_number,
        )
        .first()
    )
    if existing_track:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una canción con ese número de pista en este álbum",
        )

    song = Song(
        album_id=payload.album_id,
        title=payload.title.strip(),
        duration_seconds=payload.duration_seconds,
        track_number=payload.track_number,
        audio_path=payload.audio_path,
        cover_url=payload.cover_url,
        plays_count=0,
    )

    db.add(song)
    db.commit()
    db.refresh(song)

    song = apply_song_cover_fallback(db, song)
    return song


@router.get("", response_model=list[SongResponse])
def get_songs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    album_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(Song).filter(Song.audio_path.is_not(None), Song.audio_path != "")

    if album_id is not None:
        query = query.filter(Song.album_id == album_id)

    songs = (
        query
        .order_by(Song.created_at.desc(), Song.title.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    songs_with_cover = [apply_song_cover_fallback(db, song) for song in songs]
    return songs_with_cover


@router.get("/{song_id}", response_model=SongResponse)
def get_song_by_id(song_id: int, db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canción no encontrada",
        )

    song = apply_song_cover_fallback(db, song)
    return song


@router.patch("/{song_id}", response_model=SongResponse)
def update_song(
    song_id: int,
    payload: SongUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canción no encontrada",
        )

    album = db.query(Album).filter(Album.id == song.album_id).first()
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Álbum no encontrado",
        )

    album_artist = db.query(Artist).filter(Artist.id == album.artist_id).first()
    if not album_artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artista del álbum no encontrado",
        )

    if current_user.role == "artist":
        if album_artist.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes editar canciones de otro artista",
            )
    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para editar canciones",
        )

    new_track_number = song.track_number
    if payload.track_number is not None:
        new_track_number = payload.track_number

    if payload.track_number is not None:
        existing_track = (
            db.query(Song)
            .filter(
                Song.album_id == song.album_id,
                Song.track_number == new_track_number,
                Song.id != song_id,
            )
            .first()
        )
        if existing_track:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una canción con ese número de pista en este álbum",
            )

    if payload.title is not None:
        song.title = payload.title.strip()

    if payload.duration_seconds is not None:
        song.duration_seconds = payload.duration_seconds

    if payload.track_number is not None:
        song.track_number = payload.track_number

    if payload.audio_path is not None:
        song.audio_path = payload.audio_path

    if payload.cover_url is not None:
        song.cover_url = payload.cover_url

    db.commit()
    db.refresh(song)

    song = apply_song_cover_fallback(db, song)
    return song


@router.get("/{song_id}/playback-url", response_model=PlaybackUrlResponse)
def get_song_playback_url(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canción no encontrada",
        )

    if not song.audio_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La canción no tiene archivo de audio configurado",
        )

    try:
        playback_url = storage_service.create_signed_file_url(
            bucket=settings.SUPABASE_AUDIO_BUCKET,
            path=song.audio_path,
            expires_in=settings.SUPABASE_SIGNED_URL_EXPIRE_SECONDS,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar la URL de reproducción",
        )

    return PlaybackUrlResponse(
        song_id=song.id,
        playback_url=playback_url,
        expires_in=settings.SUPABASE_SIGNED_URL_EXPIRE_SECONDS,
    )


@router.post("/{song_id}/play", response_model=PlaySongResponse)
def play_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canción no encontrada",
        )

    song.plays_count = (song.plays_count or 0) + 1

    history_item = PlayHistory(
        user_id=current_user.id,
        song_id=song.id,
        seconds_listened=song.duration_seconds,
    )

    db.add(history_item)
    db.commit()
    db.refresh(song)
    db.refresh(history_item)

    song = apply_song_cover_fallback(db, song)

    return PlaySongResponse(
        message="Reproducción registrada correctamente",
        song=SongResponse.model_validate(song),
        played_at=history_item.played_at,
        seconds_listened=history_item.seconds_listened,
    )