from abc import ABC
from typing import Annotated

from fastapi import Depends

from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import select

from app.shared.base_domain.service import IBaseService
from app.database.model import Role, User, UserRole
from app.database import SessionDep
from app.domain.user.repository import UserRepository
from app.domain.personal_data.schemas import PersonalDataCreate, PersonalDataUpdate
from app.domain.personal_data.service import PersonalDataService


class IUserService(IBaseService[User, PersonalDataCreate, PersonalDataUpdate], ABC):
    pass


class UserService(PersonalDataService[User], IUserService):
    entity_name = "User"
    repository_class = UserRepository

    def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> UserRole:
        session = self.repository.session

        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        role = session.get(Role, role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )

        existing = session.exec(
            select(UserRole)
            .where(UserRole.user_id == user_id)
            .where(UserRole.role_id == role_id)
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role already assigned to user",
            )

        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
        )

        session.add(user_role)
        session.commit()
        session.refresh(user_role)

        return user_role

    def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> None:
        session = self.repository.session

        user_role = session.exec(
            select(UserRole)
            .where(UserRole.user_id == user_id)
            .where(UserRole.role_id == role_id)
        ).first()

        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role assignment not found",
            )

        session.delete(user_role)
        session.commit()

    def list_roles_by_user(self, user_id: UUID) -> list[Role]:
        session = self.repository.session

        user = session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        roles = session.exec(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        ).all()

        return list(roles)


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
