from uuid import UUID

from app.domain.personal_data.schemas import NonCriticalPersonalDataResponse
from app.shared.base_domain.schemas import BaseSchemaResponse

class UserResponse(NonCriticalPersonalDataResponse):
    pass


class UserRoleResponse(BaseSchemaResponse):
    user_id: UUID
    role_id: UUID
