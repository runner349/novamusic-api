from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db import base  # noqa: F401
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.album import Album
from app.models.artist import Artist
from app.models.favorite_song import FavoriteSong
from app.models.play_history import PlayHistory
from app.models.playlist import Playlist
from app.models.playlist_song import PlaylistSong
from app.models.song import Song
from app.models.user import User


DEFAULT_USER_PHOTO = "https://placehold.co/400x400/png?text=User"
DEFAULT_ARTIST_PHOTO = "https://placehold.co/600x600/png?text=Artist"
DEFAULT_ALBUM_COVER = "https://placehold.co/800x800/png?text=Album"
DEFAULT_PLAYLIST_COVER = "https://placehold.co/800x800/png?text=Playlist"
DEFAULT_SONG_COVER = None


def get_or_create_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    role: str,
    full_name: str | None = None,
    photo_url: str | None = None,
    auth_provider: str = "local",
    is_active: bool = True,
    is_verified: bool = True,
) -> User:
    user = db.query(User).filter(User.email == email).first()

    if user:
        user.username = username
        user.full_name = full_name
        user.photo_url = photo_url or DEFAULT_USER_PHOTO
        user.role = role
        user.auth_provider = auth_provider
        user.is_active = is_active
        user.is_verified = is_verified

        if auth_provider == "local":
            user.password_hash = hash_password(password)

        db.commit()
        db.refresh(user)
        return user

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password) if auth_provider == "local" else None,
        full_name=full_name,
        photo_url=photo_url or DEFAULT_USER_PHOTO,
        role=role,
        auth_provider=auth_provider,
        provider_user_id=None,
        is_active=is_active,
        is_verified=is_verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_artist(
    db: Session,
    *,
    name: str,
    user_id: int | None = None,
    bio: str | None = None,
    photo_url: str | None = None,
) -> Artist:
    artist = db.query(Artist).filter(Artist.name == name).first()

    if artist:
        artist.user_id = user_id
        artist.bio = bio
        artist.photo_url = photo_url or DEFAULT_ARTIST_PHOTO
        db.commit()
        db.refresh(artist)
        return artist

    artist = Artist(
        user_id=user_id,
        name=name,
        bio=bio,
        photo_url=photo_url or DEFAULT_ARTIST_PHOTO,
    )
    db.add(artist)
    db.commit()
    db.refresh(artist)
    return artist


def get_or_create_album(
    db: Session,
    *,
    artist_id: int,
    title: str,
    cover_url: str | None = None,
    release_date: date | None = None,
) -> Album:
    album = (
        db.query(Album)
        .filter(Album.artist_id == artist_id, Album.title == title)
        .first()
    )

    if album:
        album.cover_url = cover_url or DEFAULT_ALBUM_COVER
        album.release_date = release_date or album.release_date
        db.commit()
        db.refresh(album)
        return album

    album = Album(
        artist_id=artist_id,
        title=title,
        cover_url=cover_url or DEFAULT_ALBUM_COVER,
        release_date=release_date or date.today(),
    )
    db.add(album)
    db.commit()
    db.refresh(album)
    return album


def get_or_create_song(
    db: Session,
    *,
    album_id: int,
    title: str,
    duration_seconds: int,
    track_number: int,
    audio_path: str,
    cover_url: str | None = None,
    plays_count: int = 0,
) -> Song:
    song = (
        db.query(Song)
        .filter(Song.album_id == album_id, Song.track_number == track_number)
        .first()
    )

    if song:
        song.title = title
        song.duration_seconds = duration_seconds
        song.audio_path = audio_path
        song.cover_url = cover_url
        song.plays_count = plays_count
        db.commit()
        db.refresh(song)
        return song

    song = Song(
        album_id=album_id,
        title=title,
        duration_seconds=duration_seconds,
        track_number=track_number,
        audio_path=audio_path,
        cover_url=cover_url,
        plays_count=plays_count,
    )
    db.add(song)
    db.commit()
    db.refresh(song)
    return song


