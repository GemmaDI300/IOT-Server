from abc import ABC
from typing import Annotated, override
from uuid import UUID
from fastapi import Depends
from app.database import SessionDep
from app.database.model import EcosystemTicket, ServiceTicket
from app.domain.tickets.repository import EcosystemTicketRepository, ServiceTicketRepository
from app.domain.tickets.schemas import (
    EcosystemTicketCreate,
    EcosystemTicketUpdate,
    ServiceTicketCreate,
    ServiceTicketUpdate,
)
from app.shared.base_domain.service import BaseService, IBaseService
from app.shared.authorization.dependencies import get_current_user_from_context
from app.shared.exceptions import NotFoundException
from app.shared.pagination import PageResponse


class IServiceTicketService(
    IBaseService[ServiceTicket, ServiceTicketCreate, ServiceTicketUpdate], ABC
):
    pass


class ServiceTicketService(
    BaseService[ServiceTicket, ServiceTicketCreate, ServiceTicketUpdate],
    IServiceTicketService,
):
    entity_name = "ServiceTicket"
    repository_class = ServiceTicketRepository

    @override
    def get_all(self, offset: int = 0, limit: int = 20) -> PageResponse[ServiceTicket]:
        current_user = get_current_user_from_context()
        if current_user is None:
            return super().get_all(offset, limit)

        if current_user.account_type == "administrator":
            items, total = self.repository.get_all(offset, limit)
        elif current_user.account_type == "manager":
            items, total = self.repository.get_for_manager_sql(current_user.account_id, offset, limit)
        elif current_user.account_type == "user":
            items, total = self.repository.get_for_user(current_user.account_id, offset, limit)
        else:
            return PageResponse(total=0, offset=offset, limit=limit, data=[])

        return PageResponse(total=total, offset=offset, limit=limit, data=items)

    @override
    def get_by_id(self, id: UUID) -> ServiceTicket:
        entity = self.repository.get_by_id(id)
        if not entity:
            raise NotFoundException(self.entity_name, id)
        return entity


def get_service_ticket_service(session: SessionDep) -> ServiceTicketService:
    return ServiceTicketService(session)


ServiceTicketServiceDep = Annotated[ServiceTicketService, Depends(get_service_ticket_service)]


class IEcosystemTicketService(
    IBaseService[EcosystemTicket, EcosystemTicketCreate, EcosystemTicketUpdate], ABC
):
    pass


class EcosystemTicketService(
    BaseService[EcosystemTicket, EcosystemTicketCreate, EcosystemTicketUpdate],
    IEcosystemTicketService,
):
    entity_name = "EcosystemTicket"
    repository_class = EcosystemTicketRepository

    @override
    def get_all(self, offset: int = 0, limit: int = 20) -> PageResponse[EcosystemTicket]:
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
    def get_by_id(self, id: UUID) -> EcosystemTicket:
        entity = self.repository.get_by_id(id)
        if not entity:
            raise NotFoundException(self.entity_name, id)
        return entity


def get_ecosystem_ticket_service(session: SessionDep) -> EcosystemTicketService:
    return EcosystemTicketService(session)


EcosystemTicketServiceDep = Annotated[
    EcosystemTicketService, Depends(get_ecosystem_ticket_service)
]
