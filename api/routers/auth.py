"""Routeur FastAPI pour la gestion des cles API RamyPulse."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse
from core.security.auth import (
    AuthContext,
    create_api_key,
    deactivate_api_key,
    get_current_client,
    list_api_keys,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/keys", response_model=ApiKeyCreatedResponse, status_code=201)
def create_key(
    payload: ApiKeyCreate,
    auth: AuthContext = Depends(get_current_client),
):
    """Create a new API key. Returns the raw key ONCE."""
    key_id, raw_key = create_api_key(
        client_id=payload.client_id,
        label=payload.label,
    )
    return ApiKeyCreatedResponse(
        key_id=key_id,
        client_id=payload.client_id,
        key_prefix=raw_key[:12],
        label=payload.label,
        api_key=raw_key,
    )


@router.get("/keys", response_model=list[ApiKeyResponse])
def list_keys(
    auth: AuthContext = Depends(get_current_client),
):
    """List all API keys (never exposes hash or raw key)."""
    rows = list_api_keys()
    return [ApiKeyResponse(**row) for row in rows]


@router.delete("/keys/{key_id}")
def delete_key(
    key_id: str,
    auth: AuthContext = Depends(get_current_client),
):
    """Deactivate an API key (soft delete)."""
    if not deactivate_api_key(key_id):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "deactivated", "key_id": key_id}
