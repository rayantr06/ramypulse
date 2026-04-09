"""Routeur FastAPI pour la registry des clients et le tenant actif."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.deps.tenant import require_operator_client
from api.schemas import ClientCreate, ClientResponse, ClientSetActive
from core.tenancy.client_manager import create_client, get_active_client, set_active_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", response_model=ClientResponse, status_code=201)
def create_client_route(
    payload: ClientCreate,
    _operator = Depends(require_operator_client),
) -> ClientResponse:
    """Crée un nouveau client dans la registry."""
    try:
        client = create_client(
            client_name=payload.client_name,
            industry=payload.industry,
        )
        return ClientResponse(**client)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Erreur create_client_route: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/active", response_model=ClientResponse)
def set_active_client_route(
    payload: ClientSetActive,
    _operator = Depends(require_operator_client),
) -> ClientResponse:
    """Définit le client actif runtime."""
    try:
        client = set_active_client(payload.client_id)
        return ClientResponse(**client)
    except KeyError:
        raise HTTPException(status_code=404, detail="Client introuvable")
    except Exception as exc:
        logger.error("Erreur set_active_client_route: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/active", response_model=ClientResponse)
def get_active_client_route(
    _operator = Depends(require_operator_client),
) -> ClientResponse:
    """Retourne le client actif persiste avec fallback expo securise."""
    try:
        client = get_active_client()
        return ClientResponse(**client)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur get_active_client_route: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
