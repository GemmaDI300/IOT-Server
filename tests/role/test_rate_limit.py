"""Tests de rate limiting para los endpoints de /roles.

Límite configurado: 3 peticiones por segundo por IP.
"""
import time
import jwt
import pytest
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.shared.rate_limit import _windows


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def create_token(account_data: dict) -> str:
    to_encode = {
        "sub": str(account_data["id"]),
        "email": account_data["email"],
        "type": account_data["account_type"],
        "is_master": account_data["is_master"],
    }
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    """Limpia el estado global del rate limiter antes y después de cada test."""
    _windows.clear()
    yield
    _windows.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRoleRateLimit:

    def test_first_three_requests_are_allowed(self, client, master_admin_account):
        """Las 3 primeras peticiones deben pasar."""
        token = create_token(master_admin_account)
        for _ in range(3):
            resp = client.get(
                "/api/v1/roles",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    def test_fourth_request_returns_429(self, client, master_admin_account):
        """La 4ª petición en el mismo segundo debe devolver 429."""
        token = create_token(master_admin_account)
        for _ in range(3):
            client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})

        resp = client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 429

    def test_429_has_retry_after_header(self, client, master_admin_account):
        """La respuesta 429 debe incluir Retry-After: 1."""
        token = create_token(master_admin_account)
        for _ in range(3):
            client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})

        resp = client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert resp.headers["Retry-After"] == "1"

    def test_rate_limit_resets_after_window_expires(self, client, master_admin_account):
        """Después de 1 segundo la cuota se reinicia."""
        token = create_token(master_admin_account)
        for _ in range(3):
            client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})

        assert client.get(
            "/api/v1/roles", headers={"Authorization": f"Bearer {token}"}
        ).status_code == 429

        time.sleep(1.1)

        resp = client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_rate_limit_applies_across_different_role_routes(
        self, client, master_admin_account
    ):
        """El límite es compartido entre todas las rutas de /roles."""
        token = create_token(master_admin_account)

        # Crear un servicio primero para poder crear un role
        svc_resp = client.post(
            "/api/v1/services",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "RateLimitSvc",
                "description": "Fixture",
                "administrator_id": str(master_admin_account["id"]),
            },
        )
        assert svc_resp.status_code == 201
        service_id = svc_resp.json()["id"]

        role_resp = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "RateLimitRole", "service_id": service_id},
        )
        assert role_resp.status_code == 201
        role_id = role_resp.json()["id"]

        # Reiniciamos el contador para aislar el escenario
        _windows.clear()

        client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})
        client.get(f"/api/v1/roles/{role_id}", headers={"Authorization": f"Bearer {token}"})
        client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})

        # La 4ª petición a cualquier ruta de /roles debe ser rechazada
        resp = client.get(f"/api/v1/roles/{role_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 429

    def test_role_limit_does_not_affect_managers_endpoint(self, client, master_admin_account):
        """Agotar el límite de /roles no debe bloquear /managers."""
        token = create_token(master_admin_account)
        for _ in range(3):
            client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})

        assert client.get(
            "/api/v1/roles", headers={"Authorization": f"Bearer {token}"}
        ).status_code == 429

        # /managers tiene su propio contador
        resp = client.get("/api/v1/managers", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_unauthenticated_requests_consume_quota(self, client):
        """Las peticiones sin token también consumen cuota."""
        for _ in range(3):
            resp = client.get("/api/v1/roles")
            assert resp.status_code == 401

        resp = client.get("/api/v1/roles")
        assert resp.status_code == 429
