"""Auth manager base para entidades humanas."""

from __future__ import annotations

from abc import ABC
from typing import TypeVar

from app.shared.base_domain.model import BaseTable
from app.shared.middleware.auth.auth_manager.manager import AuthManager
from app.shared.middleware.auth.auth_rc.human import HumanAuth
from app.shared.middleware.auth.auth_xmss.human import HumanXMSSAuth

T = TypeVar("T", bound=BaseTable)


class HumanAuthManager(AuthManager[T], ABC):
    """
    Base reusable para user, manager y administrator.

    Deja registrado el switch entre auth RC y auth XMSS.
    Cada implementación concreta solo debe aportar el repository
    y cómo extraer el entity_id del request.
    """

    _auth_methods = {
        "rc": HumanAuth,
        "xmss": HumanXMSSAuth,
    }