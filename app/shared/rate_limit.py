"""
Sliding-window in-memory rate limiter.

Returns a FastAPI dependency factory.  Tracks requests per (scope, client IP)
so that different routers maintain independent counters.

Usage:
    from app.shared.rate_limit import rate_limiter
    from fastapi import Depends

    router_dependencies = [Depends(rate_limiter(max_requests=3, window_seconds=1.0, scope="managers"))]
"""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status


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
