from fastapi import APIRouter, Depends, Request, Response, Cookie, Header, HTTPException
from sqlalchemy.orm import Session
from slowapi import Limiter
from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.schemas.auth import SignupIn, SigninIn, ForgotIn, ResetIn, TokenOut, MessageOut
from app.services.auth import signup, signin, rotate, logout, forgot, reset

router = APIRouter(prefix="/auth", tags=["authentication"])

def set_cookies(response, refresh, csrf):
    common = dict(secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE,
                  domain=settings.COOKIE_DOMAIN, path="/",
                  max_age=settings.REFRESH_TOKEN_DAYS*86400)
    response.set_cookie("refresh_token", refresh, httponly=True, **common)
    # CSRF cookie is readable by React and must be echoed in X-CSRF-Token.
    response.set_cookie("csrf_token", csrf, httponly=False, **common)
    response.headers["Access-Control-Expose-Headers"] = "X-CSRF-Token"
    response.headers["X-CSRF-Token"] = csrf

def clear_cookies(response):
    for name in ("refresh_token", "csrf_token"):
        response.delete_cookie(name, path="/", domain=settings.COOKIE_DOMAIN,
            secure=settings.COOKIE_SECURE, httponly=(name == "refresh_token"),
            samesite=settings.COOKIE_SAMESITE)

def out(access):
    return TokenOut(access_token=access, expires_in=settings.ACCESS_TOKEN_MINUTES*60)

@router.post("/signup", response_model=TokenOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_SIGNUP)
def signup_route(request: Request, payload: SignupIn, response: Response, db: Session = Depends(get_db)):
    a, r, c = signup(db, payload.email, payload.password, payload.confirm_password)
    set_cookies(response, r, c); return out(a)

@router.post("/signin", response_model=TokenOut)
@limiter.limit(settings.RATE_LIMIT_SIGNIN)
def signin_route(request: Request, payload: SigninIn, response: Response, db: Session = Depends(get_db)):
    a, r, c = signin(db, payload.email, payload.password)
    set_cookies(response, r, c); return out(a)

@router.post("/refresh", response_model=TokenOut)
def refresh_route(response: Response, refresh: str | None = Cookie(None, alias="refresh_token"),
                  csrf: str | None = Cookie(None, alias="csrf_token"),
                  header_csrf: str | None = Header(None, alias="X-CSRF-Token"),
                  db: Session = Depends(get_db)):
    if not csrf or not header_csrf or csrf != header_csrf:
        raise HTTPException(403, "Invalid CSRF token")
    a, r, c = rotate(db, refresh or "", header_csrf)
    set_cookies(response, r, c); return out(a)

@router.post("/logout", response_model=MessageOut)
def logout_route(response: Response, refresh: str | None = Cookie(None, alias="refresh_token"),
                 csrf: str | None = Cookie(None, alias="csrf_token"),
                 header_csrf: str | None = Header(None, alias="X-CSRF-Token"),
                 db: Session = Depends(get_db)):
    if csrf and header_csrf and csrf != header_csrf:
        raise HTTPException(403, "Invalid CSRF token")
    logout(db, refresh or "", header_csrf or csrf or "")
    clear_cookies(response)
    return MessageOut(message="Logged out")

@router.post("/forgot-password", response_model=MessageOut)
@limiter.limit(settings.RATE_LIMIT_FORGOT)
def forgot_route(request: Request, payload: ForgotIn, db: Session = Depends(get_db)):
    forgot(db, payload.email)
    return MessageOut(message="If an account exists for that email, a reset link will be sent.")

@router.post("/reset-password", response_model=MessageOut)
def reset_route(payload: ResetIn, db: Session = Depends(get_db)):
    reset(db, payload.token, payload.new_password)
    return MessageOut(message="Password reset. Please sign in again.")
