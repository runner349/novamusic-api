from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    GoogleAuthRequest,
    AppleAuthRequest,
    RefreshTokenRequest,
    AuthResponse,
    TokenResponse,
    MessageResponse,
)
from app.schemas.password_reset import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.schemas.user import UserCreate, UserResponse
from app.services.email_service import send_reset_email
from app.services.social_auth_service import (
    SocialAuthError,
    verify_google_identity_token,
    verify_apple_identity_token,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def build_auth_response(user: User, access_token: str, refresh_token: str) -> AuthResponse:
    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ),
    )


def create_and_store_tokens(db: Session, user: User) -> tuple[str, str]:
    access_token = create_access_token(
        subject=str(user.id),
        extra_data={"email": user.email, "role": user.role},
    )

    refresh_token_value = create_refresh_token(
        subject=str(user.id),
        extra_data={"email": user.email},
    )

    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_value,
        expires_at=refresh_expires_at,
        is_revoked=False,
    )

    db.add(refresh_token)
    db.commit()

    return access_token, refresh_token_value


def resolve_username_from_email(email: str) -> str:
    return email.split("@")[0][:50]


def get_or_create_social_user(
    db: Session,
    *,
    email: str,
    provider: str,
    provider_user_id: str,
    full_name: str | None,
    photo_url: str | None,
    is_verified: bool,
) -> User:
    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user:
        if not existing_user.provider_user_id:
            existing_user.provider_user_id = provider_user_id

        if existing_user.auth_provider == "local":
            pass
        else:
            existing_user.auth_provider = provider

        if full_name and not existing_user.full_name:
            existing_user.full_name = full_name

        if photo_url and not existing_user.photo_url:
            existing_user.photo_url = photo_url

        if is_verified:
            existing_user.is_verified = True

        db.commit()
        db.refresh(existing_user)
        return existing_user

    base_username = resolve_username_from_email(email)
    candidate_username = base_username
    suffix = 1

    while db.query(User).filter(User.username == candidate_username).first():
        candidate_username = f"{base_username[:45]}_{suffix}"
        suffix += 1

    user = User(
        username=candidate_username,
        email=email,
        password_hash=None,
        full_name=full_name,
        photo_url=photo_url,
        role="user",
        auth_provider=provider,
        provider_user_id=provider_user_id,
        is_active=True,
        is_verified=is_verified,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()
    normalized_username = payload.username.strip()

    existing_user_by_email = db.query(User).filter(User.email == normalized_email).first()
    if existing_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está registrado",
        )

    existing_user_by_username = db.query(User).filter(User.username == normalized_username).first()
    if existing_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre de usuario ya está en uso",
        )

    new_user = User(
        username=normalized_username,
        email=normalized_email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip() if payload.full_name else None,
        photo_url=payload.photo_url,
        role="user",
        auth_provider="local",
        is_active=True,
        is_verified=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token, refresh_token_value = create_and_store_tokens(db, new_user)

    return build_auth_response(new_user, access_token, refresh_token_value)


@router.post("/login", response_model=AuthResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()

    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or user.auth_provider != "local" or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    access_token, refresh_token_value = create_and_store_tokens(db, user)

    return build_auth_response(user, access_token, refresh_token_value)


@router.post("/token", response_model=TokenResponse)
def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    normalized_email = form_data.username.strip().lower()

    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or user.auth_provider != "local" or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    access_token = create_access_token(
        subject=str(user.id),
        extra_data={"email": user.email, "role": user.role},
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=None,
        token_type="bearer",
    )


@router.post("/google", response_model=AuthResponse)
def login_with_google(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    try:
        social_data = verify_google_identity_token(payload.id_token)
    except SocialAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    user = get_or_create_social_user(
        db,
        email=social_data["email"],
        provider=social_data["provider"],
        provider_user_id=social_data["provider_user_id"],
        full_name=social_data["full_name"],
        photo_url=social_data["photo_url"],
        is_verified=social_data["is_verified"],
    )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    access_token, refresh_token_value = create_and_store_tokens(db, user)

    return build_auth_response(user, access_token, refresh_token_value)


@router.post("/apple", response_model=AuthResponse)
def login_with_apple(payload: AppleAuthRequest, db: Session = Depends(get_db)):
    try:
        social_data = verify_apple_identity_token(payload.id_token)
    except SocialAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    user = get_or_create_social_user(
        db,
        email=social_data["email"],
        provider=social_data["provider"],
        provider_user_id=social_data["provider_user_id"],
        full_name=social_data["full_name"],
        photo_url=social_data["photo_url"],
        is_verified=social_data["is_verified"],
    )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    access_token, refresh_token_value = create_and_store_tokens(db, user)

    return build_auth_response(user, access_token, refresh_token_value)


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido",
    )

    try:
        decoded = decode_token(payload.refresh_token)
        user_id = decoded.get("sub")
        token_type = decoded.get("token_type")

        if user_id is None or token_type != "refresh":
            raise credentials_exception

        user_id = int(user_id)

    except Exception:
        raise credentials_exception

    stored_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token == payload.refresh_token,
            RefreshToken.is_revoked == False,
        )
        .first()
    )

    if not stored_token:
        raise credentials_exception

    if stored_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception

    new_access_token = create_access_token(
        subject=str(user.id),
        extra_data={"email": user.email, "role": user.role},
    )

    new_refresh_token_value = create_refresh_token(
        subject=str(user.id),
        extra_data={"email": user.email},
    )

    new_refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    stored_token.is_revoked = True

    new_refresh_token = RefreshToken(
        user_id=user.id,
        token=new_refresh_token_value,
        expires_at=new_refresh_expires_at,
        is_revoked=False,
    )

    db.add(new_refresh_token)
    db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token_value,
        token_type="bearer",
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()

    user = db.query(User).filter(User.email == normalized_email).first()

    generic_response = ForgotPasswordResponse(
        message="Si el correo existe, se enviaron instrucciones de recuperación"
    )

    if not user:
        return generic_response

    if user.auth_provider != "local":
        return generic_response

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ).update({"used": True})

    token = generate_reset_token()
    expires_at = datetime.utcnow() + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
        used=False,
    )

    db.add(reset_token)
    db.commit()

    try:
        send_reset_email(user.email, token)
    except Exception:
        pass

    return generic_response


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token == payload.token)
        .first()
    )

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token de recuperación no válido",
        )

    if reset_token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este token ya fue utilizado",
        )

    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El token ha expirado",
        )

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if user.auth_provider != "local":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este usuario no usa contraseña local",
        )

    user.password_hash = hash_password(payload.new_password)
    reset_token.used = True

    db.commit()

    return ResetPasswordResponse(
        message="Contraseña actualizada correctamente"
    )


@router.post("/logout", response_model=MessageResponse)
def logout(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    stored_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token == payload.refresh_token,
            RefreshToken.is_revoked == False,
        )
        .first()
    )

    if stored_token:
        stored_token.is_revoked = True
        db.commit()

    return MessageResponse(message="Sesión cerrada correctamente")