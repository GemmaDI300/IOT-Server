import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.shared.auth.service import get_shared_auth_service


class StubAuthService:
    def __init__(self):
        self.calls: list[tuple[str, object, bool | None]] = []

    def login_human_rc(self, payload, expected_is_master=None):
        self.calls.append(("login_human_rc", payload, expected_is_master))
        return {
            "access_token": "token",
            "token_type": "bearer",
            "account_type": payload.entity_type,
            "auth_method": "auth_rc",
            "is_master": expected_is_master is True,
        }

    def create_xmss_challenge(self, payload, expected_is_master=None):
        self.calls.append(("create_xmss_challenge", payload, expected_is_master))
        return {
            "auth_method": "auth_xmss",
            "entity_type": payload.entity_type,
            "identifier": payload.identifier,
            "challenge": "challenge",
            "leaf_index": 0,
            "expires_at": 1234567890,
            "public_root": "root",
            "canonical_message": {"identifier": payload.identifier},
            "client_material_compact": None,
        }

    def verify_xmss(self, payload, expected_is_master=None):
        self.calls.append(("verify_xmss", payload, expected_is_master))
        return {
            "access_token": "token",
            "token_type": "bearer",
            "account_type": payload.entity_type,
            "auth_method": "auth_xmss",
            "is_master": expected_is_master is True,
        }

    def login_device_rc(self, payload):
        self.calls.append(("login_device_rc", payload, None))
        return {
            "access_token": "token",
            "token_type": "bearer",
            "account_type": "device",
            "auth_method": "auth_rc",
            "is_master": False,
        }

    def login_application_rc(self, payload):
        self.calls.append(("login_application_rc", payload, None))
        return {
            "access_token": "token",
            "token_type": "bearer",
            "account_type": "application",
            "auth_method": "auth_rc",
            "is_master": False,
        }


def _override_service():
    service = StubAuthService()
    app.dependency_overrides[get_shared_auth_service] = lambda: service
    return service


def _clear_override():
    app.dependency_overrides.pop(get_shared_auth_service, None)


@pytest.fixture(autouse=True)
def auth_policy_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "AUTH_ADMINISTRATOR_METHOD", "auth_xmss")
    monkeypatch.setattr(settings, "AUTH_MANAGER_METHOD", "auth_rc")
    monkeypatch.setattr(settings, "AUTH_USER_METHOD", "auth_rc")
    monkeypatch.setattr(settings, "AUTH_DEVICE_METHOD", "auth_rc")
    monkeypatch.setattr(settings, "AUTH_APPLICATION_METHOD", "auth_xmss")


