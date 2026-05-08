from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.shared.base_domain.schemas import BaseSchemaResponse



class SubscriptionTypeCreate(BaseModel):
    type: str
    cost: float


class SubscriptionTypeUpdate(BaseModel):
    type: str | None = None
    cost: float | None = None


class SubscriptionTypeResponse(BaseSchemaResponse):
    type: str
    cost: float




class UserServiceResponse(BaseSchemaResponse):
    user_id: UUID
    service_id: UUID
    is_active: bool




class PaymentCreate(BaseModel):
    user_service_id: UUID
    subscription_type_id: UUID
    deposit_id: str
    amount: float


class PaymentResponse(BaseSchemaResponse):
    user_service_id: UUID
    subscription_type_id: UUID
    expires_at: datetime




class PaymentHistoryResponse(BaseSchemaResponse):
    payment_id: UUID
    deposit_id: str
    amount: float
    period_start: datetime
    period_end: datetime
