from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=10)


class AppleAuthRequest(BaseModel):
    id_token: str = Field(min_length=10)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class LogoutResponse(BaseModel):
    message: str


class MessageResponse(BaseModel):
    message: str