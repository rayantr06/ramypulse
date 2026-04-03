"""Routeur FastAPI pour les recommandations IA RamyPulse.

Délègue au core.recommendation pour la génération (agent_client),
l'assemblage de contexte (context_builder) et la persistance
(recommendation_manager).
"""

import logging

from fastapi import APIRouter, HTTPException

import config
from api.data_loader import load_annotated
from api.schemas import RecommendationGenerate, RecommendationStatusUpdate
from core.recommendation import agent_client, context_builder, recommendation_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/providers")
def get_providers():
    """Affiche le catalogue de fournisseurs LLM configurés."""
    return {"providers": getattr(agent_client, "MODEL_CATALOG", {})}


@router.get("/context-preview")
def get_context_preview(trigger_type: str = "manual", trigger_id: str = None):
    """Prévisualisation du contexte compilé avant génération LLM."""
    try:
        df_annotated = load_annotated()
        ctx = context_builder.build_recommendation_context(
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            df_annotated=df_annotated,
        )
        return {
            "estimated_tokens": ctx.get("estimated_tokens", len(str(ctx)) // 4),
            "nss_global": ctx.get("current_metrics", {}).get("nss_global"),
            "volume_total": ctx.get("current_metrics", {}).get("volume_total", 0),
            "active_alerts_count": len(ctx.get("active_alerts", [])),
            "active_watchlists_count": len(ctx.get("active_watchlists", [])),
            "recent_campaigns_count": len(ctx.get("recent_campaigns", [])),
            "trigger": trigger_type,
        }
    except Exception as e:
        logger.error("Erreur context-preview: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
def generate_recommendations(req: RecommendationGenerate):
    """Génère de nouvelles recommandations via le LLM."""
    try:
        df_annotated = load_annotated()
        if df_annotated.empty:
            raise HTTPException(
                status_code=400,
                detail="Données annotées indisponibles. Lancez d'abord le pipeline.",
            )

        ctx = context_builder.build_recommendation_context(
            trigger_type=req.trigger_type,
            trigger_id=req.trigger_id,
            df_annotated=df_annotated,
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


@router.get("")
def list_recommendations(status: str = None, limit: int = 50):
    """Récupère l'historique des recommandations générées."""
    try:
        return recommendation_manager.list_recommendations(
            status=status, limit=limit
        )
    except Exception as e:
        logger.error("Erreur list_recommendations: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{recommendation_id}")
def get_recommendation(recommendation_id: str):
    """Détail d'une recommandation IA."""
    try:
        rec = recommendation_manager.get_recommendation(recommendation_id)
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
