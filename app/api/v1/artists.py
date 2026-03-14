from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_roles
from app.core.config import settings
from app.core.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.song import Song
from app.models.user import User
from app.schemas.album import AlbumResponse
from app.schemas.artist import ArtistCreate, ArtistResponse, ArtistUpdate
from app.schemas.song import SongResponse

router = APIRouter(prefix="/artists", tags=["Artists"])


def apply_artist_photo_fallback(artist: Artist) -> Artist:
    if not artist.photo_url:
        artist.photo_url = settings.DEFAULT_ARTIST_PHOTO_URL
    return artist


@router.post("", response_model=ArtistResponse, status_code=status.HTTP_201_CREATED)
def create_artist(
    payload: ArtistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    normalized_name = payload.name.strip()

    existing_artist = db.query(Artist).filter(Artist.name == normalized_name).first()
    if existing_artist:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un artista con ese nombre",
        )

    if payload.user_id is not None:
        user = db.query(User).filter(User.id == payload.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        if user.role != "artist":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario asociado debe tener rol artist",
            )

        existing_link = db.query(Artist).filter(Artist.user_id == payload.user_id).first()
        if existing_link:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ese usuario ya tiene un perfil de artista asociado",
            )

    artist = Artist(
        user_id=payload.user_id,
        name=normalized_name,
        bio=payload.bio,
        photo_url=payload.photo_url or settings.DEFAULT_ARTIST_PHOTO_URL,
    )

    db.add(artist)
    db.commit()
    db.refresh(artist)

    artist = apply_artist_photo_fallback(artist)
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

    return [apply_artist_photo_fallback(artist) for artist in artists]


@router.get("/{artist_id}", response_model=ArtistResponse)
def get_artist_by_id(artist_id: int, db: Session = Depends(get_db)):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()

    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artista no encontrado",
        )

    artist = apply_artist_photo_fallback(artist)
    return artist


@router.patch("/{artist_id}", response_model=ArtistResponse)
def update_artist(
    artist_id: int,
    payload: ArtistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    artist = db.query(Artist).filter(Artist.id == artist_id).first()

    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artista no encontrado",
        )

    if current_user.role == "artist":
        if artist.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes editar el perfil de otro artista",
            )
    elif current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para editar artistas",
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
        artist.photo_url = payload.photo_url or settings.DEFAULT_ARTIST_PHOTO_URL

    db.commit()
    db.refresh(artist)

    artist = apply_artist_photo_fallback(artist)
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

    for album in albums:
        if not album.cover_url:
            album.cover_url = settings.DEFAULT_ALBUM_COVER_URL

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

    for song in songs:
        if not song.cover_url:
            album = db.query(Album).filter(Album.id == song.album_id).first()
            song.cover_url = (
                album.cover_url if album and album.cover_url else settings.DEFAULT_SONG_COVER_URL
            )

    return songs