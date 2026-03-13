from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    EMAIL_USER: str
    EMAIL_PASSWORD: str
    EMAIL_FROM: str
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    SUPABASE_URL: str
    SUPABASE_KEY: str

    SUPABASE_AUDIO_BUCKET: str = "songs"
    SUPABASE_IMAGE_BUCKET: str = "images"
    SUPABASE_SIGNED_URL_EXPIRE_SECONDS: int = 3600

    GOOGLE_CLIENT_ID: str
    APPLE_AUDIENCE: str
    APPLE_ISSUER: str = "https://appleid.apple.com"

    class Config:
        env_file = ".env"


settings = Settings()