class TestHumanAuthSplitRoutes:
    @pytest.mark.parametrize(
        ("path", "email", "expected_entity_type", "expected_is_master"),
        [
            ("/api/v1/auth-rc/user/login", "USER@TEST.COM", "user", None),
            ("/api/v1/auth-rc/manager/login", "MANAGER@TEST.COM", "manager", None),
        ],
    )
    def test_auth_rc_login_allows_configured_entities(
        self,
        client: TestClient,
        path: str,
        email: str,
        expected_entity_type: str,
        expected_is_master: bool | None,
    ):
        service = _override_service()

        try:
            response = client.post(
                path,
                json={
                    "email": email,
                    "password": "Password123!",
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 200
        call_name, payload, actual_is_master = service.calls[-1]
        assert call_name == "login_human_rc"
        assert payload.entity_type == expected_entity_type
        assert payload.email == email.lower()
        assert actual_is_master is expected_is_master

    @pytest.mark.parametrize(
        ("path", "email"),
        [
            ("/api/v1/auth-rc/admin/login", "regular_admin@test.com"),
            ("/api/v1/auth-rc/master/login", "MASTER_ADMIN@TEST.COM"),
        ],
    )
    def test_auth_rc_login_rejects_entities_configured_for_other_method(
        self,
        client: TestClient,
        path: str,
        email: str,
    ):
        service = _override_service()

        try:
            response = client.post(
                path,
                json={
                    "email": email,
                    "password": "Password123!",
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 403
        assert service.calls == []

    @pytest.mark.parametrize(
        (
            "path",
            "identifier",
            "expected_entity_type",
            "expected_is_master",
        ),
        [
            ("/api/v1/auth-xmss/admin/challenge", "ADMIN@TEST.COM", "administrator", False),
            ("/api/v1/auth-xmss/master/challenge", "MASTER_ADMIN@TEST.COM", "administrator", True),
        ],
    )
    def test_auth_xmss_challenge_allows_configured_entities(
        self,
        client: TestClient,
        path: str,
        identifier: str,
        expected_entity_type: str,
        expected_is_master: bool | None,
    ):
        service = _override_service()

        try:
            response = client.post(
                path,
                json={
                    "identifier": identifier,
                    "password": "XmssPassword123!",
                    "tree_height": 6,
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 200
        call_name, payload, actual_is_master = service.calls[-1]
        assert call_name == "create_xmss_challenge"
        assert payload.entity_type == expected_entity_type
        assert payload.identifier == identifier.lower()
        assert payload.password == "XmssPassword123!"
        assert payload.tree_height == 6
        assert actual_is_master is expected_is_master

    @pytest.mark.parametrize(
        ("path", "identifier"),
        [
            ("/api/v1/auth-xmss/user/challenge", "USER@TEST.COM"),
            ("/api/v1/auth-xmss/manager/challenge", "MANAGER@TEST.COM"),
        ],
    )
    def test_auth_xmss_challenge_rejects_entities_configured_for_rc(
        self,
        client: TestClient,
        path: str,
        identifier: str,
    ):
        service = _override_service()

        try:
            response = client.post(
                path,
                json={
                    "identifier": identifier,
                    "password": "XmssPassword123!",
                    "tree_height": 6,
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 403
        assert service.calls == []

    @pytest.mark.parametrize(
        (
            "path",
            "identifier",
            "expected_entity_type",
            "expected_is_master",
        ),
        [
            ("/api/v1/auth-xmss/admin/verify", "ADMIN@TEST.COM", "administrator", False),
            ("/api/v1/auth-xmss/master/verify", "MASTER_ADMIN@TEST.COM", "administrator", True),
        ],
    )
    def test_auth_xmss_verify_allows_configured_entities(
        self,
        client: TestClient,
        path: str,
        identifier: str,
        expected_entity_type: str,
        expected_is_master: bool | None,
    ):
        service = _override_service()

        try:
            response = client.post(
                path,
                json={
                    "identifier": identifier,
                    "challenge": "challenge",
                    "leaf_index": 0,
                    "message": {"challenge": "challenge"},
                    "signature": {},
                    "auth_path": [],
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 200
        call_name, payload, actual_is_master = service.calls[-1]
        assert call_name == "verify_xmss"
        assert payload.entity_type == expected_entity_type
        assert payload.identifier == identifier.lower()
        assert actual_is_master is expected_is_master

    @pytest.mark.parametrize(
        ("path", "identifier"),
        [
            ("/api/v1/auth-xmss/user/verify", "USER@TEST.COM"),
            ("/api/v1/auth-xmss/manager/verify", "MANAGER@TEST.COM"),
        ],
    )
    def test_auth_xmss_verify_rejects_entities_configured_for_rc(
        self,
        client: TestClient,
        path: str,
        identifier: str,
    ):
        service = _override_service()

        try:
            response = client.post(
                path,
                json={
                    "identifier": identifier,
                    "challenge": "challenge",
                    "leaf_index": 0,
                    "message": {"challenge": "challenge"},
                    "signature": {},
                    "auth_path": [],
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 403
        assert service.calls == []


class TestEntityAuthPolicyRoutes:
    def test_auth_rc_device_login_allowed_by_policy(self, client: TestClient):
        service = _override_service()

        try:
            response = client.post(
                "/api/v1/auth-rc/devices/login",
                json={
                    "identifier": "device-123",
                    "encrypted_payload": {
                        "ciphertext": "abc",
                        "iv": "def",
                    },
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 200
        call_name, payload, _ = service.calls[-1]
        assert call_name == "login_device_rc"
        assert payload.identifier == "device-123"

    def test_auth_rc_application_login_rejected_by_policy(self, client: TestClient):
        service = _override_service()

        try:
            response = client.post(
                "/api/v1/auth-rc/applications/login",
                json={
                    "identifier": "app-123",
                    "encrypted_payload": {
                        "ciphertext": "abc",
                        "iv": "def",
                    },
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 403
        assert service.calls == []

    def test_auth_xmss_device_challenge_rejected_by_policy(self, client: TestClient):
        service = _override_service()

        try:
            response = client.post(
                "/api/v1/auth-xmss/devices/challenge",
                json={
                    "entity_type": "device",
                    "identifier": "device-123",
                    "tree_height": 4,
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 403
        assert service.calls == []

    def test_auth_xmss_application_challenge_allowed_by_policy(self, client: TestClient):
        service = _override_service()

        try:
            response = client.post(
                "/api/v1/auth-xmss/applications/challenge",
                json={
                    "entity_type": "application",
                    "identifier": "app-123",
                    "tree_height": 4,
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 200
        call_name, payload, _ = service.calls[-1]
        assert call_name == "create_xmss_challenge"
        assert payload.entity_type == "application"

    def test_auth_xmss_application_verify_allowed_by_policy(self, client: TestClient):
        service = _override_service()

        try:
            response = client.post(
                "/api/v1/auth-xmss/applications/verify",
                json={
                    "entity_type": "application",
                    "identifier": "app-123",
                    "challenge": "challenge",
                    "leaf_index": 0,
                    "message": {"challenge": "challenge"},
                    "signature": {},
                    "auth_path": [],
                },
            )
        finally:
            _clear_override()

        assert response.status_code == 200
        call_name, payload, _ = service.calls[-1]
        assert call_name == "verify_xmss"
        assert payload.entity_type == "application"