from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.song import Song
from app.models.user import User
from app.schemas.album import AlbumCreate, AlbumResponse, AlbumUpdate
from app.schemas.song import SongResponse

router = APIRouter(prefix="/albums", tags=["Albums"])


def apply_album_cover_fallback(album: Album) -> Album:
    if not album.cover_url:
        album.cover_url = settings.DEFAULT_ALBUM_COVER_URL
    return album


@router.post("", response_model=AlbumResponse, status_code=status.HTTP_201_CREATED)
def create_album(
    payload: AlbumCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    artist = db.query(Artist).filter(Artist.id == payload.artist_id).first()
    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artista no encontrado",
        )

    if current_user.role == "artist":
        if artist.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes crear álbumes para otro artista",
            )
    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para crear álbumes",
        )

    existing_album = (
        db.query(Album)
        .filter(
            Album.artist_id == payload.artist_id,
            Album.title == payload.title.strip(),
        )
        .first()
    )
    if existing_album:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un álbum con ese título para este artista",
        )

    album = Album(
        artist_id=payload.artist_id,
        title=payload.title.strip(),
        cover_url=payload.cover_url or settings.DEFAULT_ALBUM_COVER_URL,
        release_date=payload.release_date,
    )

    db.add(album)
    db.commit()
    db.refresh(album)

    album = apply_album_cover_fallback(album)
    return album


@router.get("", response_model=list[AlbumResponse])
def get_albums(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    artist_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    query = db.query(Album)

    if artist_id is not None:
        query = query.filter(Album.artist_id == artist_id)

    albums = (
        query
        .order_by(Album.release_date.desc(), Album.title.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [apply_album_cover_fallback(album) for album in albums]


@router.get("/{album_id}", response_model=AlbumResponse)
def get_album_by_id(album_id: int, db: Session = Depends(get_db)):
    album = db.query(Album).filter(Album.id == album_id).first()

    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Álbum no encontrado",
        )

    album = apply_album_cover_fallback(album)
    return album


@router.patch("/{album_id}", response_model=AlbumResponse)
def update_album(
    album_id: int,
    payload: AlbumUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    album = db.query(Album).filter(Album.id == album_id).first()

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
                detail="No puedes editar álbumes de otro artista",
            )
    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para editar álbumes",
        )

    if payload.title is not None:
        normalized_title = payload.title.strip()
        existing_album = (
            db.query(Album)
            .filter(
                Album.artist_id == album.artist_id,
                Album.title == normalized_title,
                Album.id != album_id,
            )
            .first()
        )
        if existing_album:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un álbum con ese título para este artista",
            )
        album.title = normalized_title

    if payload.cover_url is not None:
        album.cover_url = payload.cover_url or settings.DEFAULT_ALBUM_COVER_URL

    if payload.release_date is not None:
        album.release_date = payload.release_date

    db.commit()
    db.refresh(album)

    album = apply_album_cover_fallback(album)
    return album


@router.get("/{album_id}/songs", response_model=list[SongResponse])
def get_album_songs(
    album_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    album = db.query(Album).filter(Album.id == album_id).first()

    if not album:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Álbum no encontrado",
        )

    songs = (
        db.query(Song)
        .filter(Song.album_id == album_id)
        .order_by(Song.track_number.asc(), Song.title.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    for song in songs:
        if not song.cover_url:
            song.cover_url = album.cover_url or settings.DEFAULT_SONG_COVER_URL

    return songs