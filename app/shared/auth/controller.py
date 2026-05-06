from fastapi import APIRouter, Depends, Request

from app.shared.auth.auth_policy import AuthMethod, validate_auth_method_for_entity
from app.shared.auth.schemas import (
    ChangePasswordRequest,
    EntityPuzzleLoginRequest,
    HumanLoginRequest,
    HumanScopedLoginRequest,
    HumanXMSSChallengeRequest,
    HumanXMSSVerifyRequest,
    MessageResponse,
    TokenResponse,
    XMSSChallengeRequest,
    XMSSChallengeResponse,
    XMSSVerifyRequest,
)
from app.shared.auth.service import (
    CurrentAccountDep,
    SharedAuthServiceDep,
    logout_current_token,
)
from app.shared.rate_limit import enforce_request_rate_limit


change_password_logout_router = APIRouter(
    prefix="/auth",
    tags=["Change Password / Logout"],
    dependencies=[Depends(enforce_request_rate_limit)],
)
auth_rc_router = APIRouter(
    prefix="/auth-rc",
    tags=["Auth RC"],
    dependencies=[Depends(enforce_request_rate_limit)],
)
auth_xmss_router = APIRouter(
    prefix="/auth-xmss",
    tags=["Auth XMSS"],
    dependencies=[Depends(enforce_request_rate_limit)],
)


def _validate_rc(entity_type: str) -> None:
    validate_auth_method_for_entity(entity_type, AuthMethod.AUTH_RC.value)


def _validate_xmss(entity_type: str) -> None:
    validate_auth_method_for_entity(entity_type, AuthMethod.AUTH_XMSS.value)


def _build_human_login_request(
    entity_type: str,
    payload: HumanScopedLoginRequest,
) -> HumanLoginRequest:
    return HumanLoginRequest(
        entity_type=entity_type,
        email=payload.email,
        password=payload.password,
    )


def _build_human_xmss_challenge_request(
    entity_type: str,
    payload: HumanXMSSChallengeRequest,
) -> XMSSChallengeRequest:
    return XMSSChallengeRequest(
        entity_type=entity_type,
        identifier=payload.identifier,
        password=payload.password,
        tree_height=payload.tree_height,
    )


def _build_human_xmss_verify_request(
    entity_type: str,
    payload: HumanXMSSVerifyRequest,
) -> XMSSVerifyRequest:
    return XMSSVerifyRequest(
        entity_type=entity_type,
        identifier=payload.identifier,
        challenge=payload.challenge,
        leaf_index=payload.leaf_index,
        message=payload.message,
        signature=payload.signature,
        ots_public_key=payload.ots_public_key,
        auth_path=payload.auth_path,
    )


@change_password_logout_router.patch("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    service: SharedAuthServiceDep,
    current: CurrentAccountDep,
):
    return service.change_password(current, payload)


@change_password_logout_router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    _current: CurrentAccountDep,
):
    return await logout_current_token(request)


# ============================================================
# AUTH RC - LOGIN POR ENTIDAD HUMANA
# ============================================================

@auth_rc_router.post("/user/login", response_model=TokenResponse)
def login_user_rc(
    payload: HumanScopedLoginRequest,
    service: SharedAuthServiceDep,
):
    _validate_rc("user")
    return service.login_human_rc(
        _build_human_login_request("user", payload)
    )


@auth_rc_router.post("/manager/login", response_model=TokenResponse)
def login_manager_rc(
    payload: HumanScopedLoginRequest,
    service: SharedAuthServiceDep,
):
    _validate_rc("manager")
    return service.login_human_rc(
        _build_human_login_request("manager", payload)
    )


@auth_rc_router.post("/admin/login", response_model=TokenResponse)
def login_admin_rc(
    payload: HumanScopedLoginRequest,
    service: SharedAuthServiceDep,
):
    _validate_rc("administrator")
    return service.login_human_rc(
        _build_human_login_request("administrator", payload),
        expected_is_master=False,
    )


@auth_rc_router.post("/master/login", response_model=TokenResponse)
def login_master_rc(
    payload: HumanScopedLoginRequest,
    service: SharedAuthServiceDep,
):
    _validate_rc("administrator")
    return service.login_human_rc(
        _build_human_login_request("administrator", payload),
        expected_is_master=True,
    )


# ============================================================
# AUTH RC - DISPOSITIVOS Y APLICACIONES
# ============================================================

@auth_rc_router.post("/devices/login", response_model=TokenResponse)
def login_device_rc(
    payload: EntityPuzzleLoginRequest,
    service: SharedAuthServiceDep,
):
    _validate_rc("device")
    return service.login_device_rc(payload)


