from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import hmac
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.core.config import settings
from app.core.security import hash_password, verify_password, access_token, opaque_token, token_hash, csrf_token
from app.models.user import User
from app.models.auth import RefreshSession, PasswordReset
from app.services.email import send_reset_email

def now(): return datetime.now(timezone.utc)
def aware(d): return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d

def issue(db, user):
    refresh, csrf = opaque_token(), csrf_token()
    db.add(RefreshSession(user_id=user.id, token_hash=token_hash(refresh),
        csrf_hash=token_hash(csrf), expires_at=now()+timedelta(days=settings.REFRESH_TOKEN_DAYS)))
    db.commit()
    return access_token(user.id), refresh, csrf

def signup(db: Session, email, password, confirm):
    if password != confirm:
        raise HTTPException(422, "Passwords do not match")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(password))
    db.add(user); db.commit(); db.refresh(user)
    a, r, c = issue(db, user)
    return a, r, c

def signin(db: Session, email, password):
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash) or not user.is_active:
        raise HTTPException(401, "Invalid email or password")
    a, r, c = issue(db, user)
    return a, r, c

def rotate(db: Session, raw_refresh, raw_csrf):
    if not raw_refresh or not raw_csrf:
        raise HTTPException(401, "Invalid session")
    s = db.scalar(select(RefreshSession).where(
        RefreshSession.token_hash == token_hash(raw_refresh)).with_for_update())
    if not s or s.revoked_at or aware(s.expires_at) <= now():
        raise HTTPException(401, "Invalid session")
    if not hmac.compare_digest(s.csrf_hash, token_hash(raw_csrf)):
        raise HTTPException(403, "Invalid CSRF token")
    user = db.get(User, s.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Invalid session")
    s.revoked_at = now()
    db.flush()
    a, r, c = issue(db, user)
    return a, r, c

def logout(db: Session, raw_refresh, raw_csrf):
    if not raw_refresh or not raw_csrf:
        return
    s = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash(raw_refresh)))
    if s:
        if not hmac.compare_digest(s.csrf_hash, token_hash(raw_csrf)):
            raise HTTPException(403, "Invalid CSRF token")
        s.revoked_at = now()
        db.commit()

def forgot(db: Session, email):
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active: return
    raw = opaque_token()
    db.add(PasswordReset(user_id=user.id, token_hash=token_hash(raw),
        expires_at=now()+timedelta(minutes=settings.RESET_TOKEN_MINUTES)))
    db.commit()
    link = settings.FRONTEND_ORIGINS[0].rstrip("/") + "/reset-password?" + urlencode({"token": raw})
    try: send_reset_email(user.email, link)
    except Exception: pass  # Never expose SMTP details or tokens to callers.

def reset(db: Session, raw, password):
    rec = db.scalar(select(PasswordReset).where(
        PasswordReset.token_hash == token_hash(raw)).with_for_update())
    if not rec or rec.used_at or aware(rec.expires_at) <= now():
        raise HTTPException(400, "Invalid or expired reset token")
    user = db.get(User, rec.user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "Invalid or expired reset token")
    rec.used_at = now()
    user.password_hash = hash_password(password)
    db.execute(update(RefreshSession).where(
        RefreshSession.user_id == user.id, RefreshSession.revoked_at.is_(None)
    ).values(revoked_at=now()))
    db.commit()