def get_or_create_playlist(
    db: Session,
    *,
    user_id: int,
    title: str,
    description: str | None = None,
    cover_url: str | None = None,
    is_public: bool = True,
) -> Playlist:
    playlist = (
        db.query(Playlist)
        .filter(Playlist.user_id == user_id, Playlist.title == title)
        .first()
    )

    if playlist:
        playlist.description = description
        playlist.cover_url = cover_url or DEFAULT_PLAYLIST_COVER
        playlist.is_public = is_public
        db.commit()
        db.refresh(playlist)
        return playlist

    playlist = Playlist(
        user_id=user_id,
        title=title,
        description=description,
        cover_url=cover_url or DEFAULT_PLAYLIST_COVER,
        is_public=is_public,
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist


def ensure_playlist_song(
    db: Session,
    *,
    playlist_id: int,
    song_id: int,
    position: int,
) -> None:
    existing = (
        db.query(PlaylistSong)
        .filter(
            PlaylistSong.playlist_id == playlist_id,
            PlaylistSong.song_id == song_id,
        )
        .first()
    )

    if existing:
        existing.position = position
        db.commit()
        return

    item = PlaylistSong(
        playlist_id=playlist_id,
        song_id=song_id,
        position=position,
    )
    db.add(item)
    db.commit()


def ensure_favorite(
    db: Session,
    *,
    user_id: int,
    song_id: int,
) -> None:
    existing = (
        db.query(FavoriteSong)
        .filter(
            FavoriteSong.user_id == user_id,
            FavoriteSong.song_id == song_id,
        )
        .first()
    )

    if existing:
        return

    favorite = FavoriteSong(
        user_id=user_id,
        song_id=song_id,
    )
    db.add(favorite)
    db.commit()


def ensure_play_history(
    db: Session,
    *,
    user_id: int,
    song_id: int,
    seconds_listened: int,
    played_at: datetime | None = None,
) -> None:
    existing = (
        db.query(PlayHistory)
        .filter(
            PlayHistory.user_id == user_id,
            PlayHistory.song_id == song_id,
            PlayHistory.seconds_listened == seconds_listened,
        )
        .first()
    )

    if existing:
        return

    item = PlayHistory(
        user_id=user_id,
        song_id=song_id,
        seconds_listened=seconds_listened,
        played_at=played_at or datetime.now(UTC),
    )
    db.add(item)
    db.commit()


def seed() -> None:
    db = SessionLocal()

    try:
        print("🌱 Iniciando seed de NovaMusic...")

        # Usuarios
        admin = get_or_create_user(
            db,
            username="admin",
            email="admin@novamusic.com",
            password="12345678",
            role="admin",
            full_name="NovaMusic Admin",
        )

        user_1 = get_or_create_user(
            db,
            username="gabriel",
            email="gabriel@test.com",
            password="12345678",
            role="user",
            full_name="Gabriel Dev",
        )

        user_2 = get_or_create_user(
            db,
            username="ralf",
            email="ralf@test.com",
            password="12345678",
            role="user",
            full_name="Ralf User",
        )

        artist_user_1 = get_or_create_user(
            db,
            username="artistgabriel",
            email="artistgabriel@test.com",
            password="12345678",
            role="artist",
            full_name="Gabriel Artist",
        )

        artist_user_2 = get_or_create_user(
            db,
            username="artistralf",
            email="artistralf@test.com",
            password="12345678",
            role="artist",
            full_name="Ralf Artist",
        )

        print("✅ Usuarios creados/actualizados")

        # Artistas catálogo, vinculados a sus usuarios artist
        artist_1 = get_or_create_artist(
            db,
            name="Gabriel Music",
            user_id=artist_user_1.id,
            bio="Artista urbano de prueba para NovaMusic.",
        )

        artist_2 = get_or_create_artist(
            db,
            name="Ralf Beats",
            user_id=artist_user_2.id,
            bio="Productor y artista de prueba para NovaMusic.",
        )

        print("✅ Artistas creados/actualizados")

        # Álbumes
        album_1 = get_or_create_album(
            db,
            artist_id=artist_1.id,
            title="Primer Álbum",
            release_date=date(2026, 3, 1),
        )

        album_2 = get_or_create_album(
            db,
            artist_id=artist_2.id,
            title="Noches de Prueba",
            release_date=date(2026, 3, 5),
        )

        print("✅ Álbumes creados/actualizados")

        # Canciones
        song_1 = get_or_create_song(
            db,
            album_id=album_1.id,
            title="Mi Primera Canción",
            duration_seconds=210,
            track_number=1,
            audio_path="seed/gabriel_music/primer_album/mi_primera_cancion.mp3",
            cover_url=DEFAULT_SONG_COVER,
            plays_count=12,
        )

        song_2 = get_or_create_song(
            db,
            album_id=album_1.id,
            title="Modo Dev",
            duration_seconds=185,
            track_number=2,
            audio_path="seed/gabriel_music/primer_album/modo_dev.mp3",
            cover_url=DEFAULT_SONG_COVER,
            plays_count=7,
        )

        song_3 = get_or_create_song(
            db,
            album_id=album_2.id,
            title="Beat de Medianoche",
            duration_seconds=201,
            track_number=1,
            audio_path="seed/ralf_beats/noches_de_prueba/beat_de_medianoche.mp3",
            cover_url=DEFAULT_SONG_COVER,
            plays_count=18,
        )

        song_4 = get_or_create_song(
            db,
            album_id=album_2.id,
            title="Render Nights",
            duration_seconds=232,
            track_number=2,
            audio_path="seed/ralf_beats/noches_de_prueba/render_nights.mp3",
            cover_url=DEFAULT_SONG_COVER,
            plays_count=5,
        )

        print("✅ Canciones creadas/actualizadas")

        # Playlists
        playlist_1 = get_or_create_playlist(
            db,
            user_id=user_1.id,
            title="Mis Favoritas",
            description="Playlist seed pública",
            is_public=True,
        )

        playlist_2 = get_or_create_playlist(
            db,
            user_id=user_2.id,
            title="Study Mode",
            description="Playlist seed privada",
            is_public=False,
        )

        ensure_playlist_song(db, playlist_id=playlist_1.id, song_id=song_1.id, position=1)
        ensure_playlist_song(db, playlist_id=playlist_1.id, song_id=song_3.id, position=2)
        ensure_playlist_song(db, playlist_id=playlist_1.id, song_id=song_2.id, position=3)

        ensure_playlist_song(db, playlist_id=playlist_2.id, song_id=song_4.id, position=1)
        ensure_playlist_song(db, playlist_id=playlist_2.id, song_id=song_2.id, position=2)

        print("✅ Playlists creadas/actualizadas")

        # Favoritos
        ensure_favorite(db, user_id=user_1.id, song_id=song_1.id)
        ensure_favorite(db, user_id=user_1.id, song_id=song_3.id)
        ensure_favorite(db, user_id=user_2.id, song_id=song_2.id)

        print("✅ Favoritos creados")

        # Historial
        now = datetime.now(UTC)

        ensure_play_history(
            db,
            user_id=user_1.id,
            song_id=song_1.id,
            seconds_listened=120,
            played_at=now - timedelta(hours=5),
        )
        ensure_play_history(
            db,
            user_id=user_1.id,
            song_id=song_3.id,
            seconds_listened=95,
            played_at=now - timedelta(hours=3),
        )
        ensure_play_history(
            db,
            user_id=user_1.id,
            song_id=song_2.id,
            seconds_listened=40,
            played_at=now - timedelta(hours=1),
        )
        ensure_play_history(
            db,
            user_id=user_2.id,
            song_id=song_4.id,
            seconds_listened=180,
            played_at=now - timedelta(hours=2),
        )

        print("✅ Historial creado")
        print("🎉 Seed completado correctamente")
        print("Admin: admin@novamusic.com / 12345678")
        print("User: gabriel@test.com / 12345678")
        print("Artist user: artistgabriel@test.com / 12345678")

    finally:
        db.close()


if __name__ == "__main__":
    seed()