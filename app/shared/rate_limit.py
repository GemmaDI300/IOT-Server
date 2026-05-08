"""
Rate limiter utilities.

Provides:
  - rate_limiter()  – in-memory sliding-window factory (legacy, per-router)
  - build_rate_limit_key() – derive a Valkey-friendly key from a Request
  - enforce_request_rate_limit() – async FastAPI dependency backed by Valkey

Usage:
    from app.shared.rate_limit import rate_limiter, enforce_request_rate_limit
    from fastapi import Depends

    router_dependencies = [Depends(rate_limiter(max_requests=3, window_seconds=1.0, scope="managers"))]
    # or:
    router_dependencies = [Depends(enforce_request_rate_limit)]
"""
import time
from collections import defaultdict, deque
from functools import lru_cache
from threading import Lock
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.config import settings
from app.shared.session.exceptions import RateLimitExceededException
from app.shared.session.repository import SessionRepository


# Key: "<scope>:<client_ip>"  →  deque of monotonic timestamps
_windows: defaultdict[str, deque] = defaultdict(deque)
_lock = Lock()


def rate_limiter(max_requests: int = 3, window_seconds: float = 1.0, scope: str = "default"):
    """
    Factory that returns a FastAPI dependency enforcing a sliding-window rate
    limit of *max_requests* per *window_seconds* per (scope, client IP).

    Each unique *scope* keeps its own counter, so different routers do not
    share their quota.  Raises HTTP 429 when the limit is exceeded.
    """

    def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        bucket = f"{scope}:{client_ip}"
        now = time.monotonic()
        window_start = now - window_seconds

        with _lock:
            log = _windows[bucket]

            # Evict timestamps that have fallen outside the window
            while log and log[0] < window_start:
                log.popleft()

            if len(log) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Rate limit exceeded: max {max_requests} requests "
                        f"per {window_seconds:.0f} second(s)."
                    ),
                    headers={"Retry-After": "1"},
                )

            log.append(now)

    return dependency


# ---------------------------------------------------------------------------
# Valkey-backed rate limiter (new, distributed)
# ---------------------------------------------------------------------------

_MAX_REQUESTS = 3
_WINDOW_SECONDS = 1


def build_rate_limit_key(request: Request) -> str:
    """
    Derive a stable, namespaced rate-limit key from the request.

    Format:
      ``{tag-slug}:account:{account_id}``  when the request carries an
                                            authenticated account in state
      ``{tag-slug}:ip:{client_ip}``        for unauthenticated requests

    The tag slug is the first route tag lowercased with spaces replaced by '-'.
    Falls back to the route path when no tag is available.
    """
    route = getattr(request, "route", None) or getattr(
        request.scope.get("route"), "__dict__", {}
    )
    tags = getattr(route, "tags", None) or []
    if tags:
        slug = str(tags[0]).lower().replace(" ", "-")
    else:
        slug = request.url.path.strip("/").replace("/", "-") or "default"

    account = getattr(request.state, "current_account", None)
    if account and isinstance(account, dict):
        account_id = account.get("account_id", "")
        if account_id:
            return f"{slug}:account:{account_id}"

    client_ip = request.client.host if request.client else "unknown"
    return f"{slug}:ip:{client_ip}"


@lru_cache(maxsize=1)
def _get_rate_limit_repository() -> SessionRepository:
    """Singleton SessionRepository used exclusively for rate limiting."""
    return SessionRepository(settings.VALKEY_URL)


async def enforce_request_rate_limit(
    request: Request,
    repository: Annotated[SessionRepository, Depends(_get_rate_limit_repository)],
) -> None:
    """
    Async FastAPI dependency that enforces a sliding-window rate limit backed
    by Valkey.  Raises :class:`RateLimitExceededException` (HTTP 429) when
    the caller exceeds *_MAX_REQUESTS* requests inside *_WINDOW_SECONDS*.
    """
    key = build_rate_limit_key(request)
    count = await repository.increment_rate_limit(key, window_seconds=_WINDOW_SECONDS)
    if count > _MAX_REQUESTS:
        retry_after = await repository.get_rate_limit_ttl(key)
        raise RateLimitExceededException(retry_after=max(retry_after, 1))
