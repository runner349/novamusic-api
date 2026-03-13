from pydantic import BaseModel, EmailStr, Field


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=255)
    new_password: str = Field(min_length=8, max_length=100)


class ResetPasswordResponse(BaseModel):
    message: str