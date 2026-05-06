from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.database.model import Role, Service, UserRole


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


def create_service_and_role(db, administrator_id):
    with Session(db) as session:
        service = Service(
            name="User Role Service",
            description="Service for user-role tests",
            administrator_id=administrator_id,
            is_active=True,
        )
        session.add(service)
        session.flush()

        role = Role(
            name="Operator",
            description="Operator role",
            service_id=service.id,
            is_active=True,
        )
        session.add(role)
        session.commit()
        session.refresh(service)
        session.refresh(role)
        return service.id, role.id


class TestUserRoleEndpoints:
    def test_assign_role_to_user_as_master_admin(
        self,
        client: TestClient,
        db,
        master_admin_account: dict,
        user_account: dict,
    ):
        _, role_id = create_service_and_role(db, master_admin_account["id"])
        token = create_token(master_admin_account)

        response = client.post(
            f"/api/v1/users/{user_account['id']}/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(user_account["id"])
        assert data["role_id"] == str(role_id)

    def test_assign_role_to_user_rejects_duplicate_assignment(
        self,
        client: TestClient,
        db,
        master_admin_account: dict,
        user_account: dict,
    ):
        _, role_id = create_service_and_role(db, master_admin_account["id"])
        token = create_token(master_admin_account)

        first_response = client.post(
            f"/api/v1/users/{user_account['id']}/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert first_response.status_code == 201

        second_response = client.post(
            f"/api/v1/users/{user_account['id']}/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert second_response.status_code == 409
        assert "already assigned" in second_response.json()["detail"].lower()

    def test_list_roles_by_user_returns_assigned_roles(
        self,
        client: TestClient,
        db,
        master_admin_account: dict,
        user_account: dict,
    ):
        _, role_id = create_service_and_role(db, master_admin_account["id"])

        with Session(db) as session:
            session.add(UserRole(user_id=user_account["id"], role_id=role_id))
            session.commit()

        token = create_token(master_admin_account)
        response = client.get(
            f"/api/v1/users/{user_account['id']}/roles",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(role_id)
        assert data[0]["name"] == "Operator"

    def test_remove_role_from_user_deletes_assignment(
        self,
        client: TestClient,
        db,
        master_admin_account: dict,
        user_account: dict,
    ):
        _, role_id = create_service_and_role(db, master_admin_account["id"])

        with Session(db) as session:
            session.add(UserRole(user_id=user_account["id"], role_id=role_id))
            session.commit()

        token = create_token(master_admin_account)
        delete_response = client.delete(
            f"/api/v1/users/{user_account['id']}/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert delete_response.status_code == 204

        list_response = client.get(
            f"/api/v1/users/{user_account['id']}/roles",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        assert list_response.json() == []

    def test_assign_role_to_user_as_regular_admin_allowed(
        self,
        client: TestClient,
        db,
        master_admin_account: dict,
        regular_admin_account: dict,
        user_account: dict,
    ):
        _, role_id = create_service_and_role(db, master_admin_account["id"])
        token = create_token(regular_admin_account)

        response = client.post(
            f"/api/v1/users/{user_account['id']}/roles/{role_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201