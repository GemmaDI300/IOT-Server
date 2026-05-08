"""Tests de rate limiting para los endpoints de /managers.

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

class TestManagerRateLimit:

    def test_first_three_requests_are_allowed(self, client, master_admin_account):
        """Las 3 primeras peticiones dentro de 1 segundo deben pasar."""
        token = create_token(master_admin_account)
        for _ in range(3):
            resp = client.get(
                "/api/v1/managers",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    def test_fourth_request_in_same_second_returns_429(self, client, master_admin_account):
        """La 4ª petición en el mismo segundo debe devolver 429."""
        token = create_token(master_admin_account)
        for _ in range(3):
            client.get(
                "/api/v1/managers",
                headers={"Authorization": f"Bearer {token}"},
            )

        resp = client.get(
            "/api/v1/managers",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 429

    def test_429_response_has_retry_after_header(self, client, master_admin_account):
        """La respuesta 429 debe incluir el header Retry-After: 1."""
        token = create_token(master_admin_account)
        for _ in range(3):
            client.get("/api/v1/managers", headers={"Authorization": f"Bearer {token}"})

        resp = client.get("/api/v1/managers", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert resp.headers["Retry-After"] == "1"

    def test_rate_limit_resets_after_window_expires(self, client, master_admin_account):
        """Después de esperar 1 segundo, el límite debe reiniciarse."""
        token = create_token(master_admin_account)
        for _ in range(3):
            client.get("/api/v1/managers", headers={"Authorization": f"Bearer {token}"})

        # Confirmamos que está bloqueado
        assert client.get(
            "/api/v1/managers", headers={"Authorization": f"Bearer {token}"}
        ).status_code == 429

        # Esperamos que la ventana expire
        time.sleep(1.1)

        resp = client.get("/api/v1/managers", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_rate_limit_applies_across_different_manager_routes(
        self, client, master_admin_account, manager_account
    ):
        """El límite es compartido entre todas las rutas de /managers."""
        token = create_token(master_admin_account)

        # Peticiones a rutas distintas del mismo dominio
        client.get("/api/v1/managers", headers={"Authorization": f"Bearer {token}"})
        client.get(
            f"/api/v1/managers/{manager_account['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        client.get("/api/v1/managers", headers={"Authorization": f"Bearer {token}"})

        # La 4ª petición (a cualquier ruta de /managers) debe ser rechazada
        resp = client.get(
            f"/api/v1/managers/{manager_account['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 429

    def test_manager_limit_does_not_affect_roles_endpoint(
        self, client, master_admin_account
    ):
        """Agotar el límite de /managers no debe afectar a /roles."""
        token = create_token(master_admin_account)

        # Agotamos el límite de managers
        for _ in range(3):
            client.get("/api/v1/managers", headers={"Authorization": f"Bearer {token}"})
        assert client.get(
            "/api/v1/managers", headers={"Authorization": f"Bearer {token}"}
        ).status_code == 429

        # /roles tiene su propio contador — debe seguir respondiendo
        resp = client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_unauthenticated_requests_also_rate_limited(self, client):
        """Las peticiones sin token también consumen la cuota (devuelven 401 hasta el límite)."""
        for _ in range(3):
            resp = client.get("/api/v1/managers")
            assert resp.status_code == 401  # sin token → 401, pero la cuota se consume

        # La 4ª petición debe ser 429 (el rate limiter se ejecuta antes del auth check)
        resp = client.get("/api/v1/managers")
        assert resp.status_code == 429
