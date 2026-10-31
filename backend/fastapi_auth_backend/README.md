# FastAPI Authentication Backend

## Stack
FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, Pydantic, Argon2, JWT, rotating opaque refresh tokens.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Set `DATABASE_URL`, `JWT_SECRET_KEY`, `TOKEN_PEPPER`, frontend origins and SMTP values.
Generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

Create the PostgreSQL database, then:
```bash
alembic upgrade head
uvicorn app.main:app --reload
```
Docs: `http://127.0.0.1:8000/docs`

## Endpoints
- `POST /api/auth/signup` `{email,password,confirm_password}`
- `POST /api/auth/signin` `{email,password}`
- `POST /api/auth/refresh` (refresh cookie + CSRF cookie/header)
- `POST /api/auth/logout`
- `POST /api/auth/forgot-password` `{email}`
- `POST /api/auth/reset-password` `{token,new_password}`
- `GET /api/users/me` (Bearer access token)
- `GET /health`

## React notes
Use `credentials: "include"` on signup/signin/refresh/logout. Read `X-CSRF-Token`
from the login response header and retain it in React memory; the API also sets a
readable `csrf_token` cookie so the frontend can recover it after a page reload.
Send that value as `X-CSRF-Token` for refresh/logout. Keep access tokens in memory,
not localStorage. Send access token as `Authorization: Bearer <token>`.

Example:
```js
const r = await fetch("http://localhost:8000/api/auth/signin", {
  method: "POST", credentials: "include",
  headers: {"Content-Type":"application/json"},
  body: JSON.stringify({email, password})
});
const {access_token} = await r.json();
const csrf = r.headers.get("X-CSRF-Token");
// Store access_token and csrf in React state/context.
```

## Security / deployment checklist
- Use HTTPS and set `COOKIE_SECURE=true` in production.
- Use exact frontend origins, never wildcard origins with credentials.
- Use `SameSite=None; Secure` only if frontend/API are genuinely cross-site and
  maintain CSRF protections; prefer same-site deployment.
- Keep `.env` out of Git and use a secret manager in production.
- Configure SMTP; without it reset emails are not delivered.
- The included SlowAPI limiter uses in-memory storage: replace with Redis for
  multi-worker/multi-instance production.
- Add monitoring, backups, dependency scanning, tests, and email verification.
- Review reset-token lifecycle and email delivery operationally before launch.
