import os
import json
def _flag(name, default): return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://brightloop:brightloop@localhost:5432/brightloop")
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "dev-secret-change-me-please-32-bytes-min"))
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
CORS_RAW = os.getenv("CORS_ORIGINS", "*")
try:
    CORS_ORIGINS = json.loads(CORS_RAW) if CORS_RAW.lstrip().startswith("[") else [o.strip() for o in CORS_RAW.split(",") if o.strip()]
except json.JSONDecodeError:
    CORS_ORIGINS = [o.strip() for o in CORS_RAW.split(",") if o.strip()]
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()      # "production" turns on the start-up safety checks
# Reset/verify tokens are returned in API responses only when this is on (default: on in development, off in production).
DEV_RETURN_TOKENS = _flag("DEV_RETURN_TOKENS", "0" if ENVIRONMENT == "production" else "1")

# ---- abuse protection (in-memory, per API process; read at call time so tests can change them) ----
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))                 # wrong passwords per e-mail + IP ...
LOGIN_MAX_FAILURES_PER_IP = int(os.getenv("LOGIN_MAX_FAILURES_PER_IP", "30"))  # ... and per IP, within the window
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "900"))
RESET_MAX_REQUESTS = int(os.getenv("RESET_MAX_REQUESTS", "5"))                 # forgot-password requests per e-mail + IP per window
REGISTER_MAX_PER_IP = int(os.getenv("REGISTER_MAX_PER_IP", "30"))              # sign-ups per IP per hour
TRUST_FORWARDED_FOR = _flag("TRUST_FORWARDED_FOR", "0")                        # 1 only behind a proxy that overwrites X-Forwarded-For

# ---- e-mail delivery (read at call time, so tests can change them) ----
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", os.getenv("MAIL_BACKEND", "console"))        # console (log only) | smtp | memory (tests)
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("MAIL_FROM", "Brightloop Software <no-reply@brightloop.local>"))
SMTP_STARTTLS = _flag("SMTP_STARTTLS", "1")
SMTP_SSL = _flag("SMTP_SSL", "0")                            # implicit TLS (port 465); overrides STARTTLS
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")   # used to build links in e-mails

# ---- background jobs ----
SCHEDULER_ENABLED = _flag("SCHEDULER_ENABLED", os.getenv("ENABLE_SCHEDULER", "1"))          # run the in-process scheduler inside the API
OUTBOX_POLL_SECONDS = int(os.getenv("OUTBOX_POLL_SECONDS", "10"))
OUTBOX_MAX_ATTEMPTS = int(os.getenv("OUTBOX_MAX_ATTEMPTS", "5"))
DAILY_JOBS_HOUR = int(os.getenv("DAILY_JOBS_HOUR", "2"))     # server-local hour after which billing + reminders run once a day
REMINDER_INTERVAL_DAYS = int(os.getenv("REMINDER_INTERVAL_DAYS", "7"))
REMINDER_MAX = int(os.getenv("REMINDER_MAX", "4"))

def production_problems() -> list[str]:
    """Things that must not be left at their development defaults when ENVIRONMENT=production."""
    out = []
    if len(JWT_SECRET) < 32 or any(w in JWT_SECRET.lower() for w in ("change-me", "dev-secret", "changeme", "secret-key")):
        out.append("JWT_SECRET is a placeholder or shorter than 32 characters")
    if "*" in CORS_ORIGINS: out.append("CORS_ORIGINS must list the real front-end origin(s), not *")
    if DEV_RETURN_TOKENS: out.append("DEV_RETURN_TOKENS must be 0 (it returns reset/verify tokens in API responses)")
    if EMAIL_BACKEND != "smtp": out.append("EMAIL_BACKEND must be smtp (customers never receive reset links otherwise)")
    if not APP_BASE_URL.startswith("https://"): out.append("APP_BASE_URL must be an https:// address")
    return out

def assert_production_ready():
    if ENVIRONMENT == "production":
        probs = production_problems()
        if probs: raise RuntimeError("Refusing to start in production: " + "; ".join(probs))