@auth_rc_router.post("/applications/login", response_model=TokenResponse)
def login_application_rc(
    payload: EntityPuzzleLoginRequest,
    service: SharedAuthServiceDep,
):
    _validate_rc("application")
    return service.login_application_rc(payload)


# ============================================================
# AUTH XMSS - USER
# ============================================================

@auth_xmss_router.post("/user/challenge", response_model=XMSSChallengeResponse)
def create_user_xmss_challenge(
    payload: HumanXMSSChallengeRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("user")
    return service.create_xmss_challenge(
        _build_human_xmss_challenge_request("user", payload)
    )


@auth_xmss_router.post("/user/verify", response_model=TokenResponse)
def verify_user_xmss(
    payload: HumanXMSSVerifyRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("user")
    return service.verify_xmss(
        _build_human_xmss_verify_request("user", payload)
    )


# ============================================================
# AUTH XMSS - MANAGER
# ============================================================

@auth_xmss_router.post("/manager/challenge", response_model=XMSSChallengeResponse)
def create_manager_xmss_challenge(
    payload: HumanXMSSChallengeRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("manager")
    return service.create_xmss_challenge(
        _build_human_xmss_challenge_request("manager", payload)
    )


@auth_xmss_router.post("/manager/verify", response_model=TokenResponse)
def verify_manager_xmss(
    payload: HumanXMSSVerifyRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("manager")
    return service.verify_xmss(
        _build_human_xmss_verify_request("manager", payload)
    )


# ============================================================
# AUTH XMSS - ADMIN NORMAL
# ============================================================

@auth_xmss_router.post("/admin/challenge", response_model=XMSSChallengeResponse)
def create_admin_xmss_challenge(
    payload: HumanXMSSChallengeRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("administrator")
    return service.create_xmss_challenge(
        _build_human_xmss_challenge_request("administrator", payload),
        expected_is_master=False,
    )


@auth_xmss_router.post("/admin/verify", response_model=TokenResponse)
def verify_admin_xmss(
    payload: HumanXMSSVerifyRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("administrator")
    return service.verify_xmss(
        _build_human_xmss_verify_request("administrator", payload),
        expected_is_master=False,
    )


# ============================================================
# AUTH XMSS - MASTER ADMIN
# ============================================================

@auth_xmss_router.post("/master/challenge", response_model=XMSSChallengeResponse)
def create_master_xmss_challenge(
    payload: HumanXMSSChallengeRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("administrator")
    return service.create_xmss_challenge(
        _build_human_xmss_challenge_request("administrator", payload),
        expected_is_master=True,
    )


@auth_xmss_router.post("/master/verify", response_model=TokenResponse)
def verify_master_xmss(
    payload: HumanXMSSVerifyRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("administrator")
    return service.verify_xmss(
        _build_human_xmss_verify_request("administrator", payload),
        expected_is_master=True,
    )


# ============================================================
# AUTH XMSS - DEVICES
# ============================================================

@auth_xmss_router.post("/devices/challenge", response_model=XMSSChallengeResponse)
def create_device_xmss_challenge(
    payload: XMSSChallengeRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("device")
    if payload.entity_type != "device":
        from app.shared.exceptions import BadRequestException

        raise BadRequestException("Invalid device entity type")

    return service.create_xmss_challenge(payload)


@auth_xmss_router.post("/devices/verify", response_model=TokenResponse)
def verify_device_xmss(
    payload: XMSSVerifyRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("device")
    if payload.entity_type != "device":
        from app.shared.exceptions import BadRequestException

        raise BadRequestException("Invalid device entity type")

    return service.verify_xmss(payload)


# ============================================================
# AUTH XMSS - APPLICATIONS
# ============================================================

@auth_xmss_router.post("/applications/challenge", response_model=XMSSChallengeResponse)
def create_application_xmss_challenge(
    payload: XMSSChallengeRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("application")
    if payload.entity_type != "application":
        from app.shared.exceptions import BadRequestException

        raise BadRequestException("Invalid application entity type")

    return service.create_xmss_challenge(payload)


@auth_xmss_router.post("/applications/verify", response_model=TokenResponse)
def verify_application_xmss(
    payload: XMSSVerifyRequest,
    service: SharedAuthServiceDep,
):
    _validate_xmss("application")
    if payload.entity_type != "application":
        from app.shared.exceptions import BadRequestException

        raise BadRequestException("Invalid application entity type")

    return service.verify_xmss(payload)