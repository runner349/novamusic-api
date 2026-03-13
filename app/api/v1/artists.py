from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.core.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.song import Song
from app.models.user import User
from app.schemas.album import AlbumResponse
from app.schemas.artist import ArtistCreate, ArtistResponse, ArtistUpdate
from app.schemas.song import SongResponse

router = APIRouter(prefix="/artists", tags=["Artists"])


@router.post("", response_model=ArtistResponse, status_code=status.HTTP_201_CREATED)
def create_artist(
    payload: ArtistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "artist")),
):
    normalized_name = payload.name.strip()

    existing_artist = db.query(Artist).filter(Artist.name == normalized_name).first()
    if existing_artist:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un artista con ese nombre",
        )

    artist = Artist(
        name=normalized_name,
        bio=payload.bio,
        photo_url=payload.photo_url,
    )

    db.add(artist)
    db.commit()
    db.refresh(artist)

    return artist


@router.get("", response_model=list[ArtistResponse])
def get_artists(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    artists = (
        db.query(Artist)
        .order_by(Artist.name.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return artists


@router.get("/{artist_id}", response_model=ArtistResponse)
def get_artist_by_id(artist_id: int, db: Session = Depends(get_db)):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()

    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artista no encontrado",
        )

    return artist


@router.patch("/{artist_id}", response_model=ArtistResponse)
def update_artist(
    artist_id: int,
    payload: ArtistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "artist")),
):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()

    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artista no encontrado",
        )

    if payload.name is not None:
        normalized_name = payload.name.strip()
        existing_artist = (
            db.query(Artist)
            .filter(Artist.name == normalized_name, Artist.id != artist_id)
            .first()
        )
        if existing_artist:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un artista con ese nombre",
            )
        artist.name = normalized_name

    if payload.bio is not None:
        artist.bio = payload.bio

    if payload.photo_url is not None:
        artist.photo_url = payload.photo_url

    db.commit()
    db.refresh(artist)

    return artist


@router.get("/{artist_id}/albums", response_model=list[AlbumResponse])
def get_artist_albums(
    artist_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()

    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artista no encontrado",
        )

    albums = (
        db.query(Album)
        .filter(Album.artist_id == artist_id)
        .order_by(Album.release_date.desc(), Album.title.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return albums


@router.get("/{artist_id}/songs", response_model=list[SongResponse])
def get_artist_songs(
    artist_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()

    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artista no encontrado",
        )

    songs = (
        db.query(Song)
        .join(Album, Song.album_id == Album.id)
        .filter(Album.artist_id == artist_id)
        .order_by(Album.release_date.desc(), Song.track_number.asc(), Song.title.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return songs