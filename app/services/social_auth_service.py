import time
from typing import Any

import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import jwk, jwt
from jose.utils import base64url_decode

from app.core.config import settings


class SocialAuthError(Exception):
    pass


def verify_google_identity_token(token: str) -> dict[str, Any]:
    try:
        id_info = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        raise SocialAuthError("Token de Google inválido") from exc

    email = id_info.get("email")
    if not email:
        raise SocialAuthError("Google no devolvió un correo válido")

    return {
        "provider": "google",
        "provider_user_id": id_info.get("sub"),
        "email": email.lower().strip(),
        "full_name": id_info.get("name"),
        "photo_url": id_info.get("picture"),
        "is_verified": bool(id_info.get("email_verified", False)),
    }


def verify_apple_identity_token(token: str) -> dict[str, Any]:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise SocialAuthError("Token de Apple inválido") from exc

    kid = unverified_header.get("kid")
    if not kid:
        raise SocialAuthError("No se pudo identificar la clave pública de Apple")

    try:
        jwks_response = requests.get("https://appleid.apple.com/auth/keys", timeout=10)
        jwks_response.raise_for_status()
        jwks = jwks_response.json()
    except Exception as exc:
        raise SocialAuthError("No se pudo obtener las claves públicas de Apple") from exc

    key_data = next((key for key in jwks.get("keys", []) if key.get("kid") == kid), None)
    if not key_data:
        raise SocialAuthError("No se encontró la clave pública de Apple")

    try:
        public_key = jwk.construct(key_data)
        message, encoded_signature = token.rsplit(".", 1)
        decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))

        if not public_key.verify(message.encode("utf-8"), decoded_signature):
            raise SocialAuthError("Firma de Apple inválida")

        claims = jwt.get_unverified_claims(token)
    except SocialAuthError:
        raise
    except Exception as exc:
        raise SocialAuthError("No se pudo validar el token de Apple") from exc

    issuer = claims.get("iss")
    audience = claims.get("aud")
    exp = claims.get("exp")
    email = claims.get("email")
    sub = claims.get("sub")

    if issuer != settings.APPLE_ISSUER:
        raise SocialAuthError("Issuer de Apple inválido")

    if audience != settings.APPLE_AUDIENCE:
        raise SocialAuthError("Audience de Apple inválido")

    if not exp or int(exp) < int(time.time()):
        raise SocialAuthError("Token de Apple expirado")

    if not email:
        raise SocialAuthError("Apple no devolvió un correo válido")

    if not sub:
        raise SocialAuthError("Apple no devolvió un identificador de usuario")

    return {
        "provider": "apple",
        "provider_user_id": sub,
        "email": email.lower().strip(),
        "full_name": None,
        "photo_url": None,
        "is_verified": True,
    }