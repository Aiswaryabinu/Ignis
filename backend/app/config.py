"""Application configuration loaded from environment variables."""

import os
from typing import List


DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://brightloop:brightloop@localhost:5432/brightloop",
)

JWT_SECRET: str = os.getenv(
    "JWT_SECRET", "dev-secret-change-me-please-32-bytes-min"
)
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))

CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Rate-limiting (requests per minute per IP for auth endpoints)
AUTH_RATE_LIMIT: int = int(os.getenv("AUTH_RATE_LIMIT", "20"))

# bcrypt hashing rounds
BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))
