import logging
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import sqlite3
import config

from api.data_loader import load_annotated
from api.schemas import RecommendationGenerate, RecommendationStatusUpdate
from core.recommendation import recommendation_manager, context_builder, agent_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.get("/providers")
def get_providers():
    """Affiche le catalogue de fournisseurs LLM configurés."""
    # Assuming MODEL_CATALOG is defined in agent_client
    return {"providers": getattr(agent_client, "MODEL_CATALOG", {})}

@router.get("/context-preview")
def get_context_preview(trigger_type: str = "manual", trigger_id: str = None):
    """Prévisualisation du contexte compilé avant génération LLM."""
    try:
        df_annotated = load_annotated()
        context = context_builder.build_recommendation_context(trigger_type=trigger_type, trigger_id=trigger_id, df_annotated=df_annotated)
        # Simply return context sizing stats for preview
        return {
            "estimated_tokens": len(str(context)) // 4,
            "trigger": trigger_type
        }
    except Exception as e:
        logger.error(f"Erreur context-preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
def generate_recommendations(req: RecommendationGenerate):
    """Génère de nouvelles recommandations via le LLM."""
    try:
        df_annotated = load_annotated()
        context_data = context_builder.build_recommendation_context(trigger_type=req.trigger_type, trigger_id=req.trigger_id, df_annotated=df_annotated)
        
        provider = req.provider or config.AGENT_PROVIDER
        model = req.model or config.AGENT_MODEL
        
        prediction = agent_client.generate_recommendations(
            context_data=context_data,
            provider=provider,
            model=model,
            api_key=req.api_key
        )
        
        payload = {
            "trigger_type": req.trigger_type,
            "trigger_id": req.trigger_id,
            "analysis_summary": prediction.get("analysis_summary", ""),
            "recommendations": prediction.get("recommendations", []),
            "watchlist_priorities": prediction.get("watchlist_priorities", []),
            "confidence_score": prediction.get("confidence_score", 0.0),
            "data_quality_note": prediction.get("data_quality_note", ""),
            "provider_used": provider,
            "model_used": model,
        }
        
        rec_id = recommendation_manager.save_recommendation(payload, req.trigger_type, req.trigger_id)
        return {"result": "success", "recommendation_id": rec_id}
    except Exception as e:
        logger.error(f"Erreur generate_recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
def list_recommendations(limit: int = 50):
    """Récupère l'historique des recommandations générées."""
    try:
        return recommendation_manager.list_recommendations(limit=limit)
    except Exception as e:
        logger.error(f"Erreur list_recommendations: {e}")
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
        logger.error(f"Erreur get_recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{recommendation_id}/status")
def update_recommendation(recommendation_id: str, payload: RecommendationStatusUpdate):
    """Mise à jour du statut d'une recommandation."""
    try:
        success = recommendation_manager.update_recommendation_status(recommendation_id, payload.status)
        if not success:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        return {"result": "success", "recommendation_id": recommendation_id, "status": payload.status}
    except Exception as e:
        logger.error(f"Erreur update_recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
