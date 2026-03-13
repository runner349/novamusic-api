from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.song import Song
from app.schemas.search import SearchResponse, ArtistSearch, AlbumSearch
from app.schemas.song import SongResponse

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = q.strip()

    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La búsqueda no puede estar vacía",
        )

    songs = (
        db.query(Song)
        .join(Album, Song.album_id == Album.id)
        .join(Artist, Album.artist_id == Artist.id)
        .filter(
            or_(
                Song.title.ilike(f"%{query}%"),
                Artist.name.ilike(f"%{query}%"),
            )
        )
        .order_by(Song.plays_count.desc(), Song.title.asc())
        .limit(limit)
        .all()
    )

    artists = (
        db.query(Artist)
        .filter(Artist.name.ilike(f"%{query}%"))
        .order_by(Artist.name.asc())
        .limit(limit)
        .all()
    )

    albums = (
        db.query(Album)
        .join(Artist, Album.artist_id == Artist.id)
        .filter(
            or_(
                Album.title.ilike(f"%{query}%"),
                Artist.name.ilike(f"%{query}%"),
            )
        )
        .order_by(Album.title.asc())
        .limit(limit)
        .all()
    )

    return SearchResponse(
        songs=[SongResponse.model_validate(song) for song in songs],
        artists=[
            ArtistSearch(
                id=artist.id,
                name=artist.name,
                photo_url=artist.photo_url,
            )
            for artist in artists
        ],
        albums=[
            AlbumSearch(
                id=album.id,
                title=album.title,
                cover_url=album.cover_url,
                artist_id=album.artist_id,
            )
            for album in albums
        ],
    )