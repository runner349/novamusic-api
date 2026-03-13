import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import require_roles
from app.core.config import settings
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.services.storage_service import storage_service

router = APIRouter(prefix="/uploads", tags=["Uploads"])


ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/aac",
    "audio/ogg",
}

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/jpg",
}


def _build_file_path(folder: str, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return f"{folder}/{unique_name}"


def _read_upload_file(file: UploadFile) -> tuple[bytes, str]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe tener nombre",
        )

    content_type = file.content_type or "application/octet-stream"
    file_bytes = file.file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío",
        )

    return file_bytes, content_type


@router.post("/songs/audio", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_song_audio(
    file: UploadFile = File(...),
    artist_id: int = Form(...),
    album_id: int = Form(...),
    current_user: User = Depends(require_roles("admin", "artist")),
):
    file_bytes, content_type = _read_upload_file(file)

    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo de audio no permitido",
        )

    folder = f"artist_{artist_id}/album_{album_id}"
    path = _build_file_path(folder, file.filename)

    try:
        storage_service.upload_file(
            bucket=settings.SUPABASE_AUDIO_BUCKET,
            path=path,
            file_bytes=file_bytes,
            content_type=content_type,
            upsert=False,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo subir el audio a Supabase Storage",
        )

    return UploadResponse(
        bucket=settings.SUPABASE_AUDIO_BUCKET,
        path=path,
        public_url=None,
        content_type=content_type,
        size=len(file_bytes),
        message="Audio subido correctamente",
    )


@router.post("/albums/cover", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_album_cover(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("admin", "artist")),
):
    file_bytes, content_type = _read_upload_file(file)

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de imagen no permitido",
        )

    path = _build_file_path("albums", file.filename)

    try:
        storage_service.upload_file(
            bucket=settings.SUPABASE_IMAGE_BUCKET,
            path=path,
            file_bytes=file_bytes,
            content_type=content_type,
            upsert=False,
        )
        public_url = storage_service.get_public_file_url(
            bucket=settings.SUPABASE_IMAGE_BUCKET,
            path=path,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo subir la portada del álbum",
        )

    return UploadResponse(
        bucket=settings.SUPABASE_IMAGE_BUCKET,
        path=path,
        public_url=public_url,
        content_type=content_type,
        size=len(file_bytes),
        message="Portada de álbum subida correctamente",
    )


@router.post("/artists/photo", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_artist_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("admin", "artist")),
):
    file_bytes, content_type = _read_upload_file(file)

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de imagen no permitido",
        )

    path = _build_file_path("artists", file.filename)

    try:
        storage_service.upload_file(
            bucket=settings.SUPABASE_IMAGE_BUCKET,
            path=path,
            file_bytes=file_bytes,
            content_type=content_type,
            upsert=False,
        )
        public_url = storage_service.get_public_file_url(
            bucket=settings.SUPABASE_IMAGE_BUCKET,
            path=path,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo subir la foto del artista",
        )

    return UploadResponse(
        bucket=settings.SUPABASE_IMAGE_BUCKET,
        path=path,
        public_url=public_url,
        content_type=content_type,
        size=len(file_bytes),
        message="Foto de artista subida correctamente",
    )


@router.post("/users/photo", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_user_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("admin", "artist", "user")),
):
    file_bytes, content_type = _read_upload_file(file)

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de imagen no permitido",
        )

    path = _build_file_path("users", file.filename)

    try:
        storage_service.upload_file(
            bucket=settings.SUPABASE_IMAGE_BUCKET,
            path=path,
            file_bytes=file_bytes,
            content_type=content_type,
            upsert=False,
        )
        public_url = storage_service.get_public_file_url(
            bucket=settings.SUPABASE_IMAGE_BUCKET,
            path=path,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo subir la foto del usuario",
        )

    return UploadResponse(
        bucket=settings.SUPABASE_IMAGE_BUCKET,
        path=path,
        public_url=public_url,
        content_type=content_type,
        size=len(file_bytes),
        message="Foto de usuario subida correctamente",
    )


@router.post("/playlists/cover", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_playlist_cover(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("admin", "artist", "user")),
):
    file_bytes, content_type = _read_upload_file(file)

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de imagen no permitido",
        )

    path = _build_file_path("playlists", file.filename)

    try:
        storage_service.upload_file(
            bucket=settings.SUPABASE_IMAGE_BUCKET,
            path=path,
            file_bytes=file_bytes,
            content_type=content_type,
            upsert=False,
        )
        public_url = storage_service.get_public_file_url(
            bucket=settings.SUPABASE_IMAGE_BUCKET,
            path=path,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo subir la portada de la playlist",
        )

    return UploadResponse(
        bucket=settings.SUPABASE_IMAGE_BUCKET,
        path=path,
        public_url=public_url,
        content_type=content_type,
        size=len(file_bytes),
        message="Portada de playlist subida correctamente",
    )