import hashlib
from fastapi import HTTPException, status, Request
from app.shared.base_domain.controller import FullCrudApiController
from app.domain.application.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationCreateResponse,
    ApplicationUpdate,
    PuzzleRequest,
)
from app.domain.application.service import ApplicationServiceDep
from app.database import SessionDep
from app.shared.middleware.auth.applications.auth import CryptoManager
from app.shared.session.service import SessionService
from app.config import settings
from app.shared.authorization.dependencies import require_read, require_write, require_delete  # nuevo
from app.database.model import Application  # nuevo


class ApplicationController(FullCrudApiController):
    prefix = "/applications"
    tags = ["Applications"]
    service_dep = ApplicationServiceDep
    response_schema = ApplicationResponse
    create_schema = ApplicationCreate
    update_schema = ApplicationUpdate

    # nuevo
    list_dependencies = [require_read(Application)]
    retrieve_dependencies = [require_read(Application)]
    create_dependencies = [require_write(Application)]
    update_dependencies = [require_write(Application)]
    delete_dependencies = [require_delete(Application)]


application_router = ApplicationController().router

# Reemplazar POST / para retornar server_key
application_router.routes = [
    r for r in application_router.routes
    if not (hasattr(r, "methods") and "POST" in r.methods and r.path == "/applications/" and r.endpoint.__name__ == "create")
]


@application_router.post(
    "/",
    response_model=ApplicationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Applications"],
)
def create_application(service: ApplicationServiceDep, payload: ApplicationCreate):
    entity = service.create_entity(payload)
    server_key = hashlib.sha256(
        (settings.SECRET_KEY + "|puzzle_v1").encode("utf-8")
    ).hexdigest()
    entity_data = entity.model_dump()
    entity_data["server_key"] = server_key
    return ApplicationCreateResponse.model_validate(entity_data)


@application_router.post("/auth")
async def authenticate_application(
    puzzle: PuzzleRequest,
    session: SessionDep,
    request: Request,
):
    session_service = SessionService(
        valkey_url=settings.VALKEY_URL,
        encryption_key=settings.ENCRYPTION_KEY,
    )
    request_info = {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
    }
    crypto = CryptoManager(session, session_service)
    result = await crypto.authenticate(puzzle, request_info)
    if not result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["error"],
        )
    return result
