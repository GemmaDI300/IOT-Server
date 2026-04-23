"""
IAuthManager + AuthManager — orquesta el flujo de autenticación.

Sigue el mismo patrón de IBaseService / BaseService del proyecto.

IAuthManager: interfaz que define qué debe hacer todo auth manager.
AuthManager: implementación base con el flujo genérico.

Proceso genérico:
    1. Verificar si la entidad existe
    2. Verificar si está activa
    3. Verificar sesión activa
    4. Autenticar (usando el método configurado)
    5. Generar llave de sesión
    6. Crear sesión
"""

import base64
import logging
import secrets
from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar
from uuid import UUID

from app.shared.base_domain.model import BaseTable
from app.shared.base_domain.repository import BaseRepository
from app.shared.session.service import SessionService
from sqlmodel import Session

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseTable)


class IAuthManager(ABC):
    """
    Interfaz que define qué debe hacer todo auth manager.

    Equivalente a IBaseService del proyecto.
    """

    @abstractmethod
    def _find_entity(self, entity_id: UUID):
        """Buscar la entidad en BD."""
        ...

    @abstractmethod
    def _get_entity_id(self, request_data) -> UUID:
        """Extraer el ID de la entidad desde el request."""
        ...

    @abstractmethod
    def _generate_session_key(self) -> bytes:
        """Generar llave de sesión única."""
        ...

    @abstractmethod
    async def authenticate(self, request_data) -> dict:
        """Ejecutar el flujo completo de autenticación."""
        ...


class AuthManager(IAuthManager, Generic[T]):
    """
    Implementación base del flujo de autenticación.

    Equivalente a BaseService del proyecto.

    Cada hijo define:
        - repository_class: clase del repository de la entidad
        - _auth_methods: dict con los tipos disponibles
        - _get_entity_id: cómo extraer el ID del request

    Uso:
        manager = DeviceAuthManager(session, session_service, auth_type="rc")
        result = await manager.authenticate(request_data)
    """

    repository_class: ClassVar[type[BaseRepository]]
    _auth_methods: ClassVar[dict[str, type]]

    def __init__(self, session: Session, session_service: SessionService, auth_type: str):
        self.session = session
        self.session_service = session_service
        self.auth_type = auth_type
        self.repository: BaseRepository[T] = self.repository_class(session)
        self._authenticator = self._resolve_auth_type(auth_type)

    def _find_entity(self, entity_id: UUID) -> T | None:
        """Buscar la entidad en BD usando el repository."""
        return self.repository.get_by_id(entity_id)

    def _resolve_auth_type(self, auth_type: str):
        """
        Resolver el tipo de autenticación desde el registro.
        Retorna una instancia del autenticador.
        """
        auth_class = self._auth_methods.get(auth_type)
        if not auth_class:
            available = ", ".join(self._auth_methods.keys()) or "ninguno"
            raise ValueError(
                f"Tipo de autenticación '{auth_type}' no disponible. "
                f"Disponibles: {available}"
            )
        return auth_class()

    def _generate_session_key(self) -> bytes:
        """
        Generar llave de sesión única.
        - Longitud: 32 bytes (256 bits)
        - Aleatoriedad: criptográficamente segura
        - Unicidad: única por sesión
        """
        return secrets.token_bytes(32)

    async def authenticate(self, request_data) -> dict:
        entity_id = self._get_entity_id(request_data)
        entity_id_str = str(entity_id)

        # 1. Verificar si existe
        entity = self._find_entity(entity_id)
        if not entity:
            logger.warning(f"Auth failed: entity {entity_id_str} not found")
            return {"valid": False, "error": "Authentication failed"}

        # 2. Verificar si está activa
        if not entity.is_active:
            logger.warning(f"Auth failed: entity {entity_id_str} inactive")
            return {"valid": False, "error": "Authentication failed"}

        # 3. Verificar sesión activa
        existing_session = await self.session_service.get_session(entity_id_str)
        if existing_session:
            logger.warning(f"Auth failed: entity {entity_id_str} already has active session")
            return {"valid": False, "error": "Authentication failed"}

        # 4. Autenticar (usando el método configurado)
        result = self._authenticator.authenticate(entity, request_data)
        if not result["valid"]:
            return result

        # 5. Generar llave de sesión
        session_key = self._generate_session_key()
        key_session = base64.urlsafe_b64encode(session_key).decode()

        # 6. Crear sesión (id + llave)
        result = await self.session_service.create_entity_session(
            entity_id=entity_id_str,
            key_session=key_session,
        )

        return {
            "valid": True,
            "session_id": result.session_id,
            "encrypted_token": result.encrypted_token,
            "key_session": key_session,
        }
