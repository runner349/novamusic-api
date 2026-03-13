from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.favorite_song import FavoriteSong
from app.models.song import Song
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.song import SongResponse

router = APIRouter(prefix="/favorites", tags=["Favorites"])


@router.post("/songs/{song_id}", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def add_favorite_song(
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

    existing_favorite = (
        db.query(FavoriteSong)
        .filter(
            FavoriteSong.user_id == current_user.id,
            FavoriteSong.song_id == song_id,
        )
        .first()
    )

    if existing_favorite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La canción ya está en favoritos",
        )

    favorite = FavoriteSong(
        user_id=current_user.id,
        song_id=song_id,
    )

    db.add(favorite)
    db.commit()

    return MessageResponse(message="Canción agregada a favoritos")


@router.get("/songs", response_model=list[SongResponse])
def get_favorite_songs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    songs = (
        db.query(Song)
        .join(FavoriteSong, FavoriteSong.song_id == Song.id)
        .filter(FavoriteSong.user_id == current_user.id)
        .order_by(FavoriteSong.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return songs


@router.delete("/songs/{song_id}", response_model=MessageResponse)
def remove_favorite_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    favorite = (
        db.query(FavoriteSong)
        .filter(
            FavoriteSong.user_id == current_user.id,
            FavoriteSong.song_id == song_id,
        )
        .first()
    )

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La canción no está en favoritos",
        )

    db.delete(favorite)
    db.commit()

    return MessageResponse(message="Canción eliminada de favoritos")