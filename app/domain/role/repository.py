from abc import ABC
from uuid import UUID

from sqlmodel import Session, select

from app.database.model import Role, UserRole
from app.shared.base_domain.repository import BaseRepository, IBaseRepository


class IRoleRepository(IBaseRepository[Role], ABC):
    pass


class RoleRepository(BaseRepository[Role], IRoleRepository):
    model = Role

    def __init__(self, session: Session):
        super().__init__(session)

    # ── UserRole operations ──────────────────────────────────────────

    def get_users_by_role(self, role_id: UUID) -> list[UserRole]:
        stmt = select(UserRole).where(UserRole.role_id == role_id)
        return list(self.session.exec(stmt).all())

    def get_user_role(self, role_id: UUID, user_id: UUID) -> UserRole | None:
        stmt = select(UserRole).where(
            UserRole.role_id == role_id,
            UserRole.user_id == user_id,
        )
        return self.session.exec(stmt).first()

    def create_user_role(self, user_role: UserRole) -> UserRole:
        self.session.add(user_role)
        self.session.commit()
        self.session.refresh(user_role)
        return user_role

    def delete_user_role(self, user_role: UserRole) -> None:
        self.session.delete(user_role)
        self.session.commit()
