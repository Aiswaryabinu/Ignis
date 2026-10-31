import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access
from app.models.user import User

bearer = HTTPBearer(auto_error=False)

def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db)):
    if not creds: raise HTTPException(401, "Not authenticated")
    try: uid = int(decode_access(creds.credentials)["sub"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(401, "Invalid or expired access token")
    user = db.get(User, uid)
    if not user or not user.is_active: raise HTTPException(401, "Invalid user")
    return user
