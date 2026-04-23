"""Tests para AuthManager — flujo de autenticación."""
import base64
import pytest
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from app.shared.middleware.auth.auth_manager.base import AuthManager


# ── Fakes para testear sin BD ni Valkey ─────────────────────────────

FAKE_ID = uuid4()


@dataclass
class FakeEntity:
    id: UUID = field(default_factory=lambda: FAKE_ID)
    is_active: bool = True
    name: str = "Test Entity"


class FakeRepository:
    """Repository falso que retorna entidades controladas."""

    def __init__(self, session, entity=None):
        self._entity = entity

    def get_by_id(self, entity_id):
        if self._entity and str(self._entity.id) == str(entity_id):
            return self._entity
        return None


class FakeAuthSuccess:
    """Autenticador falso que siempre pasa."""

    def authenticate(self, entity, request_data) -> dict:
        return {"valid": True}


class FakeAuthFail:
    """Autenticador falso que siempre falla."""

    def authenticate(self, entity, request_data) -> dict:
        return {"valid": False, "error": "Authentication failed"}


class FakeRequest:
    """Request falso con entity_id."""

    def __init__(self, entity_id: UUID = FAKE_ID):
        self.entity_id = entity_id


# ── Manager concreto para tests ─────────────────────────────────────

class StubAuthManager(AuthManager[FakeEntity]):
    """Manager concreto para testear el flujo base."""

    repository_class = FakeRepository
    _auth_methods = {
        "success": FakeAuthSuccess,
        "fail": FakeAuthFail,
    }

    def _get_entity_id(self, request_data) -> UUID:
        return request_data.entity_id


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def mock_session_service():
    service = AsyncMock()
    service.get_session.return_value = None
    service.create_entity_session.return_value = MagicMock(
        session_id="test-session-id",
        encrypted_token="test-encrypted-token",
    )
    return service


@pytest.fixture
def active_entity():
    return FakeEntity(id=FAKE_ID, is_active=True)


@pytest.fixture
def inactive_entity():
    return FakeEntity(id=FAKE_ID, is_active=False)


# ── Tests: flujo exitoso ────────────────────────────────────────────

class TestAuthManagerSuccess:
    """Flujo completo exitoso."""

    @pytest.mark.asyncio
    async def test_valid_auth_returns_valid(self, mock_session_service, active_entity):
        FakeRepository._shared_entity = active_entity
        original_init = FakeRepository.__init__

        def patched_init(self, session, entity=None):
            original_init(self, session, entity=active_entity)

        FakeRepository.__init__ = patched_init

        manager = StubAuthManager(None, mock_session_service, auth_type="success")
        result = await manager.authenticate(FakeRequest())

        assert result["valid"] is True
        assert "session_id" in result
        assert "encrypted_token" in result
        assert "key_session" in result

        FakeRepository.__init__ = original_init

    @pytest.mark.asyncio
    async def test_session_key_is_base64(self, mock_session_service, active_entity):
        original_init = FakeRepository.__init__

        def patched_init(self, session, entity=None):
            original_init(self, session, entity=active_entity)

        FakeRepository.__init__ = patched_init

        manager = StubAuthManager(None, mock_session_service, auth_type="success")
        result = await manager.authenticate(FakeRequest())

        key_bytes = base64.urlsafe_b64decode(result["key_session"])
        assert len(key_bytes) == 32

        FakeRepository.__init__ = original_init

    @pytest.mark.asyncio
    async def test_create_session_called_with_correct_params(self, mock_session_service, active_entity):
        original_init = FakeRepository.__init__

        def patched_init(self, session, entity=None):
            original_init(self, session, entity=active_entity)

        FakeRepository.__init__ = patched_init

        manager = StubAuthManager(None, mock_session_service, auth_type="success")
        await manager.authenticate(FakeRequest())

        mock_session_service.create_entity_session.assert_called_once()
        call_kwargs = mock_session_service.create_entity_session.call_args[1]
        assert call_kwargs["entity_id"] == str(FAKE_ID)
        assert "key_session" in call_kwargs

        FakeRepository.__init__ = original_init


# ── Tests: entidad no encontrada ────────────────────────────────────

class TestAuthManagerEntityNotFound:
    """Entidad no existe → falla."""

    @pytest.mark.asyncio
    async def test_nonexistent_entity_fails(self, mock_session_service):
        manager = StubAuthManager(None, mock_session_service, auth_type="success")
        fake_id = uuid4()
        result = await manager.authenticate(FakeRequest(entity_id=fake_id))

        assert result["valid"] is False
        assert result["error"] == "Authentication failed"


# ── Tests: entidad inactiva ─────────────────────────────────────────

class TestAuthManagerEntityInactive:
    """Entidad inactiva → falla."""

    @pytest.mark.asyncio
    async def test_inactive_entity_fails(self, mock_session_service, inactive_entity):
        original_init = FakeRepository.__init__

        def patched_init(self, session, entity=None):
            original_init(self, session, entity=inactive_entity)

        FakeRepository.__init__ = patched_init

        manager = StubAuthManager(None, mock_session_service, auth_type="success")
        result = await manager.authenticate(FakeRequest())

        assert result["valid"] is False
        assert result["error"] == "Authentication failed"

        FakeRepository.__init__ = original_init


# ── Tests: sesión activa ────────────────────────────────────────────

class TestAuthManagerSessionActive:
    """Sesión ya activa → falla."""

    @pytest.mark.asyncio
    async def test_active_session_fails(self, mock_session_service, active_entity):
        mock_session_service.get_session.return_value = MagicMock()

        original_init = FakeRepository.__init__

        def patched_init(self, session, entity=None):
            original_init(self, session, entity=active_entity)

        FakeRepository.__init__ = patched_init

        manager = StubAuthManager(None, mock_session_service, auth_type="success")
        result = await manager.authenticate(FakeRequest())

        assert result["valid"] is False
        assert result["error"] == "Authentication failed"

        FakeRepository.__init__ = original_init


# ── Tests: autenticación falla ──────────────────────────────────────

class TestAuthManagerAuthFails:
    """Método de autenticación falla → falla."""

    @pytest.mark.asyncio
    async def test_auth_method_fails(self, mock_session_service, active_entity):
        original_init = FakeRepository.__init__

        def patched_init(self, session, entity=None):
            original_init(self, session, entity=active_entity)

        FakeRepository.__init__ = patched_init

        manager = StubAuthManager(None, mock_session_service, auth_type="fail")
        result = await manager.authenticate(FakeRequest())

        assert result["valid"] is False
        assert result["error"] == "Authentication failed"

        FakeRepository.__init__ = original_init


# ── Tests: tipo de auth inválido ────────────────────────────────────

class TestAuthManagerInvalidType:
    """Tipo de autenticación no registrado → ValueError."""

    def test_invalid_auth_type_raises(self, mock_session_service):
        with pytest.raises(ValueError, match="no disponible"):
            StubAuthManager(None, mock_session_service, auth_type="xyz")


# ── Tests: llave de sesión ──────────────────────────────────────────

class TestAuthManagerSessionKey:
    """Llave de sesión tiene las propiedades correctas."""

    def test_session_key_is_32_bytes(self):
        manager = StubAuthManager.__new__(StubAuthManager)
        key = manager._generate_session_key()

        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_session_keys_are_unique(self):
        manager = StubAuthManager.__new__(StubAuthManager)
        key1 = manager._generate_session_key()
        key2 = manager._generate_session_key()

        assert key1 != key2
