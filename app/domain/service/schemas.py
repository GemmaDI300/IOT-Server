from uuid import UUID
from pydantic import BaseModel
from app.shared.base_domain.schemas import BaseSchemaResponse


class ServiceCreate(BaseModel):
    name: str
    description: str | None = None
    administrator_id: UUID


class ServiceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class ServiceResponse(BaseSchemaResponse):
    name: str
    description: str | None
    administrator_id: UUID
    is_active: bool


# ── Schemas para tablas intermedias ─────────────────────────────────

class ManagerServiceResponse(BaseSchemaResponse):
    manager_id: UUID
    service_id: UUID


class ApplicationServiceResponse(BaseSchemaResponse):
    application_id: UUID
    service_id: UUID


class DeviceServiceResponse(BaseSchemaResponse):
    device_id: UUID
    service_id: UUID
