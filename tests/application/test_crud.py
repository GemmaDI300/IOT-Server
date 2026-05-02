"""Tests para la entidad Application — CRUD completo con autorización OSO."""
import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt
from app.config import settings

APP_BASE = {
    "version": "1.0.0",
    "url": "https://test.com",
    "description": "Test application",
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
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


@pytest.fixture
def auth_headers(master_admin_account):
    token = create_token(master_admin_account)
    return {"Authorization": f"Bearer {token}"}


class TestCreateApplication:
    """POST /api/v1/applications"""

    def test_create_application_success(self, client, master_admin_account, auth_headers):
        response = client.post(
            "/api/v1/applications",
            json={
                "name": "App de Monitoreo",
                "administrator_id": str(master_admin_account["id"]),
                **APP_BASE,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "App de Monitoreo"
        assert data["version"] == "1.0.0"
        assert data["url"] == "https://test.com"
        assert data["description"] == "Test application"
        assert data["administrator_id"] == str(master_admin_account["id"])
        assert data["is_active"] is True
        assert "id" in data
        assert "api_key" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_application_generates_api_key(self, client, master_admin_account, auth_headers):
        response = client.post(
            "/api/v1/applications",
            json={
                "name": "App con API Key",
                "administrator_id": str(master_admin_account["id"]),
                **APP_BASE,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert len(data["api_key"]) == 64

    def test_create_application_without_name_fails(self, client, master_admin_account, auth_headers):
        response = client.post(
            "/api/v1/applications",
            json={
                "administrator_id": str(master_admin_account["id"]),
                **APP_BASE,
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_create_application_without_administrator_fails(self, client, auth_headers):
        response = client.post(
            "/api/v1/applications",
            json={"name": "Sin admin", **APP_BASE},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_create_application_duplicate_name_fails(self, client, master_admin_account, auth_headers):
        admin_id = str(master_admin_account["id"])
        client.post(
            "/api/v1/applications",
            json={"name": "Duplicada", "administrator_id": admin_id, **APP_BASE},
            headers=auth_headers,
        )
        response = client.post(
            "/api/v1/applications",
            json={"name": "Duplicada", "administrator_id": admin_id, **APP_BASE},
            headers=auth_headers,
        )
        assert response.status_code == 500

    def test_create_application_without_token_fails(self, client, master_admin_account):
        response = client.post(
            "/api/v1/applications",
            json={
                "name": "Sin token",
                "administrator_id": str(master_admin_account["id"]),
                **APP_BASE,
            },
        )
        assert response.status_code == 401


class TestListApplications:
    """GET /api/v1/applications"""

    def test_list_applications_empty(self, client, auth_headers):
        response = client.get("/api/v1/applications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["data"] == []

    def test_list_applications_with_data(self, client, master_admin_account, auth_headers):
        admin_id = str(master_admin_account["id"])
        client.post(
            "/api/v1/applications",
            json={"name": "App 1", "administrator_id": admin_id, **APP_BASE},
            headers=auth_headers,
        )
        client.post(
            "/api/v1/applications",
            json={"name": "App 2", "administrator_id": admin_id, **APP_BASE},
            headers=auth_headers,
        )
        response = client.get("/api/v1/applications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["data"]) == 2

    def test_list_applications_pagination(self, client, master_admin_account, auth_headers):
        admin_id = str(master_admin_account["id"])
        for i in range(5):
            client.post(
                "/api/v1/applications",
                json={"name": f"App {i}", "administrator_id": admin_id, **APP_BASE},
                headers=auth_headers,
            )
        response = client.get("/api/v1/applications?offset=0&limit=2", headers=auth_headers)
        data = response.json()
        assert data["total"] == 5
        assert len(data["data"]) == 2


class TestGetApplication:
    """GET /api/v1/applications/{id}"""

    def test_get_application_by_id(self, client, master_admin_account, auth_headers):
        create_response = client.post(
            "/api/v1/applications",
            json={
                "name": "Mi App",
                "administrator_id": str(master_admin_account["id"]),
                **APP_BASE,
            },
            headers=auth_headers,
        )
        app_id = create_response.json()["id"]
        response = client.get(f"/api/v1/applications/{app_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Mi App"

    def test_get_application_not_found(self, client, auth_headers):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/applications/{fake_id}", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateApplication:
    """PATCH /api/v1/applications/{id}"""

    def test_update_application_name(self, client, master_admin_account, auth_headers):
        create_response = client.post(
            "/api/v1/applications",
            json={
                "name": "Nombre Original",
                "administrator_id": str(master_admin_account["id"]),
                **APP_BASE,
            },
            headers=auth_headers,
        )
        app_id = create_response.json()["id"]
        response = client.patch(
            f"/api/v1/applications/{app_id}",
            json={"name": "Nombre Actualizado"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Nombre Actualizado"

    def test_update_application_description(self, client, master_admin_account, auth_headers):
        create_response = client.post(
            "/api/v1/applications",
            json={
                "name": "App Desc",
                "administrator_id": str(master_admin_account["id"]),
                **APP_BASE,
            },
            headers=auth_headers,
        )
        app_id = create_response.json()["id"]
        response = client.patch(
            f"/api/v1/applications/{app_id}",
            json={"description": "Nueva descripcion"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Nueva descripcion"

    def test_update_application_deactivate(self, client, master_admin_account, auth_headers):
        create_response = client.post(
            "/api/v1/applications",
            json={
                "name": "App Activa",
                "administrator_id": str(master_admin_account["id"]),
                **APP_BASE,
            },
            headers=auth_headers,
        )
        app_id = create_response.json()["id"]
        response = client.patch(
            f"/api/v1/applications/{app_id}",
            json={"is_active": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_update_application_not_found(self, client, auth_headers):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.patch(
            f"/api/v1/applications/{fake_id}",
            json={"name": "No existe"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeleteApplication:
    """DELETE /api/v1/applications/{id}"""

    def test_delete_application(self, client, master_admin_account, auth_headers):
        create_response = client.post(
            "/api/v1/applications",
            json={
                "name": "Para borrar",
                "administrator_id": str(master_admin_account["id"]),
                **APP_BASE,
            },
            headers=auth_headers,
        )
        app_id = create_response.json()["id"]
        response = client.delete(f"/api/v1/applications/{app_id}", headers=auth_headers)
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/applications/{app_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_application_not_found(self, client, auth_headers):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(f"/api/v1/applications/{fake_id}", headers=auth_headers)
        assert response.status_code == 404
