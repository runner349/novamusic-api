from supabase import Client, create_client

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
        )

    def get_public_file_url(self, bucket: str, path: str) -> str:
        response = self.client.storage.from_(bucket).get_public_url(path)

        if isinstance(response, dict):
            return response.get("publicURL") or response.get("public_url") or ""

        getter = getattr(response, "get", None)
        if callable(getter):
            return response.get("publicURL") or response.get("public_url") or ""

        return str(response)

    def create_signed_file_url(self, bucket: str, path: str, expires_in: int) -> str:
        response = self.client.storage.from_(bucket).create_signed_url(path, expires_in)

        if isinstance(response, dict):
            signed_url = response.get("signedURL") or response.get("signed_url")
            if not signed_url:
                raise ValueError("No se pudo generar la signed URL")
            return signed_url

        getter = getattr(response, "get", None)
        if callable(getter):
            value = response.get("signedURL") or response.get("signed_url")
            if not value:
                raise ValueError("No se pudo generar la signed URL")
            return value

        value = getattr(response, "signedURL", None) or getattr(response, "signed_url", None)
        if not value:
            raise ValueError("No se pudo generar la signed URL")
        return value

    def upload_file(
        self,
        bucket: str,
        path: str,
        file_bytes: bytes,
        content_type: str,
        upsert: bool = False,
    ):
        return self.client.storage.from_(bucket).upload(
            path,
            file_bytes,
            {
                "content-type": content_type,
                "upsert": str(upsert).lower(),
            },
        )


storage_service = StorageService()