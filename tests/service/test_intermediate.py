"""Tests para tablas intermedias de Service — managers, applications, devices."""
import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt
from app.config import settings

APP_BASE = {
    "version": "1.0.0",
    "url": "https://test.com",
    "description": "Test app",
}


def create_token(account_data: dict) -> str:
    """Create a valid JWT token for testing."""
    to_encode = {
        "sub": str(account_data["id"]),
        "email": account_data["email"],
        "type": account_data["account_type"],
        "is_master": account_data["is_master"],
    }
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def service_data(client, master_admin_account):
    """Crear un service para las pruebas."""
    response = client.post(
        "/api/v1/services",
        json={
            "name": "Servicio de Prueba",
            "description": "Para tests de tablas intermedias",
            "administrator_id": str(master_admin_account["id"]),
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def application_data(client, master_admin_account):
    """Crear una application para las pruebas."""
    response = client.post(
        "/api/v1/applications",
        json={
            "name": "App de Prueba",
            "administrator_id": str(master_admin_account["id"]),
            **APP_BASE,
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def device_data(client, master_admin_account):
    """Crear un device para las pruebas (requiere auth)."""
    token = create_token(master_admin_account)
    response = client.post(
        "/api/v1/devices",
        json={
            "name": "Sensor de Prueba",
            "brand": "TestBrand",
            "model": "T-100",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


# ── Tests: ManagerService ───────────────────────────────────────────

class TestAssignManager:
    """POST /services/{service_id}/managers/{manager_id}"""

    def test_assign_manager_success(self, client, service_data, manager_account):
        response = client.post(
            f"/api/v1/services/{service_data['id']}/managers/{manager_account['id']}"
        )
        assert response.status_code == 201
        data = response.json()
        assert data["service_id"] == service_data["id"]
        assert data["manager_id"] == str(manager_account["id"])

    def test_assign_manager_service_not_found(self, client, manager_account):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/v1/services/{fake_id}/managers/{manager_account['id']}"
        )
        assert response.status_code == 404

    def test_assign_manager_not_found(self, client, service_data):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/v1/services/{service_data['id']}/managers/{fake_id}"
        )
        assert response.status_code == 404

    def test_assign_manager_duplicate(self, client, service_data, manager_account):
        client.post(
            f"/api/v1/services/{service_data['id']}/managers/{manager_account['id']}"
        )
        response = client.post(
            f"/api/v1/services/{service_data['id']}/managers/{manager_account['id']}"
        )
        assert response.status_code == 409


class TestUnassignManager:
    """DELETE /services/{service_id}/managers/{manager_id}"""

    def test_unassign_manager_success(self, client, service_data, manager_account):
        client.post(
            f"/api/v1/services/{service_data['id']}/managers/{manager_account['id']}"
        )
        response = client.delete(
            f"/api/v1/services/{service_data['id']}/managers/{manager_account['id']}"
        )
        assert response.status_code == 204

    def test_unassign_manager_not_assigned(self, client, service_data, manager_account):
        response = client.delete(
            f"/api/v1/services/{service_data['id']}/managers/{manager_account['id']}"
        )
        assert response.status_code == 404


class TestListManagers:
    """GET /services/{service_id}/managers"""

    def test_list_managers_empty(self, client, service_data):
        response = client.get(f"/api/v1/services/{service_data['id']}/managers")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_managers_with_data(self, client, service_data, manager_account):
        client.post(
            f"/api/v1/services/{service_data['id']}/managers/{manager_account['id']}"
        )
        response = client.get(f"/api/v1/services/{service_data['id']}/managers")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["manager_id"] == str(manager_account["id"])

    def test_list_managers_service_not_found(self, client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/services/{fake_id}/managers")
        assert response.status_code == 404


# ── Tests: ApplicationService ───────────────────────────────────────

class TestAssignApplication:
    """POST /services/{service_id}/applications/{application_id}"""

    def test_assign_application_success(self, client, service_data, application_data):
        response = client.post(
            f"/api/v1/services/{service_data['id']}/applications/{application_data['id']}"
        )
        assert response.status_code == 201
        data = response.json()
        assert data["service_id"] == service_data["id"]
        assert data["application_id"] == application_data["id"]

    def test_assign_application_service_not_found(self, client, application_data):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/v1/services/{fake_id}/applications/{application_data['id']}"
        )
        assert response.status_code == 404

    def test_assign_application_not_found(self, client, service_data):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/v1/services/{service_data['id']}/applications/{fake_id}"
        )
        assert response.status_code == 404

    def test_assign_application_duplicate(self, client, service_data, application_data):
        client.post(
            f"/api/v1/services/{service_data['id']}/applications/{application_data['id']}"
        )
        response = client.post(
            f"/api/v1/services/{service_data['id']}/applications/{application_data['id']}"
        )
        assert response.status_code == 409


class TestUnassignApplication:
    """DELETE /services/{service_id}/applications/{application_id}"""

    def test_unassign_application_success(self, client, service_data, application_data):
        client.post(
            f"/api/v1/services/{service_data['id']}/applications/{application_data['id']}"
        )
        response = client.delete(
            f"/api/v1/services/{service_data['id']}/applications/{application_data['id']}"
        )
        assert response.status_code == 204

    def test_unassign_application_not_assigned(self, client, service_data, application_data):
        response = client.delete(
            f"/api/v1/services/{service_data['id']}/applications/{application_data['id']}"
        )
        assert response.status_code == 404


class TestListApplications:
    """GET /services/{service_id}/applications"""

    def test_list_applications_empty(self, client, service_data):
        response = client.get(f"/api/v1/services/{service_data['id']}/applications")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_applications_with_data(self, client, service_data, application_data):
        client.post(
            f"/api/v1/services/{service_data['id']}/applications/{application_data['id']}"
        )
        response = client.get(f"/api/v1/services/{service_data['id']}/applications")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["application_id"] == application_data["id"]

    def test_list_applications_service_not_found(self, client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/services/{fake_id}/applications")
        assert response.status_code == 404


# ── Tests: DeviceService ────────────────────────────────────────────

class TestAssignDevice:
    """POST /services/{service_id}/devices/{device_id}"""

    def test_assign_device_success(self, client, service_data, device_data):
        response = client.post(
            f"/api/v1/services/{service_data['id']}/devices/{device_data['id']}"
        )
        assert response.status_code == 201
        data = response.json()
        assert data["service_id"] == service_data["id"]
        assert data["device_id"] == device_data["id"]

    def test_assign_device_service_not_found(self, client, device_data):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/v1/services/{fake_id}/devices/{device_data['id']}"
        )
        assert response.status_code == 404

    def test_assign_device_not_found(self, client, service_data):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/v1/services/{service_data['id']}/devices/{fake_id}"
        )
        assert response.status_code == 404

    def test_assign_device_duplicate(self, client, service_data, device_data):
        client.post(
            f"/api/v1/services/{service_data['id']}/devices/{device_data['id']}"
        )
        response = client.post(
            f"/api/v1/services/{service_data['id']}/devices/{device_data['id']}"
        )
        assert response.status_code == 409


class TestUnassignDevice:
    """DELETE /services/{service_id}/devices/{device_id}"""

    def test_unassign_device_success(self, client, service_data, device_data):
        client.post(
            f"/api/v1/services/{service_data['id']}/devices/{device_data['id']}"
        )
        response = client.delete(
            f"/api/v1/services/{service_data['id']}/devices/{device_data['id']}"
        )
        assert response.status_code == 204

    def test_unassign_device_not_assigned(self, client, service_data, device_data):
        response = client.delete(
            f"/api/v1/services/{service_data['id']}/devices/{device_data['id']}"
        )
        assert response.status_code == 404


class TestListDevices:
    """GET /services/{service_id}/devices"""

    def test_list_devices_empty(self, client, service_data):
        response = client.get(f"/api/v1/services/{service_data['id']}/devices")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_devices_with_data(self, client, service_data, device_data):
        client.post(
            f"/api/v1/services/{service_data['id']}/devices/{device_data['id']}"
        )
        response = client.get(f"/api/v1/services/{service_data['id']}/devices")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["device_id"] == device_data["id"]

    def test_list_devices_service_not_found(self, client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/services/{fake_id}/devices")
        assert response.status_code == 404
