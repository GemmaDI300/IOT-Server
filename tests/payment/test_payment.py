"""Tests para la entidad Payment — CRUD, SubscriptionType, UserService, PaymentHistory."""
import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt
from app.config import settings


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


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def subscription_type_data(client, auth_headers):
    """Crear un tipo de suscripción mensual."""
    response = client.post(
        "/api/v1/payments/subscription-types",
        json={"type": "mensual", "cost": 100.0},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def service_data(client, master_admin_account, auth_headers):
    """Crear un service."""
    response = client.post(
        "/api/v1/services",
        json={
            "name": "Monitoreo",
            "description": "Servicio de monitoreo",
            "administrator_id": str(master_admin_account["id"]),
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def user_service_data(client, auth_headers, user_account, service_data):
    """Asignar usuario a servicio."""
    response = client.post(
        f"/api/v1/payments/user-services/{user_account['id']}/{service_data['id']}",
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


# ── Tests: SubscriptionType ─────────────────────────────────────────

class TestCreateSubscriptionType:

    def test_create_success(self, client, auth_headers):
        response = client.post(
            "/api/v1/payments/subscription-types",
            json={"type": "mensual", "cost": 100.0},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "mensual"
        assert data["cost"] == 100.0

    def test_create_duplicate_fails(self, client, auth_headers, subscription_type_data):
        response = client.post(
            "/api/v1/payments/subscription-types",
            json={"type": "mensual", "cost": 200.0},
            headers=auth_headers,
        )
        assert response.status_code == 409


class TestListSubscriptionTypes:

    def test_list_empty(self, client, auth_headers):
        response = client.get(
            "/api/v1/payments/subscription-types",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_with_data(self, client, auth_headers, subscription_type_data):
        response = client.get(
            "/api/v1/payments/subscription-types",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestUpdateSubscriptionType:

    def test_update_cost(self, client, auth_headers, subscription_type_data):
        response = client.patch(
            f"/api/v1/payments/subscription-types/{subscription_type_data['id']}",
            json={"cost": 150.0},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["cost"] == 150.0

    def test_update_not_found(self, client, auth_headers):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.patch(
            f"/api/v1/payments/subscription-types/{fake_id}",
            json={"cost": 150.0},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeleteSubscriptionType:

    def test_delete_success(self, client, auth_headers, subscription_type_data):
        response = client.delete(
            f"/api/v1/payments/subscription-types/{subscription_type_data['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_delete_not_found(self, client, auth_headers):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(
            f"/api/v1/payments/subscription-types/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


# ── Tests: UserService ──────────────────────────────────────────────

class TestAssignUserService:

    def test_assign_success(self, client, auth_headers, user_account, service_data):
        response = client.post(
            f"/api/v1/payments/user-services/{user_account['id']}/{service_data['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(user_account["id"])
        assert data["service_id"] == service_data["id"]
        assert data["is_active"] is False

    def test_assign_duplicate_fails(self, client, auth_headers, user_service_data, user_account, service_data):
        response = client.post(
            f"/api/v1/payments/user-services/{user_account['id']}/{service_data['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 409

    def test_assign_user_not_found(self, client, auth_headers, service_data):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/v1/payments/user-services/{fake_id}/{service_data['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_assign_service_not_found(self, client, auth_headers, user_account):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/v1/payments/user-services/{user_account['id']}/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUnassignUserService:

    def test_unassign_success(self, client, auth_headers, user_service_data, user_account, service_data):
        response = client.delete(
            f"/api/v1/payments/user-services/{user_account['id']}/{service_data['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_unassign_not_assigned(self, client, auth_headers, user_account, service_data):
        response = client.delete(
            f"/api/v1/payments/user-services/{user_account['id']}/{service_data['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListUserServices:

    def test_list_by_user(self, client, auth_headers, user_service_data, user_account):
        response = client.get(
            f"/api/v1/payments/user-services/user/{user_account['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_by_service(self, client, auth_headers, user_service_data, service_data):
        response = client.get(
            f"/api/v1/payments/user-services/service/{service_data['id']}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


# ── Tests: Payment ──────────────────────────────────────────────────

class TestCreatePayment:

    def test_create_payment_activates_user_service(self, client, auth_headers, user_service_data, subscription_type_data):
        response = client.post(
            "/api/v1/payments",
            json={
                "user_service_id": user_service_data["id"],
                "subscription_type_id": subscription_type_data["id"],
                "deposit_id": "BBVA-2026-001",
                "amount": 100.0,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_service_id"] == user_service_data["id"]
        assert data["subscription_type_id"] == subscription_type_data["id"]
        assert "expires_at" in data

    def test_create_payment_auto_creates_history(self, client, auth_headers, user_service_data, subscription_type_data):
        """Al crear pago, se genera automáticamente el historial."""
        payment_response = client.post(
            "/api/v1/payments",
            json={
                "user_service_id": user_service_data["id"],
                "subscription_type_id": subscription_type_data["id"],
                "deposit_id": "BBVA-2026-002",
                "amount": 100.0,
            },
            headers=auth_headers,
        )
        payment = payment_response.json()

        history_response = client.get(
            f"/api/v1/payments/{payment['id']}/history",
            headers=auth_headers,
        )
        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history) == 1
        assert history[0]["deposit_id"] == "BBVA-2026-002"
        assert history[0]["amount"] == 100.0

    def test_create_payment_user_service_not_found(self, client, auth_headers, subscription_type_data):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            "/api/v1/payments",
            json={
                "user_service_id": fake_id,
                "subscription_type_id": subscription_type_data["id"],
                "deposit_id": "BBVA-2026-003",
                "amount": 100.0,
            },
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_create_payment_subscription_type_not_found(self, client, auth_headers, user_service_data):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            "/api/v1/payments",
            json={
                "user_service_id": user_service_data["id"],
                "subscription_type_id": fake_id,
                "deposit_id": "BBVA-2026-004",
                "amount": 100.0,
            },
            headers=auth_headers,
        )
        assert response.status_code == 404


# ── Tests: PaymentHistory ───────────────────────────────────────────

class TestPaymentHistory:

    def test_list_history(self, client, auth_headers, user_service_data, subscription_type_data):
        payment_response = client.post(
            "/api/v1/payments",
            json={
                "user_service_id": user_service_data["id"],
                "subscription_type_id": subscription_type_data["id"],
                "deposit_id": "BBVA-2026-005",
                "amount": 100.0,
            },
            headers=auth_headers,
        )
        payment = payment_response.json()

        response = client.get(
            f"/api/v1/payments/{payment['id']}/history",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["deposit_id"] == "BBVA-2026-005"

    def test_list_history_payment_not_found(self, client, auth_headers):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/v1/payments/{fake_id}/history",
            headers=auth_headers,
        )
        assert response.status_code == 404
