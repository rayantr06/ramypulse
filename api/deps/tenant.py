"""Dependances FastAPI pour la resolution du client actif."""

from __future__ import annotations

import importlib

from fastapi import Depends, Header, HTTPException, Query

from core.security.auth import AuthContext, get_current_client

import config
from core.runtime.runtime_settings_manager import get_runtime_setting

_ACTIVE_CLIENT_SETTING_KEY = "active_client_id"


def _config_module():
    """Retourne le module config courant, même après reload dans les tests."""
    return importlib.import_module("config")


def require_operator_client(
    auth: AuthContext = Depends(get_current_client),
) -> AuthContext:
    """Valide que la cle authentifiee appartient au client operateur expo."""
    if auth.client_id != getattr(_config_module(), "SAFE_EXPO_CLIENT_ID", config.SAFE_EXPO_CLIENT_ID):
        raise HTTPException(status_code=403, detail="Operator access required")
    return auth


def resolve_client_id(
    auth: AuthContext = Depends(get_current_client),
    x_ramy_client_id: str | None = Header(default=None, alias="X-Ramy-Client-Id"),
    query_client_id: str | None = Query(default=None, alias="client_id"),
) -> str:
    """Resout le tenant cible selon la cle auth et le modele expo safe."""
    cfg = _config_module()
    requested_client_id = None
    if x_ramy_client_id and x_ramy_client_id.strip():
        requested_client_id = x_ramy_client_id.strip()
    elif query_client_id and query_client_id.strip():
        requested_client_id = query_client_id.strip()

    safe_expo_client_id = getattr(cfg, "SAFE_EXPO_CLIENT_ID", config.SAFE_EXPO_CLIENT_ID)

    if auth.client_id != safe_expo_client_id:
        if requested_client_id and requested_client_id != auth.client_id:
            raise HTTPException(status_code=403, detail="Tenant override forbidden")
        return auth.client_id

    if requested_client_id:
        return requested_client_id

    runtime_client_id = get_runtime_setting(_ACTIVE_CLIENT_SETTING_KEY)
    if isinstance(runtime_client_id, str) and runtime_client_id.strip():
        return runtime_client_id.strip()

    return safe_expo_client_id
