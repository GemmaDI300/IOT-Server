# ============================================================================
# Fine-Grained RBAC Policies (Polar)
# Pattern: Least Privilege + Instance-Level Control + Granular Filtering
#
# Decisiones confirmadas:
# 1. Managers crean Users: SI
# 2. Managers se ven: NO (aislamiento total)
# 3. Manager ve PersonalData: SI (del equipo)
# 4. Todos crean Tickets: SI
# 5. Managers asignan ServiceTicket: SI (equipo)
# 6. Solo admins ven Roles: SI
# 7. Managers ven Devices: SOLO LOS SUYOS
# 8. Admin Normal crea Roles: NO (Master only)
#
# NOTE: Type-level rules use _resource wildcards. Instance-level filtering
# is applied at the repository layer via SQL VIEWs (device_manager_vw, etc.)
# ============================================================================

actor CurrentUser {}

# ============================================================================
# NIVEL 1: ADMIN MASTER
# ============================================================================
allow(user: CurrentUser, _action, _resource) if
    user.account_type = "administrator" and
    user.is_master = true;


# ============================================================================
# NIVEL 2: ADMIN NORMAL (No Master)
# ============================================================================
allow(user: CurrentUser, "read", _resource: User) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "write", _resource: User) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "delete", _resource: User) if
    user.account_type = "administrator" and
    user.is_master = false;

# Admin normal: NO puede ver/editar otros admins
allow(user: CurrentUser, "read", _resource: Administrator) if
    user.account_type = "administrator" and
    user.is_master = false;

# Admin normal: NO puede ver/editar otros admins
allow(user: CurrentUser, "read", _resource: Administrator) if
    user.account_type = "administrator" and
    user.is_master = false;

deny(user: CurrentUser, _action, admin: Administrator) if
    user.account_type = "administrator" and
    user.is_master = false and
    admin.id != user.account_id;

allow(user: CurrentUser, "read", _resource: Role) if
    user.account_type = "administrator" and
    user.is_master = false;

deny(user: CurrentUser, "write", _resource: Role) if
    user.account_type = "administrator" and
    user.is_master = false;

deny(user: CurrentUser, "delete", _resource: Role) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "read", _resource: Manager) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "write", _resource: Manager) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "delete", _resource: Manager) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "read", _resource: Device) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "write", _resource: Device) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "delete", _resource: Device) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "read", _resource: Application) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "write", _resource: Application) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "delete", _resource: Application) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "read", _resource: Service) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "write", _resource: Service) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "delete", _resource: Service) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "read", _resource: EcosystemTicket) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "write", _resource: EcosystemTicket) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "delete", _resource: EcosystemTicket) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "read", _resource: ServiceTicket) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "write", _resource: ServiceTicket) if
    user.account_type = "administrator" and
    user.is_master = false;

allow(user: CurrentUser, "delete", _resource: ServiceTicket) if
    user.account_type = "administrator" and
    user.is_master = false;



# ============================================================================
# NIVEL 3: MANAGER (Gerente)
# Type-level: Oso allows the action. Instance filtering at repository layer.
# ============================================================================

# Users: read (own team), write (create), no delete
allow(user: CurrentUser, "read", _resource: User) if
    user.account_type = "manager";

allow(user: CurrentUser, "write", _resource: User) if
    user.account_type = "manager";

deny(user: CurrentUser, "delete", _resource: User) if
    user.account_type = "manager";

# Devices: read/write (own team), no delete
allow(user: CurrentUser, "read", _resource: Device) if
    user.account_type = "manager";

allow(user: CurrentUser, "write", _resource: Device) if
    user.account_type = "manager";

deny(user: CurrentUser, "delete", _resource: Device) if
    user.account_type = "manager";

# Applications: read/write (own team), no delete
allow(user: CurrentUser, "read", _resource: Application) if
    user.account_type = "manager";

allow(user: CurrentUser, "write", _resource: Application) if
    user.account_type = "manager";

