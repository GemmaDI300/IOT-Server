from abc import ABC
from typing import Annotated

from fastapi import Depends

from app.database import SessionDep
from app.database.model import Role
from app.domain.role.repository import RoleRepository
from app.domain.role.schemas import RoleCreate, RoleUpdate
from app.shared.base_domain.service import BaseService, IBaseService


class IRoleService(IBaseService[Role, RoleCreate, RoleUpdate], ABC):
    pass


class RoleService(BaseService[Role, RoleCreate, RoleUpdate], IRoleService):
    entity_name = "Role"
    repository_class = RoleRepository


def get_role_service(session: SessionDep) -> RoleService:
    return RoleService(session)


RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]