from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


def apply_user_photo_fallback(user: User) -> User:
    if not user.photo_url:
        user.photo_url = settings.DEFAULT_USER_PHOTO_URL
    return user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    current_user = apply_user_photo_fallback(current_user)
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if payload.username is not None:
        normalized_username = payload.username.strip()

        existing_user = (
            db.query(User)
            .filter(User.username == normalized_username, User.id != current_user.id)
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El nombre de usuario ya está en uso",
            )

        current_user.username = normalized_username

    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip() if payload.full_name else None

    if payload.photo_url is not None:
        current_user.photo_url = payload.photo_url or settings.DEFAULT_USER_PHOTO_URL

    db.commit()
    db.refresh(current_user)

    current_user = apply_user_photo_fallback(current_user)
    return current_user