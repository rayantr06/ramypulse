"""Routeur FastAPI pour les recommandations IA RamyPulse.

Délègue au core.recommendation pour la génération (agent_client),
l'assemblage de contexte (context_builder) et la persistance
(recommendation_manager).
"""

import logging
from math import isfinite

from fastapi import APIRouter, Depends, HTTPException

import config
from api.data_loader import load_annotated
from api.deps.tenant import resolve_client_id
from api.schemas import (
    ContextPreview,
    RecommendationBulkStatusUpdate,
    RecommendationGenerate,
    RecommendationStatusUpdate,
)
from core.recommendation import agent_client, context_builder, recommendation_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _estimate_prompt_cost_usd(
    provider: str | None,
    model: str | None,
    estimated_tokens: int,
) -> float | None:
    """Estimate prompt-only cost from the configured model pricing table."""
    if estimated_tokens <= 0:
        return 0.0

    provider_key = provider or config.DEFAULT_AGENT_PROVIDER
    model_key = model or config.DEFAULT_AGENT_MODEL
    price_per_1k = (
        config.LLM_INPUT_PRICING_USD_PER_1K_TOKENS.get(provider_key, {}).get(model_key)
    )
    if price_per_1k is None:
        return None

    estimate = (estimated_tokens / 1000.0) * float(price_per_1k)
    return round(estimate, 6) if isfinite(estimate) else None


@router.get("/providers")
def get_providers():
    """Affiche le catalogue de fournisseurs LLM configurés."""
    return {"providers": getattr(agent_client, "MODEL_CATALOG", {})}


@router.get("/context-preview", response_model=ContextPreview)
def get_context_preview(
    trigger_type: str = "manual",
    trigger_id: str = None,
    provider: str | None = None,
    model: str | None = None,
    client_id: str = Depends(resolve_client_id),
):
    """Prévisualisation du contexte compilé avant génération LLM."""
    try:
        df_annotated = load_annotated(client_id=client_id)
        ctx = context_builder.build_recommendation_context(
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            df_annotated=df_annotated,
            client_id=client_id,
        )
        provider_used = provider or config.DEFAULT_AGENT_PROVIDER
        model_used = model or config.DEFAULT_AGENT_MODEL
        estimated_tokens = ctx.get("estimated_tokens", len(str(ctx)) // 4)
        return {
            "estimated_tokens": estimated_tokens,
            "estimated_cost_usd": _estimate_prompt_cost_usd(
                provider=provider_used,
                model=model_used,
                estimated_tokens=estimated_tokens,
            ),
            "nss_global": ctx.get("current_metrics", {}).get("nss_global"),
            "volume_total": ctx.get("current_metrics", {}).get("volume_total", 0),
            "active_alerts_count": len(ctx.get("active_alerts", [])),
            "active_watchlists_count": len(ctx.get("active_watchlists", [])),
            "recent_campaigns_count": len(ctx.get("recent_campaigns", [])),
            "provider_used": provider_used,
            "model_used": model_used,
            "pricing_basis": "prompt_input_usd_per_1k_tokens",
            "trigger": trigger_type,
        }
    except Exception as e:
        logger.error("Erreur context-preview: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
def generate_recommendations(
    req: RecommendationGenerate,
    client_id: str = Depends(resolve_client_id),
):
    """Génère de nouvelles recommandations via le LLM."""
    try:
        df_annotated = load_annotated(client_id=client_id)
        if df_annotated.empty:
            raise HTTPException(
                status_code=400,
                detail="Données annotées indisponibles. Lancez d'abord le pipeline.",
            )

        ctx = context_builder.build_recommendation_context(
            trigger_type=req.trigger_type,
            trigger_id=req.trigger_id,
            df_annotated=df_annotated,
            client_id=client_id,
        )

        provider = req.provider or config.DEFAULT_AGENT_PROVIDER
        model = req.model or config.DEFAULT_AGENT_MODEL

        result = agent_client.generate_recommendations(
            context=ctx,
            provider=provider,
            model=model,
            api_key=req.api_key,
        )

        # result already contains provider_used, model_used, generation_ms
        # from the agent_client — pass it directly to save_recommendation
        rec_id = recommendation_manager.save_recommendation(
            result=result,
            trigger_type=req.trigger_type,
            trigger_id=req.trigger_id,
            client_id=client_id,
        )

        return {
            "result": "success",
            "recommendation_id": rec_id,
            "recommendations_count": len(result.get("recommendations", [])),
            "confidence_score": result.get("confidence_score", 0.0),
            "generation_ms": result.get("generation_ms"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur generate_recommendations: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


_VALID_STATUSES = {"active", "archived", "dismissed"}


@router.post("/bulk-status")
def bulk_update_recommendation_status(payload: RecommendationBulkStatusUpdate):
    """Met à jour le statut de plusieurs recommandations en une transaction.

    - IDs inexistants : ignorés silencieusement
    - Status invalide : HTTP 422
    - Retourne {"updated": N, "ids": [...ids mis à jour...]}
    """
    if payload.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide '{payload.status}'. Valeurs acceptées : {sorted(_VALID_STATUSES)}",
        )

    if not payload.ids:
        return {"updated": 0, "ids": []}

    try:
        updated_ids = recommendation_manager.bulk_update_status(payload.ids, payload.status)
        return {"updated": len(updated_ids), "ids": updated_ids}
    except Exception as e:
        logger.error("Erreur bulk_update_recommendation_status: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def list_recommendations(
    status: str = None,
    limit: int = 50,
    client_id: str = Depends(resolve_client_id),
):
    """Récupère l'historique des recommandations générées."""
    try:
        return recommendation_manager.list_recommendations(
            status=status,
            limit=limit,
            client_id=client_id,
        )
    except Exception as e:
        logger.error("Erreur list_recommendations: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{recommendation_id}")
def get_recommendation(
    recommendation_id: str,
    client_id: str = Depends(resolve_client_id),
):
    """Détail d'une recommandation IA."""
    try:
        rec = recommendation_manager.get_recommendation(recommendation_id, client_id=client_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return rec
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur get_recommendation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{recommendation_id}/status")
def update_recommendation(
    recommendation_id: str, payload: RecommendationStatusUpdate
):
    """Mise à jour du statut d'une recommandation."""
    try:
        success = recommendation_manager.update_recommendation_status(
            recommendation_id, payload.status
        )
        if not success:
            raise HTTPException(
                status_code=404, detail="Recommendation not found"
            )
        return {
            "result": "success",
            "recommendation_id": recommendation_id,
            "status": payload.status,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur update_recommendation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
