from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.play_history import PlayHistory
from app.models.song import Song
from app.models.user import User
from app.schemas.history import HistoryCreate, HistoryItemResponse
from app.schemas.history_recent import RecentHistoryItemResponse
from app.schemas.song import SongResponse

router = APIRouter(prefix="/history", tags=["History"])


@router.post("", response_model=HistoryItemResponse, status_code=status.HTTP_201_CREATED)
def add_to_history(
    payload: HistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    song = db.query(Song).filter(Song.id == payload.song_id).first()
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Canción no encontrada",
        )

    history_item = PlayHistory(
        user_id=current_user.id,
        song_id=payload.song_id,
        seconds_listened=payload.seconds_listened,
    )

    db.add(history_item)

    # CONTAR REPRODUCCIÓN SOLO SI ESCUCHÓ SUFICIENTE
    if payload.seconds_listened >= 30:
        song.plays_count += 1

    db.commit()
    db.refresh(history_item)

    history_item.song = song

    return history_item


@router.get("", response_model=list[HistoryItemResponse])
def get_history(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    history = (
        db.query(PlayHistory)
        .options(joinedload(PlayHistory.song))
        .filter(PlayHistory.user_id == current_user.id)
        .order_by(PlayHistory.played_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return history


@router.get("/recent", response_model=list[RecentHistoryItemResponse])
def get_recent_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    grouped_rows = (
        db.query(
            PlayHistory.song_id,
            func.max(PlayHistory.played_at).label("last_played_at"),
            func.count(PlayHistory.id).label("total_plays"),
        )
        .filter(PlayHistory.user_id == current_user.id)
        .group_by(PlayHistory.song_id)
        .order_by(func.max(PlayHistory.played_at).desc())
        .limit(limit)
        .all()
    )

    if not grouped_rows:
        return []

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

    results = []
    for row in grouped_rows:
        song = songs_by_id.get(row.song_id)
        if not song:
            continue

        results.append(
            RecentHistoryItemResponse(
                song=SongResponse.model_validate(song),
                last_played_at=row.last_played_at,
                total_plays=row.total_plays,
                last_seconds_listened=latest_seconds_by_song_id.get(row.song_id),
            )
        )

    return results