from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.playlist import Playlist
from app.models.playlist_song import PlaylistSong
from app.models.song import Song
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.playlist import (
    PlaylistCreate,
    PlaylistUpdate,
    PlaylistResponse,
    PlaylistDetailResponse,
    PlaylistReorderRequest,
)
from app.schemas.song import SongResponse

router = APIRouter(prefix="/playlists", tags=["Playlists"])


def get_playlist_or_404(db: Session, playlist_id: int) -> Playlist:
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist no encontrada",
        )
    return playlist


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
def create_playlist(
    payload: PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    playlist = Playlist(
        user_id=current_user.id,
        title=payload.title.strip(),
        description=payload.description,
        cover_url=payload.cover_url,
        is_public=payload.is_public,
    )

    db.add(playlist)
    db.commit()
    db.refresh(playlist)

    return playlist


@router.get("", response_model=list[PlaylistResponse])
def get_my_playlists(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    playlists = (
        db.query(Playlist)
        .filter(Playlist.user_id == current_user.id)
        .order_by(Playlist.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return playlists


@router.get("/{playlist_id}", response_model=PlaylistDetailResponse)
def get_playlist_detail(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    playlist = get_playlist_or_404(db, playlist_id)

    if playlist.user_id != current_user.id and not playlist.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta playlist",
        )

    playlist_items = (
        db.query(PlaylistSong)
        .options(joinedload(PlaylistSong.song))
        .filter(PlaylistSong.playlist_id == playlist_id)
        .order_by(PlaylistSong.position.asc())
        .all()
    )

    songs = [SongResponse.model_validate(item.song) for item in playlist_items]

    return PlaylistDetailResponse(
        id=playlist.id,
        user_id=playlist.user_id,
        title=playlist.title,
        description=playlist.description,
        cover_url=playlist.cover_url,
        is_public=playlist.is_public,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
        songs=songs,
    )


@router.patch("/{playlist_id}", response_model=PlaylistResponse)
def update_playlist(
    playlist_id: int,
    payload: PlaylistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    playlist = get_playlist_or_404(db, playlist_id)

    if playlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes editar esta playlist",
        )

    if payload.title is not None:
        playlist.title = payload.title.strip()

    if payload.description is not None:
        playlist.description = payload.description

    if payload.cover_url is not None:
        playlist.cover_url = payload.cover_url

    if payload.is_public is not None:
        playlist.is_public = payload.is_public

    db.commit()
    db.refresh(playlist)

    return playlist


@router.delete("/{playlist_id}", response_model=MessageResponse)
def delete_playlist(
    playlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    playlist = get_playlist_or_404(db, playlist_id)

    if playlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes eliminar esta playlist",
        )

    db.delete(playlist)
    db.commit()

    return MessageResponse(message="Playlist eliminada correctamente")


@router.post("/{playlist_id}/songs/{song_id}", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def add_song_to_playlist(
    playlist_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    playlist = get_playlist_or_404(db, playlist_id)

    if playlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes modificar esta playlist",
        )

    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canción no encontrada",
        )

    existing = (
        db.query(PlaylistSong)
        .filter(
            PlaylistSong.playlist_id == playlist_id,
            PlaylistSong.song_id == song_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La canción ya está en la playlist",
        )

    last_item = (
        db.query(PlaylistSong)
        .filter(PlaylistSong.playlist_id == playlist_id)
        .order_by(PlaylistSong.position.desc())
        .first()
    )

    next_position = 1 if not last_item else last_item.position + 1

    playlist_song = PlaylistSong(
        playlist_id=playlist_id,
        song_id=song_id,
        position=next_position,
    )

    db.add(playlist_song)
    db.commit()

    return MessageResponse(message="Canción agregada a la playlist")


@router.delete("/{playlist_id}/songs/{song_id}", response_model=MessageResponse)
def remove_song_from_playlist(
    playlist_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    playlist = get_playlist_or_404(db, playlist_id)

    if playlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes modificar esta playlist",
        )

    playlist_song = (
        db.query(PlaylistSong)
        .filter(
            PlaylistSong.playlist_id == playlist_id,
            PlaylistSong.song_id == song_id,
        )
        .first()
    )

    if not playlist_song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La canción no está en la playlist",
        )

    db.delete(playlist_song)
    db.flush()

    remaining_items = (
        db.query(PlaylistSong)
        .filter(PlaylistSong.playlist_id == playlist_id)
        .order_by(PlaylistSong.position.asc())
        .all()
    )

    for index, item in enumerate(remaining_items, start=1):
        item.position = index

    db.commit()

    return MessageResponse(message="Canción eliminada de la playlist")


@router.patch("/{playlist_id}/reorder", response_model=MessageResponse)
def reorder_playlist(
    playlist_id: int,
    payload: PlaylistReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    playlist = get_playlist_or_404(db, playlist_id)

    if playlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes modificar esta playlist",
        )

    existing_items = (
        db.query(PlaylistSong)
        .filter(PlaylistSong.playlist_id == playlist_id)
        .order_by(PlaylistSong.position.asc())
        .all()
    )

    existing_by_song_id = {item.song_id: item for item in existing_items}

    if len(payload.items) != len(existing_items):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar todas las canciones de la playlist para reordenar",
        )

    received_song_ids = {item.song_id for item in payload.items}
    existing_song_ids = set(existing_by_song_id.keys())

    if received_song_ids != existing_song_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La lista de canciones no coincide con la playlist actual",
        )

    positions = [item.position for item in payload.items]
    if len(positions) != len(set(positions)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las posiciones no pueden repetirse",
        )

    expected_positions = set(range(1, len(existing_items) + 1))
    if set(positions) != expected_positions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las posiciones deben ser consecutivas empezando en 1",
        )

    # Paso 1: mover temporalmente a posiciones altas para evitar choque
    temp_base = 1000
    for index, item in enumerate(existing_items, start=1):
        item.position = temp_base + index

    db.flush()

    # Paso 2: asignar posiciones finales
    for item in payload.items:
        existing_by_song_id[item.song_id].position = item.position

    db.commit()

    return MessageResponse(message="Playlist reordenada correctamente")