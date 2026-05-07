from fastapi import Depends

from app.database.model import EcosystemTicket, ServiceTicket
from app.domain.tickets.schemas import (
    EcosystemTicketCreate,
    EcosystemTicketResponse,
    EcosystemTicketUpdate,
    ServiceTicketCreate,
    ServiceTicketResponse,
    ServiceTicketUpdate,
)
from app.domain.tickets.service import EcosystemTicketServiceDep, ServiceTicketServiceDep
from app.shared.authorization.dependencies import require_delete, require_read, require_write
from app.shared.base_domain.controller import FullCrudApiController
from app.shared.rate_limit import rate_limiter


class ServiceTicketController(FullCrudApiController):
    prefix = "/tickets/service"
    tags = ["Tickets"]
    service_dep = ServiceTicketServiceDep
    response_schema = ServiceTicketResponse
    create_schema = ServiceTicketCreate
    update_schema = ServiceTicketUpdate

    router_dependencies = [Depends(rate_limiter(max_requests=3, window_seconds=1.0, scope="tickets_service"))]

    list_dependencies = [require_read(ServiceTicket)]
    retrieve_dependencies = [require_read(ServiceTicket)]
    create_dependencies = [require_write(ServiceTicket)]
    update_dependencies = [require_write(ServiceTicket)]
    delete_dependencies = [require_delete(ServiceTicket)]


class EcosystemTicketController(FullCrudApiController):
    prefix = "/tickets/ecosystem"
    tags = ["Tickets"]
    service_dep = EcosystemTicketServiceDep
    response_schema = EcosystemTicketResponse
    create_schema = EcosystemTicketCreate
    update_schema = EcosystemTicketUpdate

    router_dependencies = [Depends(rate_limiter(max_requests=3, window_seconds=1.0, scope="tickets_ecosystem"))]

    list_dependencies = [require_read(EcosystemTicket)]
    retrieve_dependencies = [require_read(EcosystemTicket)]
    create_dependencies = [require_write(EcosystemTicket)]
    update_dependencies = [require_write(EcosystemTicket)]
    delete_dependencies = [require_delete(EcosystemTicket)]


service_ticket_router = ServiceTicketController().router
ecosystem_ticket_router = EcosystemTicketController().router
