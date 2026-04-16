from abc import ABC
from typing import Annotated
from fastapi import Depends
from app.shared.base_domain.service import IBaseService, BaseService
from app.database.model import Application
from app.database import SessionDep
from app.domain.application.repository import ApplicationRepository
from app.domain.application.schemas import ApplicationCreate, ApplicationUpdate
from typing import override
import secrets



class IApplicationService(IBaseService[Application, ApplicationCreate, ApplicationUpdate], ABC):
    pass


class ApplicationService(BaseService[Application, ApplicationCreate, ApplicationUpdate], IApplicationService):
    entity_name = "Application"
    repository_class = ApplicationRepository

    
def get_application_service(session: SessionDep) -> ApplicationService:
    return ApplicationService(session)


ApplicationServiceDep = Annotated[ApplicationService, Depends(get_application_service)]