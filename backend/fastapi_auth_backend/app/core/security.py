import hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from app.core.config import settings

_hasher = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(password, hashed)
    except Exception:
        return False

def access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now,
               "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES),
               "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

def decode_access(token: str):
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"],
                         options={"require": ["exp", "iat", "sub"]})
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    return payload

def opaque_token() -> str:
    return secrets.token_urlsafe(48)

def token_hash(token: str) -> str:
    return hmac.new(settings.TOKEN_PEPPER.encode(), token.encode(), hashlib.sha256).hexdigest()

def csrf_token() -> str:
    return secrets.token_urlsafe(32)
