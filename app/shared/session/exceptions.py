from fastapi import HTTPException, status


class SessionNotFoundException(HTTPException):
    """Raised when a session lookup fails for an authenticated request."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found",
        )


class SessionAlreadyExistsException(HTTPException):
    """Raised when trying to create a session for an entity that already has one."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active session already exists for this entity",
        )


class InvalidRefreshTokenException(HTTPException):
    """Raised when the supplied refresh token is missing, invalid or expired."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


class RateLimitExceededException(HTTPException):
    """Raised when an authentication attempt exceeds the configured rate limit."""

    def __init__(self, retry_after: int = 900):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Try again in {retry_after // 60} minutes.",
            headers={"Retry-After": str(retry_after)},
        )


class InvalidTokenException(HTTPException):
    """Raised when an access token is malformed, tampered with or unrecognised."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


class SessionExpiredException(HTTPException):
    """Raised when a session has surpassed its TTL."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )


class InvalidTagException(HTTPException):
    """Raised when the HMAC tag attached to a request fails verification."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid request signature",
        )


class InvalidEntityIdException(HTTPException):
    """Raised when ``entity_id`` is not a valid UUID."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entity_id format",
        )


class InvalidKeySessionException(HTTPException):
    """Raised when ``key_session`` does not meet the format/length contract.

    The underlying validation reason is intentionally kept out of the HTTP
    response to avoid leaking parsing internals to the client. Callers must
    log the specific reason internally via the application logger.
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key_session format",
        )


class InvalidMetadataException(HTTPException):
    """Raised when session metadata violates size, key or serialisation rules.

    The underlying validation reason is intentionally kept out of the HTTP
    response to avoid leaking parsing internals to the client. Callers must
    log the specific reason internally via the application logger.
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid metadata",
        )


class InvalidIpAddressException(HTTPException):
    """Raised when the supplied IP address is empty or malformed.

    The underlying validation reason is intentionally kept out of the HTTP
    response to avoid leaking parsing internals to the client. Callers must
    log the specific reason internally via the application logger.
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid IP address format",
        )
