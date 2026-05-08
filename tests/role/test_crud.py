"""Tests para la entidad Role — CRUD API, validación de esquemas y asignaciones UserRole."""
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.config import settings
from app.domain.role.schemas import RoleCreate, RoleUpdate


def create_token(account_data: dict) -> str:
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


def create_service_via_api(
    client,
    master_admin_account: dict,
    name: str = "Svc Role Test",
) -> str:
    resp = client.post(
        "/api/v1/services",
        json={
            "name": name,
            "description": "Fixture service for roles",
            "administrator_id": str(master_admin_account["id"]),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.fixture
def service_id(client, master_admin_account):
    return create_service_via_api(client, master_admin_account)


class TestRoleSchemaValidation:
    def test_create_accepts_unicode_letters_only(self):
        payload = RoleCreate(
            name="OperadorÓ",
            service_id="00000000-0000-0000-0000-000000000001",
        )
        assert payload.name == "OperadorÓ"

    def test_create_rejects_digit_in_name(self):
        with pytest.raises(ValueError):
            RoleCreate(name="Bad1", service_id=str(uuid4()))

    def test_create_rejects_space_in_name(self):
        with pytest.raises(ValueError):
            RoleCreate(name="Dos Palabras", service_id=str(uuid4()))

    def test_update_optional_name_must_be_valid(self):
        RoleUpdate(description="ok")
        with pytest.raises(ValueError):
            RoleUpdate(name="_bad")


class TestRoleCreateApi:
    def test_create_role_success_master_admin(
        self,
        client,
        master_admin_account,
        service_id,
    ):
        token = create_token(master_admin_account)
        response = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Moderador",
                "description": "Gestión de contenido",
                "service_id": service_id,
                "is_active": True,
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["name"] == "Moderador"
        assert data["description"] == "Gestión de contenido"
        assert data["service_id"] == service_id
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_role_invalid_name_returns_422(
        self,
        client,
        master_admin_account,
        service_id,
    ):
        token = create_token(master_admin_account)
        response = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Rol-ConGuion",
                "service_id": service_id,
            },
        )
        assert response.status_code == 422

    def test_create_role_extra_fields_forbidden(
        self,
        client,
        master_admin_account,
        service_id,
    ):
        token = create_token(master_admin_account)
        response = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Moderadorextra",
                "service_id": service_id,
                "unexpected": True,
            },
        )
        assert response.status_code == 422


class TestRoleListRetrieveApi:
    def test_list_requires_auth(self, client):
        response = client.get("/api/v1/roles")
        assert response.status_code == 401

    def test_list_roles_user_allowed(
        self,
        client,
        user_account,
        master_admin_account,
        service_id,
    ):
        token_admin = create_token(master_admin_account)
        client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token_admin}"},
            json={"name": "Lector", "service_id": service_id},
        )

        token = create_token(user_account)
        response = client.get(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["total"] >= 1


class TestRoleAuthorizationApi:
    def test_user_cannot_create_role(self, client, user_account, service_id):
        token = create_token(user_account)
        response = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Forbidden",
                "service_id": service_id,
            },
        )
        assert response.status_code == 403

    def test_manager_can_create_role(
        self,
        client,
        manager_account,
        master_admin_account,
        service_id,
    ):
        token = create_token(manager_account)
        response = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Encargado",
                "service_id": service_id,
            },
        )
        assert response.status_code == 201, response.text

    def test_manager_delete_forbidden(
        self,
        client,
        manager_account,
        master_admin_account,
        service_id,
    ):
        admin_tok = create_token(master_admin_account)
        create_resp = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_tok}"},
            json={"name": "ParaBorrar", "service_id": service_id},
        )
        assert create_resp.status_code == 201
        role_id = create_resp.json()["id"]

        mgr_tok = create_token(manager_account)
        response = client.delete(
            f"/api/v1/roles/{role_id}",
            headers={"Authorization": f"Bearer {mgr_tok}"},
        )
        assert response.status_code == 403

    def test_regular_admin_can_delete_role(
        self,
        client,
        regular_admin_account,
        master_admin_account,
        service_id,
    ):
        admin_master_tok = create_token(master_admin_account)
        create_resp = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {admin_master_tok}"},
            json={"name": "BorradoAdminRegular", "service_id": service_id},
        )
        role_id = create_resp.json()["id"]

        reg_tok = create_token(regular_admin_account)
        response = client.delete(
            f"/api/v1/roles/{role_id}",
            headers={"Authorization": f"Bearer {reg_tok}"},
        )
        assert response.status_code == 204


