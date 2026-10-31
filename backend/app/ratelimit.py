"""Small in-memory sliding-window limiter (per API process).

Good enough to stop password guessing and mail-bombing from one client; with several API instances each keeps its own
counters, so put a shared limiter (reverse proxy / Redis) in front if you need a hard global limit."""
import threading, time
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from . import config

class Limiter:
    def __init__(self):
        self._h = defaultdict(deque); self._lock = threading.Lock()

    def _live(self, key, window, now):
        d = self._h[key]
        while d and d[0] <= now - window: d.popleft()
        return d

    def check(self, key: str, limit: int, window: int):
        """Raise 429 when `key` already has `limit` hits inside the window (does not add a hit)."""
        now = time.monotonic()
        with self._lock:
            d = self._live(key, window, now)
            if not d: self._h.pop(key, None)
            elif len(d) >= limit:
                raise HTTPException(429, "Too many attempts. Please wait and try again.", headers={"Retry-After": str(int(d[0] + window - now) + 1)})

    def hit(self, key: str, window: int):
        now = time.monotonic()
        with self._lock:
            self._live(key, window, now).append(now)
            if len(self._h) > 20000:        # drop idle keys so random e-mail addresses cannot grow memory without bound
                for k in [k for k, d in self._h.items() if not d or d[-1] <= now - window]: self._h.pop(k, None)

    def reset(self, key: str):
        with self._lock: self._h.pop(key, None)

    def clear(self):
        with self._lock: self._h.clear()

limiter = Limiter()

def client_ip(request: Request) -> str:
    if config.TRUST_FORWARDED_FOR:
        fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if fwd: return fwd
    return request.client.host if request.client else "unknown"
