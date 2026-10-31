import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://brightloop:brightloop@localhost:5432/brightloop")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-please-32-bytes-min")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
