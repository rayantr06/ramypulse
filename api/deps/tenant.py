"""Dependances FastAPI pour la resolution du client actif."""

from __future__ import annotations

from fastapi import Header

import config
from core.runtime.runtime_settings_manager import get_runtime_setting

_ACTIVE_CLIENT_SETTING_KEY = "active_client_id"


def resolve_client_id(
    x_ramy_client_id: str | None = Header(default=None, alias="X-Ramy-Client-Id"),
) -> str:
    """Retourne le client demande, sinon le tenant actif runtime, sinon l'expo safe."""
    if x_ramy_client_id and x_ramy_client_id.strip():
        return x_ramy_client_id.strip()

    runtime_client_id = get_runtime_setting(_ACTIVE_CLIENT_SETTING_KEY)
    if isinstance(runtime_client_id, str) and runtime_client_id.strip():
        return runtime_client_id.strip()

    return config.SAFE_EXPO_CLIENT_ID
