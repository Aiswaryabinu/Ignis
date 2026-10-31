import re, uuid, hashlib
from datetime import datetime, timedelta, timezone
import bcrypt, jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .config import JWT_SECRET, JWT_EXPIRE_MINUTES
from .db import get_db
from .models import User, Customer

def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt()).decode()
def verify_password(p: str, h: str) -> bool:
    try: return bcrypt.checkpw(p.encode()[:72], h.encode())
    except ValueError: return False

def password_problems(p: str) -> list[str]:
    out = []
    if len(p) <= 8: out.append("more than 8 characters")
    if not re.search(r"[A-Z]", p): out.append("an uppercase letter")
    if not re.search(r"[a-z]", p): out.append("a lowercase letter")
    if not re.search(r"[^A-Za-z0-9]", p): out.append("a special character")
    return out

_DUMMY_HASH = None
def burn_password_check(p: str):
    """Spend the same time as a real check, so an unknown e-mail cannot be told apart from a wrong password by timing."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None: _DUMMY_HASH = hash_password("not-a-real-password")
    verify_password(p, _DUMMY_HASH)

def password_stamp(user: User) -> str:
    """Changes whenever the password does, so every older token stops working (reset, change, admin reset)."""
    return hashlib.sha256(user.password_hash.encode()).hexdigest()[:16]

def make_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user.id), "role": user.role, "pv": password_stamp(user), "iat": now,
                       "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES)}, JWT_SECRET, algorithm="HS256")

def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Not authenticated")
    try:
        data = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"], options={"require": ["exp", "sub"]})
        u = db.get(User, uuid.UUID(str(data["sub"])))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Invalid or expired token")
    if not u or not u.is_active: raise HTTPException(401, "Account disabled")
    if data.get("pv") != password_stamp(u): raise HTTPException(401, "Your session has ended. Please sign in again.")   # password changed since this token was issued
    return u

def require(*roles):
    def dep(u: User = Depends(current_user)) -> User:
        if u.role not in roles: raise HTTPException(403, "You do not have access to this")
        return u
    return dep

staff_or_admin = require("ADMIN", "STAFF")
admin_only = require("ADMIN")

def customer_of(db: Session, u: User):
    return db.query(Customer).filter(Customer.user_id == u.id).first()
