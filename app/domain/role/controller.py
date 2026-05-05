from app.database.model import Role
from app.domain.role.schemas import RoleCreate, RoleResponse, RoleUpdate
from app.domain.role.service import RoleServiceDep
from app.shared.authorization.dependencies import require_delete, require_read, require_write
from app.shared.base_domain.controller import FullCrudApiController


class RoleController(FullCrudApiController):
    prefix = "/roles"
    tags = ["Roles"]
    service_dep = RoleServiceDep
    response_schema = RoleResponse
    create_schema = RoleCreate
    update_schema = RoleUpdate

    list_dependencies = [require_read(Role)]
    retrieve_dependencies = [require_read(Role)]
    create_dependencies = [require_write(Role)]
    update_dependencies = [require_write(Role)]
    delete_dependencies = [require_delete(Role)]


role_router = RoleController().router
