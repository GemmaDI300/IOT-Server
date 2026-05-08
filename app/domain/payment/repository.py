from abc import ABC
from app.shared.base_domain.repository import IBaseRepository, BaseRepository
from app.database.model import Payment
from sqlmodel import Session


class IPaymentRepository(IBaseRepository[Payment], ABC):
    pass


class PaymentRepository(BaseRepository[Payment], IPaymentRepository):
    model = Payment

    def __init__(self, session: Session):
        super().__init__(session)
