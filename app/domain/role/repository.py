from abc import ABC
from sqlmodel import Session
from app.database.model import Role
from app.shared.base_domain.repository import BaseRepository, IBaseRepository


class IRoleRepository(IBaseRepository[Role], ABC):
    pass


class RoleRepository(BaseRepository[Role], IRoleRepository):
    model = Role

    def __init__(self, session: Session):
        super().__init__(session)
