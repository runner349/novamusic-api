from datetime import datetime, timedelta, timezone
import secrets
from typing import Any, Dict

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _build_token_payload(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_data: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: Dict[str, Any] = {
        "sub": subject,
        "token_type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    if extra_data:
        payload.update(extra_data)

    return payload


def create_access_token(
    subject: str,
    extra_data: Dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    expire_delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = _build_token_payload(
        subject=subject,
        token_type="access",
        expires_delta=expire_delta,
        extra_data=extra_data,
    )

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    subject: str,
    extra_data: Dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    refresh_expire_days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 30)
    expire_delta = expires_delta or timedelta(days=refresh_expire_days)

    payload = _build_token_payload(
        subject=subject,
        token_type="refresh",
        expires_delta=expire_delta,
        extra_data=extra_data,
    )

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)