"""API key authentication and per-key sliding-window rate limiting."""

from __future__ import annotations

import hmac
import threading
import time
from collections import deque

from fastapi import Header, HTTPException, status

from src import config


class _RateLimiter:
    def __init__(self, max_calls: int, window_seconds: float = 60.0) -> None:
        self._max_calls = max_calls
        self._window = window_seconds
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def is_allowed(self) -> bool:
        """Return True if the request is within the rate limit window."""
        now = time.monotonic()
        with self._lock:
            cutoff = now - self._window
            while self._calls and self._calls[0] < cutoff:
                self._calls.popleft()
            if len(self._calls) >= self._max_calls:
                return False
            self._calls.append(now)
            return True


_rate_limiter = _RateLimiter(max_calls=config.RATE_LIMIT_PER_MINUTE)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """FastAPI dependency that enforces API key auth and rate limiting."""
    if not config.API_KEY:
        return  # API key auth disabled

    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Api-Key header.",
        )
    if not hmac.compare_digest(x_api_key, config.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )
    if not _rate_limiter.is_allowed():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Slow down.",
            headers={"Retry-After": "60"},
        )
