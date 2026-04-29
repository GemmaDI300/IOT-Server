from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.shared.base_domain.schemas import BaseSchemaResponse


def _normalize_role_name_strict_letters(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("name cannot be empty or whitespace only")
    if len(trimmed) > 255:
        raise ValueError("name cannot exceed 255 characters")
    if not all(ch.isalpha() for ch in trimmed):
        raise ValueError("name must contain only letters (no digits, spaces, or symbols)")
    return trimmed


class RoleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    service_id: UUID
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _normalize_role_name_strict_letters(value)


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_role_name_strict_letters(value)


class RoleResponse(BaseSchemaResponse):
    name: str
    description: str | None
    service_id: UUID
    is_active: bool
