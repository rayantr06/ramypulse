"""Routeur FastAPI pour les métriques d'engagement social."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

import config
from api.schemas import (
    CampaignPostAdd,
    CampaignRevenuePatch,
    CredentialCreate,
    ManualMetricsInput,
)
from core.social_metrics import credential_manager, metrics_aggregator
from core.social_metrics.instagram_graph_collector import collect_and_save, save_metrics
from core.social_metrics.screenshot_parser import save_screenshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/social-metrics", tags=["Social Metrics"])


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@router.post("/credentials", status_code=201)
def create_credential(data: CredentialCreate):
    """Enregistre un credential plateforme."""
    try:
        credential_id = credential_manager.create_credential(
            entity_type=data.entity_type,
            entity_name=data.entity_name,
            platform=data.platform,
            account_id=data.account_id,
            access_token=data.access_token,
            app_id=data.app_id,
            app_secret=data.app_secret,
            extra_config=data.extra_config,
        )
        return {"credential_id": credential_id, "status": "created"}
    except Exception as exc:
        logger.error("Erreur create_credential : %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/credentials")
def list_credentials(
    platform: str | None = None,
    entity_type: str | None = None,
    is_active: bool = True,
):
    """Liste les credentials enregistrés."""
    try:
        return credential_manager.list_credentials(
            platform=platform,
            entity_type=entity_type,
            is_active=is_active,
        )
    except Exception as exc:
        logger.error("Erreur list_credentials : %s", exc)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.delete("/credentials/{credential_id}", status_code=204)
def deactivate_credential(credential_id: str):
    """Désactive logiquement un credential."""
    try:
        ok = credential_manager.deactivate_credential(credential_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Credential not found")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur deactivate_credential : %s", exc)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.post("/campaigns/{campaign_id}/posts", status_code=201)
def add_campaign_post(campaign_id: str, data: CampaignPostAdd):
    """Lie un post social à une campagne."""
    try:
        post_id = f"post-{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        with _get_db() as conn:
            conn.execute(
                """
                INSERT INTO campaign_posts (
                    post_id, campaign_id, platform, post_platform_id,
                    post_url, entity_type, entity_name, credential_id, added_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    campaign_id,
                    data.platform,
                    data.post_platform_id,
                    data.post_url,
                    data.entity_type,
                    data.entity_name,
                    data.credential_id,
                    now,
                ),
            )
            conn.commit()
        return {"post_id": post_id, "campaign_id": campaign_id, "status": "linked"}
    except Exception as exc:
        logger.error("Erreur add_campaign_post : %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/campaigns/{campaign_id}/posts")
def list_campaign_posts(campaign_id: str):
    """Liste les posts rattachés à une campagne."""
    try:
        with _get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM campaign_posts WHERE campaign_id = ? ORDER BY added_at DESC",
                [campaign_id],
            ).fetchall()
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.error("Erreur list_campaign_posts : %s", exc)
        raise HTTPException(status_code=500, detail="Internal DB error")


@router.post("/campaigns/{campaign_id}/collect")
def collect_campaign_metrics(campaign_id: str):
    """Déclenche une collecte Graph API pour les posts liés."""
    try:
        with _get_db() as conn:
            posts = conn.execute(
                """
                SELECT p.*, c.platform AS cred_platform
                FROM campaign_posts p
                LEFT JOIN platform_credentials c ON p.credential_id = c.credential_id
                WHERE p.campaign_id = ?
                """,
                [campaign_id],
            ).fetchall()

        if not posts:
            raise HTTPException(status_code=404, detail="Aucun post lié à cette campagne")

        results: list[dict] = []
        errors: list[dict] = []
        for post in posts:
            post_dict = dict(post)
            cred_id = post_dict.get("credential_id")
            if not cred_id:
                errors.append({"post_id": post_dict["post_id"], "error": "Pas de credential lié"})
                continue

            cred = credential_manager.get_credential(cred_id)
            if not cred or not cred.get("access_token"):
                errors.append({"post_id": post_dict["post_id"], "error": "Token non résolvable"})
                continue

            try:
                result = collect_and_save(
                    post_dict["post_id"],
                    access_token=cred["access_token"],
                    ig_media_id=post_dict["post_platform_id"],
                )
                results.append({"post_id": post_dict["post_id"], **result})
            except Exception as exc:
                errors.append({"post_id": post_dict["post_id"], "error": str(exc)})

        return {
            "campaign_id": campaign_id,
            "collected": len(results),
            "errors": len(errors),
            "results": results,
            "error_details": errors,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur collect_campaign_metrics : %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/posts/{post_id}/metrics/manual")
def add_manual_metrics(post_id: str, data: ManualMetricsInput):
    """Persiste des métriques manuelles pour un post."""
    try:
        metric_id = save_metrics(
            post_id,
            data.model_dump(),
            collection_mode="manual",
        )
        return {"metric_id": metric_id, "post_id": post_id, "status": "saved"}
    except Exception as exc:
        logger.error("Erreur add_manual_metrics : %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/posts/{post_id}/metrics/screenshot")
async def upload_screenshot(
    post_id: str,
    file: UploadFile = File(...),
    likes: int = Form(0),
    comments: int = Form(0),
    shares: int = Form(0),
    views: int = Form(0),
    reach: int = Form(0),
    impressions: int = Form(0),
    saves: int = Form(0),
):
    """Upload d'une capture d'écran avec métriques visibles."""
    try:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=422, detail="Le fichier doit être une image")

        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=422, detail="Fichier trop grand (max 10 Mo)")

        return save_screenshot(
            post_id,
            content,
            file.filename or "screenshot.png",
            metrics={
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "views": views,
                "reach": reach,
                "impressions": impressions,
                "saves": saves,
            },
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Erreur upload_screenshot : %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/campaigns/{campaign_id}")
def get_campaign_engagement(campaign_id: str):
    """Retourne les métriques agrégées d'une campagne."""
    try:
        result = metrics_aggregator.get_campaign_engagement(campaign_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur get_campaign_engagement : %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/campaigns/{campaign_id}/revenue")
def set_campaign_revenue(campaign_id: str, data: CampaignRevenuePatch):
    """Met à jour le revenu attribué à une campagne."""
    try:
        now = datetime.now().isoformat()
        with _get_db() as conn:
            cursor = conn.execute(
                "UPDATE campaigns SET revenue_dza = ?, updated_at = ? WHERE campaign_id = ?",
                [data.revenue_dza, now, campaign_id],
            )
            conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return {
            "campaign_id": campaign_id,
            "revenue_dza": data.revenue_dza,
            "status": "updated",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erreur set_campaign_revenue : %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
