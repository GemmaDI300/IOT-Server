from abc import ABC
from typing import Annotated, override
from uuid import UUID
from fastapi import Depends
from app.shared.base_domain.service import IBaseService, BaseService
from app.database.model import Service
from app.database import SessionDep
from app.domain.service.repository import ServiceRepository
from app.domain.service.schemas import ServiceCreate, ServiceUpdate
from app.shared.authorization.dependencies import get_current_user_from_context
from app.shared.exceptions import NotFoundException
from app.shared.pagination import PageResponse


class IServiceService(IBaseService[Service, ServiceCreate, ServiceUpdate], ABC):
    pass


class ServiceService(BaseService[Service, ServiceCreate, ServiceUpdate], IServiceService):
    entity_name = "Service"
    repository_class = ServiceRepository

    @override
    def get_all(self, offset: int = 0, limit: int = 20) -> PageResponse[Service]:
        current_user = get_current_user_from_context()
        if current_user is None:
            return super().get_all(offset, limit)

        if current_user.account_type == "administrator":
            items, total = self.repository.get_all(offset, limit)
        elif current_user.account_type == "manager":
            items, total = self.repository.get_for_manager(current_user.account_id, offset, limit)
        elif current_user.account_type == "user":
            return PageResponse(total=0, offset=offset, limit=limit, data=[])
        else:
            return PageResponse(total=0, offset=offset, limit=limit, data=[])

        return PageResponse(total=total, offset=offset, limit=limit, data=items)

    @override
    def get_by_id(self, id: UUID) -> Service:
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

        raise NotFoundException(self.entity_name, id)


def get_service_service(session: SessionDep) -> ServiceService:
    return ServiceService(session)


ServiceServiceDep = Annotated[ServiceService, Depends(get_service_service)]
