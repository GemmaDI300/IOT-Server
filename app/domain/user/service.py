from abc import ABC
from typing import Annotated, override
from uuid import UUID
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
from app.shared.authorization.dependencies import get_current_user_from_context
from app.shared.exceptions import NotFoundException
from app.shared.pagination import PageResponse


class IUserService(IBaseService[User, PersonalDataCreate, PersonalDataUpdate], ABC):
    pass


class UserService(PersonalDataService[User], IUserService):
    entity_name = "User"
    repository_class = UserRepository

    @override
    def get_all(self, offset: int = 0, limit: int = 20) -> PageResponse[User]:
        current_user = get_current_user_from_context()
        if current_user is None:
            return super().get_all(offset, limit)

        if current_user.account_type == "administrator":
            items, total = self.repository.get_all(offset, limit)
        elif current_user.account_type == "manager":
            items, total = self.repository.get_for_manager(current_user.account_id, offset, limit)
        elif current_user.account_type == "user":
            entity = self.repository.get_by_id(current_user.account_id)
            items = [entity] if entity else []
            total = 1 if entity else 0
        else:
            return PageResponse(total=0, offset=offset, limit=limit, data=[])

        return PageResponse(total=total, offset=offset, limit=limit, data=items)

    @override
    def get_by_id(self, id: UUID) -> User:
        entity = self.repository.get_by_id(id)
        if not entity:
            raise NotFoundException(self.entity_name, id)

        current_user = get_current_user_from_context()
        if current_user is None:
            return entity

        if current_user.account_type == "administrator":
            return entity

        if current_user.account_type == "manager":
            if not self.repository.check_manager_access(id, current_user.account_id):
                raise NotFoundException(self.entity_name, id)
            return entity

        if current_user.account_type == "user":
            if entity.id != current_user.account_id:
                raise NotFoundException(self.entity_name, id)
            return entity

        raise NotFoundException(self.entity_name, id)


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
