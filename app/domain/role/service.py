from abc import ABC
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.database import SessionDep
from app.database.model import Role, User, UserRole
from app.domain.role.repository import RoleRepository
from app.domain.role.schemas import RoleCreate, RoleUpdate, UserRoleResponse
from app.shared.base_domain.service import BaseService, IBaseService
from app.shared.exceptions import AlreadyExistsException, NotFoundException


class IRoleService(IBaseService[Role, RoleCreate, RoleUpdate], ABC):
    pass


class RoleService(BaseService[Role, RoleCreate, RoleUpdate], IRoleService):
    entity_name = "Role"
    repository_class = RoleRepository

    def assign_user(self, role_id: UUID, user_id: UUID) -> UserRole:
        repo: RoleRepository = self.repository

        # Verificar que el Role existe
        role = repo.get_by_id(role_id)
        if not role:
            raise NotFoundException("Role", role_id)

        # Verificar que el User existe
        user = repo.session.get(User, user_id)
        if not user:
            raise NotFoundException("User", user_id)

        # Verificar que la asignación no existe ya → 409
        existing = repo.get_user_role(role_id, user_id)
        if existing:
            raise AlreadyExistsException("UserRole", "user_id + role_id", f"{user_id} + {role_id}")

        return repo.create_user_role(UserRole(role_id=role_id, user_id=user_id))

    def remove_user(self, role_id: UUID, user_id: UUID) -> None:
        repo: RoleRepository = self.repository

        user_role = repo.get_user_role(role_id, user_id)
        if not user_role:
            raise NotFoundException("UserRole", f"{user_id} in role {role_id}")

        repo.delete_user_role(user_role)

    def get_users_by_role(self, role_id: UUID) -> list[UserRole]:
        # Verificar que el Role existe
        role = self.repository.get_by_id(role_id)
        if not role:
            raise NotFoundException("Role", role_id)

        repo: RoleRepository = self.repository
        return repo.get_users_by_role(role_id)


def get_role_service(session: SessionDep) -> RoleService:
    return RoleService(session)


RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
