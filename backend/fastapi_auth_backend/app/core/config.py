from functools import lru_cache
from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Auth API"
    DEBUG: bool = False
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    TOKEN_PEPPER: str
    ACCESS_TOKEN_MINUTES: int = 10
    REFRESH_TOKEN_DAYS: int = 14
    RESET_TOKEN_MINUTES: int = 20
    FRONTEND_ORIGINS: list[str] = ["http://localhost:5173"]
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    COOKIE_DOMAIN: str | None = None
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "no-reply@example.com"
    SMTP_USE_TLS: bool = True
    RATE_LIMIT_SIGNUP: str = "5/minute"
    RATE_LIMIT_SIGNIN: str = "10/minute"
    RATE_LIMIT_FORGOT: str = "3/hour"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("FRONTEND_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        return [x.strip() for x in v.split(",")] if isinstance(v, str) else v

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