class TestRoleUpdateDeleteApi:
    def test_patch_role_regular_admin(
        self,
        client,
        master_admin_account,
        regular_admin_account,
        service_id,
    ):
        master_tok = create_token(master_admin_account)
        create_resp = client.post(
            "/api/v1/roles",
            headers={"Authorization": f"Bearer {master_tok}"},
            json={
                "name": "NombreInicial",
                "description": "d",
                "service_id": service_id,
            },
        )
        role_id = create_resp.json()["id"]

        reg_tok = create_token(regular_admin_account)
        response = client.patch(
            f"/api/v1/roles/{role_id}",
            headers={"Authorization": f"Bearer {reg_tok}"},
            json={"description": None, "is_active": False},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["is_active"] is False

    def test_get_role_not_found(self, client, master_admin_account):
        token = create_token(master_admin_account)
        response = client.get(
            f"/api/v1/roles/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Helpers para UserRole
# ─────────────────────────────────────────────────────────────────────────────

def create_role_via_api(client, account: dict, service_id: str, name: str) -> str:
    token = create_token(account)
    resp = client.post(
        "/api/v1/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "service_id": service_id},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestUserRoleAssignApi:
    """POST /roles/{role_id}/users — asignar usuario a rol."""

    def test_manager_can_assign_user_to_role(
        self, client, manager_account, master_admin_account, user_account, service_id
    ):
        role_id = create_role_via_api(client, master_admin_account, service_id, "Operador")
        token = create_token(manager_account)

        response = client.post(
            f"/api/v1/roles/{role_id}/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(user_account["id"])},
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["user_id"] == str(user_account["id"])
        assert data["role_id"] == role_id
        assert "id" in data
        assert "created_at" in data

    def test_admin_can_assign_user_to_role(
        self, client, regular_admin_account, master_admin_account, user_account, service_id
    ):
        role_id = create_role_via_api(client, master_admin_account, service_id, "Supervisor")
        token = create_token(regular_admin_account)

        response = client.post(
            f"/api/v1/roles/{role_id}/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(user_account["id"])},
        )
        assert response.status_code == 201, response.text

    def test_user_cannot_assign_role(
        self, client, user_account, master_admin_account, service_id
    ):
        role_id = create_role_via_api(client, master_admin_account, service_id, "Visitante")
        token = create_token(user_account)

        response = client.post(
            f"/api/v1/roles/{role_id}/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(user_account["id"])},
        )
        assert response.status_code == 403

    def test_duplicate_assignment_returns_409(
        self, client, manager_account, master_admin_account, user_account, service_id
    ):
        role_id = create_role_via_api(client, master_admin_account, service_id, "Auditor")
        token = create_token(manager_account)
        payload = {"user_id": str(user_account["id"])}

        client.post(
            f"/api/v1/roles/{role_id}/users",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        response = client.post(
            f"/api/v1/roles/{role_id}/users",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert response.status_code == 409

    def test_assign_nonexistent_user_returns_404(
        self, client, manager_account, master_admin_account, service_id
    ):
        role_id = create_role_via_api(client, master_admin_account, service_id, "Inspector")
        token = create_token(manager_account)

        response = client.post(
            f"/api/v1/roles/{role_id}/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(uuid4())},
        )
        assert response.status_code == 404

    def test_assign_to_nonexistent_role_returns_404(
        self, client, manager_account, user_account
    ):
        token = create_token(manager_account)

        response = client.post(
            f"/api/v1/roles/{uuid4()}/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(user_account["id"])},
        )
        assert response.status_code == 404


class TestUserRoleListApi:
    """GET /roles/{role_id}/users — listar asignaciones."""

    def test_user_can_list_assigned_users(
        self, client, manager_account, master_admin_account, user_account, service_id
    ):
        role_id = create_role_via_api(client, master_admin_account, service_id, "Revisor")
        mgr_tok = create_token(manager_account)
        client.post(
            f"/api/v1/roles/{role_id}/users",
            headers={"Authorization": f"Bearer {mgr_tok}"},
            json={"user_id": str(user_account["id"])},
        )

        user_tok = create_token(user_account)
        response = client.get(
            f"/api/v1/roles/{role_id}/users",
            headers={"Authorization": f"Bearer {user_tok}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(item["user_id"] == str(user_account["id"]) for item in data)

    def test_list_users_role_not_found(self, client, master_admin_account):
        token = create_token(master_admin_account)
        response = client.get(
            f"/api/v1/roles/{uuid4()}/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404

    def test_list_requires_auth(self, client, master_admin_account, service_id):
        role_id = create_role_via_api(client, master_admin_account, service_id, "Tecnico")
        response = client.get(f"/api/v1/roles/{role_id}/users")
        assert response.status_code == 401


class TestUserRoleRemoveApi:
    """DELETE /roles/{role_id}/users/{user_id} — quitar usuario de rol."""

    def test_manager_can_remove_user_from_role(
        self, client, manager_account, master_admin_account, user_account, service_id
    ):
        role_id = create_role_via_api(client, master_admin_account, service_id, "Coordinador")
        token = create_token(manager_account)

        client.post(
            f"/api/v1/roles/{role_id}/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": str(user_account["id"])},
        )

        response = client.delete(
            f"/api/v1/roles/{role_id}/users/{user_account['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

    def test_user_cannot_remove_assignment(
        self, client, manager_account, master_admin_account, user_account, service_id
    ):
        role_id = create_role_via_api(client, master_admin_account, service_id, "Delegado")
        mgr_tok = create_token(manager_account)
        client.post(
            f"/api/v1/roles/{role_id}/users",
            headers={"Authorization": f"Bearer {mgr_tok}"},
            json={"user_id": str(user_account["id"])},
        )

        user_tok = create_token(user_account)
        response = client.delete(
            f"/api/v1/roles/{role_id}/users/{user_account['id']}",
            headers={"Authorization": f"Bearer {user_tok}"},
        )
        assert response.status_code == 403

    def test_remove_nonexistent_assignment_returns_404(
        self, client, manager_account, master_admin_account, user_account, service_id
    ):
        role_id = create_role_via_api(client, master_admin_account, service_id, "Gestor")
        token = create_token(manager_account)

        response = client.delete(
            f"/api/v1/roles/{role_id}/users/{user_account['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
