from enum import StrEnum

from fastapi import HTTPException, status

from app.config import settings


class AuthMethod(StrEnum):
    AUTH_RC = "auth_rc"
    AUTH_XMSS = "auth_xmss"


class EntityType(StrEnum):
    ADMINISTRATOR = "administrator"
    MANAGER = "manager"
    USER = "user"
    DEVICE = "device"
    APPLICATION = "application"


def get_auth_policy() -> dict[str, str]:
    return {
        EntityType.ADMINISTRATOR.value: settings.AUTH_ADMINISTRATOR_METHOD,
        EntityType.MANAGER.value: settings.AUTH_MANAGER_METHOD,
        EntityType.USER.value: settings.AUTH_USER_METHOD,
        EntityType.DEVICE.value: settings.AUTH_DEVICE_METHOD,
        EntityType.APPLICATION.value: settings.AUTH_APPLICATION_METHOD,
    }


def normalize_entity_type(entity_type: str) -> str:
    entity_type = entity_type.strip().lower()
    allowed_entities = {entity.value for entity in EntityType}

    if entity_type not in allowed_entities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entity type",
        )

    return entity_type


def normalize_auth_method(auth_method: str) -> str:
    auth_method = auth_method.strip().lower()
    allowed_methods = {method.value for method in AuthMethod}

    if auth_method not in allowed_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authentication method",
        )

    return auth_method


def get_auth_method_for_entity(entity_type: str) -> str:
    entity_type = normalize_entity_type(entity_type)
    policy = get_auth_policy()
    configured_method = policy[entity_type].strip().lower()
    allowed_methods = {method.value for method in AuthMethod}

    if configured_method not in allowed_methods:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid authentication method configured for {entity_type}",
        )

    return configured_method


def validate_auth_method_for_entity(entity_type: str, requested_method: str) -> None:
    entity_type = normalize_entity_type(entity_type)
    requested_method = normalize_auth_method(requested_method)
    configured_method = get_auth_method_for_entity(entity_type)

    if configured_method != requested_method:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"{entity_type} must authenticate using {configured_method} "
                f"in this deployment"
            ),
        )