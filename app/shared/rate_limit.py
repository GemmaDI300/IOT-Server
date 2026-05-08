import re

from fastapi import Depends, Request

from app.config import settings
from app.shared.session.exceptions import RateLimitExceededException
from app.shared.session.repository import SessionRepository


RATE_LIMIT_MAX_ATTEMPTS = 3
RATE_LIMIT_WINDOW_SECONDS = 1


def get_rate_limit_repository() -> SessionRepository:
    return SessionRepository(settings.VALKEY_URL)


def _slugify_scope(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return normalized.strip("-") or "unknown"


def _resolve_scope_name(request: Request) -> str:
    route = request.scope.get("route")
    tags = getattr(route, "tags", None) or []
    if tags:
        return _slugify_scope(str(tags[0]))

    path_format = getattr(route, "path_format", None)
    if path_format:
        return _slugify_scope(path_format)

    return _slugify_scope(request.url.path)


def _resolve_subject_name(request: Request) -> str:
    current_account = getattr(request.state, "current_account", None)
    if isinstance(current_account, dict):
        account_id = current_account.get("account_id")
        if account_id:
            return f"account:{account_id}"

    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def build_rate_limit_key(request: Request) -> str:
    scope_name = _resolve_scope_name(request)
    subject_name = _resolve_subject_name(request)
    return f"{scope_name}:{subject_name}"


async def enforce_request_rate_limit(
    request: Request,
    repository: SessionRepository = Depends(get_rate_limit_repository),
) -> None:
    key = build_rate_limit_key(request)

    try:
        current_attempts = await repository.increment_rate_limit(
            key,
            window_seconds=RATE_LIMIT_WINDOW_SECONDS,
        )
        if current_attempts > RATE_LIMIT_MAX_ATTEMPTS:
            retry_after = await repository.get_rate_limit_ttl(key)
            raise RateLimitExceededException(retry_after=max(retry_after, 1))
    finally:
        await repository.close()