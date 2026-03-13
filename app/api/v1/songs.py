from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.core.config import settings
from app.core.database import get_db
from app.models.album import Album
from app.models.play_history import PlayHistory
from app.models.song import Song
from app.models.user import User
from app.schemas.playback import PlaySongResponse, PlaybackUrlResponse
from app.schemas.song import SongCreate, SongResponse, SongUpdate
from app.services.storage_service import storage_service

router = APIRouter(prefix="/songs", tags=["Songs"])


@router.get("/popular", response_model=list[SongResponse])
def get_popular_songs(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    songs = (
        db.query(Song)
        .order_by(Song.plays_count.desc(), Song.title.asc())
        .limit(limit)
        .all()
    )
    return songs


@router.post("", response_model=SongResponse, status_code=status.HTTP_201_CREATED)
def create_song(
    payload: SongCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "artist")),
):
    album = db.query(Album).filter(Album.id == payload.album_id).first()
    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Álbum no encontrado",
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

    return song


@router.get("", response_model=list[SongResponse])
def get_songs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    album_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(Song)

    if album_id is not None:
        query = query.filter(Song.album_id == album_id)

    songs = (
        query
        .order_by(Song.created_at.desc(), Song.title.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return songs


@router.get("/{song_id}", response_model=SongResponse)
def get_song_by_id(song_id: int, db: Session = Depends(get_db)):
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canción no encontrada",
        )

    return song


@router.patch("/{song_id}", response_model=SongResponse)
def update_song(
    song_id: int,
    payload: SongUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "artist")),
):
    song = db.query(Song).filter(Song.id == song_id).first()

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canción no encontrada",
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

    return PlaySongResponse(
        message="Reproducción registrada correctamente",
        song=SongResponse.model_validate(song),
        played_at=history_item.played_at,
        seconds_listened=history_item.seconds_listened,
    )