deny(user: CurrentUser, "delete", _resource: Application) if
    user.account_type = "manager";

# Services: read/write (own team), no delete
allow(user: CurrentUser, "read", _resource: Service) if
    user.account_type = "manager";

allow(user: CurrentUser, "write", _resource: Service) if
    user.account_type = "manager";

deny(user: CurrentUser, "delete", _resource: Service) if
    user.account_type = "manager";

# Managers: NO ver otros managers (aislamiento total)
deny(user: CurrentUser, _action, other_manager: Manager) if
    user.account_type = "manager" and
    other_manager.id != user.account_id;

# Roles: NO acceso
deny(user: CurrentUser, "read", _resource: Role) if
    user.account_type = "manager";

deny(user: CurrentUser, "write", _resource: Role) if
    user.account_type = "manager";


# EcosystemTicket: read/write, no delete
allow(user: CurrentUser, "read", _resource: EcosystemTicket) if
    user.account_type = "manager";

allow(user: CurrentUser, "write", _resource: EcosystemTicket) if
    user.account_type = "manager";

deny(user: CurrentUser, "delete", _resource: EcosystemTicket) if
    user.account_type = "manager";

# ServiceTicket: read/write, no delete
allow(user: CurrentUser, "read", _resource: ServiceTicket) if
    user.account_type = "manager";

allow(user: CurrentUser, "write", _resource: ServiceTicket) if
    user.account_type = "manager";

deny(user: CurrentUser, "delete", _resource: ServiceTicket) if
    user.account_type = "manager";

# Administrators: NO acceso
deny(user: CurrentUser, "read", _resource: Administrator) if
    user.account_type = "manager";


# ============================================================================
# NIVEL 4: USER (Usuario Final)
# Type-level rules for own profile. Instance filtering at repository layer.
# ============================================================================

# Self: read/write own profile only
allow(user: CurrentUser, "read", _resource: User) if
    user.account_type = "user";

allow(user: CurrentUser, "write", _resource: User) if
    user.account_type = "user";

deny(user: CurrentUser, "delete", _resource: User) if
    user.account_type = "user";

# Devices: read own only (filtered in repository)
allow(user: CurrentUser, "read", _resource: Device) if
    user.account_type = "user";

deny(user: CurrentUser, "write", _resource: Device) if
    user.account_type = "user";

deny(user: CurrentUser, "delete", _resource: Device) if
    user.account_type = "user";

# Applications: read own only
allow(user: CurrentUser, "read", _resource: Application) if
    user.account_type = "user";

deny(user: CurrentUser, "write", _resource: Application) if
    user.account_type = "user";

deny(user: CurrentUser, "delete", _resource: Application) if
    user.account_type = "user";

# Services: read own only
allow(user: CurrentUser, "read", _resource: Service) if
    user.account_type = "user";

deny(user: CurrentUser, "write", _resource: Service) if
    user.account_type = "user";

deny(user: CurrentUser, "delete", _resource: Service) if
    user.account_type = "user";


# Roles: NO acceso
deny(user: CurrentUser, "read", _resource: Role) if
    user.account_type = "user";

deny(user: CurrentUser, "write", _resource: Role) if
    user.account_type = "user";

# Tickets: create (ecosystem), read assigned
allow(user: CurrentUser, "read", _resource: EcosystemTicket) if
    user.account_type = "user";

allow(user: CurrentUser, "write", _resource: EcosystemTicket) if
    user.account_type = "user";

allow(user: CurrentUser, "read", _resource: ServiceTicket) if
    user.account_type = "user";

deny(user: CurrentUser, "write", _resource: ServiceTicket) if
    user.account_type = "user";

# Managers: NO acceso
deny(user: CurrentUser, "read", _resource: Manager) if
    user.account_type = "user";

# Administrators: NO acceso
deny(user: CurrentUser, "read", _resource: Administrator) if
    user.account_type = "user";


# ============================================================================
# DEFAULT DENY
# ============================================================================
# Anything not explicitly allowed is denied
