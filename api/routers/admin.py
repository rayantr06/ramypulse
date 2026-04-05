"""Routeur FastAPI pour l'administration métier RamyPulse (Phase 3).

Ce routeur permet à l'UI Admin de piloter les sources d'ingestion
(Facebook, Instagram, Google Maps, YouTube, Import), de déclencher
des synchronisations, et de vérifier la santé des connecteurs.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from config import DEFAULT_CLIENT_ID
from api.schemas import (
    AutomationCycleTrigger,
    NormalizationTrigger,
    SourceCreate,
    SourceSyncTrigger,
    SourceUpdate,
)
from core.ingestion.health_checker import compute_source_health
from core.ingestion.orchestrator import IngestionOrchestrator
from core.ingestion.scheduler import run_due_syncs
from core.ingestion.source_admin_service import SourceAdminService
from core.runtime.automation_runtime import run_automation_cycle

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/sources")
def create_source(payload: SourceCreate):
    """Crée une nouvelle source via l'orchestrateur."""
    try:
        orchestrator = IngestionOrchestrator()
        result = orchestrator.create_source(payload.model_dump(exclude_unset=True))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Erreur create_source: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
def list_sources(
    client_id: str = Query(DEFAULT_CLIENT_ID),
    platform: str | None = None,
    owner_type: str | None = None,
    status: str = "all",
):
    """Liste les sources avec leurs dernières métriques de santé/synchronisation."""
    try:
        service = SourceAdminService()
        return service.list_sources(
            client_id=client_id,
            platform=platform,
            owner_type=owner_type,
            status=status,
        )
    except Exception as e:
        logger.error("Erreur list_sources: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/{source_id}")
def get_source_trace(source_id: str, client_id: str = Query(DEFAULT_CLIENT_ID)):
    """Retourne la source détaillée, sa dernière synchro, et son dernier health snapshot."""
    try:
        service = SourceAdminService()
        return service.get_source_trace(source_id=source_id, client_id=client_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Source introuvable ou client mismtach")
    except Exception as e:
        logger.error("Erreur get_source_trace: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sources/{source_id}")
def update_source(source_id: str, payload: SourceUpdate):
    """Met à jour les paramètres administrables d'une source."""
    try:
        service = SourceAdminService()
        cid = payload.client_id or DEFAULT_CLIENT_ID
        return service.update_source(
            source_id=source_id,
            updates=payload.model_dump(exclude_unset=True, exclude={"client_id"}),
            client_id=cid,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Source introuvable")
    except Exception as e:
        logger.error("Erreur update_source: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/{source_id}/sync")
def trigger_source_sync(source_id: str, payload: SourceSyncTrigger):
    """Déclenche manuellement ou active un run de synchronisation pour la source."""
    try:
        orchestrator = IngestionOrchestrator()
        cid = payload.client_id or DEFAULT_CLIENT_ID
        return orchestrator.run_source_sync(
            source_id=source_id,
            manual_file_path=payload.manual_file_path,
            column_mapping=payload.column_mapping,
            run_mode=payload.run_mode,
            credentials=payload.credentials,
            client_id=cid,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Source introuvable")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Erreur trigger_source_sync: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/{source_id}/health")
def trigger_source_health(source_id: str, client_id: str | None = Query(DEFAULT_CLIENT_ID)):
    """Calcule immédiatement la santé d'une source et crée un snapshot."""
    try:
        return compute_source_health(source_id=source_id, client_id=client_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Source introuvable")
    except Exception as e:
        logger.error("Erreur trigger_source_health: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/{source_id}/runs")
def list_sync_runs(
    source_id: str,
    client_id: str | None = Query(DEFAULT_CLIENT_ID),
    limit: int = 50,
):
    """Affiche l'historique d'exécution (sync runs) pour la source."""
    try:
        service = SourceAdminService()
        return service.list_sync_runs(
            client_id=client_id,
            source_id=source_id,
            limit=limit,
        )
    except Exception as e:
        logger.error("Erreur list_sync_runs: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/{source_id}/snapshots")
def list_health_snapshots(
    source_id: str,
    client_id: str | None = Query(DEFAULT_CLIENT_ID),
    limit: int = 50,
):
    """Affiche l'historique des snapshots de santé pour la source."""
    try:
        service = SourceAdminService()
        return service.list_health_snapshots(
            client_id=client_id,
            source_id=source_id,
            limit=limit,
        )
    except Exception as e:
        logger.error("Erreur list_health_snapshots: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/normalization")
def trigger_normalization(payload: NormalizationTrigger):
    """Déclenche le pipeline de normalisation de façon asynchrone / batch."""
    try:
        orchestrator = IngestionOrchestrator()
        cid = payload.client_id or DEFAULT_CLIENT_ID
        return orchestrator.run_normalization_cycle(
            batch_size=payload.batch_size,
            client_id=cid,
        )
    except Exception as e:
        logger.error("Erreur trigger_normalization: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/tick")
def scheduler_tick(
    client_id: str = Query(DEFAULT_CLIENT_ID),
    now: str | None = Query(None),
):
    """Exécute les synchronisations dues avec priorité/fallback par coverage_key."""
    try:
        return run_due_syncs(client_id=client_id, now=now)
    except Exception as e:
        logger.error("Erreur scheduler_tick: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runtime/cycle")
def trigger_runtime_cycle(payload: AutomationCycleTrigger):
    """Exécute un cycle one-shot du runtime d'automatisation."""
    try:
        cid = payload.client_id or DEFAULT_CLIENT_ID
        return run_automation_cycle(
            client_id=cid,
            run_sync=payload.run_sync,
            run_normalization=payload.run_normalization,
            run_health=payload.run_health,
            run_alerts=payload.run_alerts,
            batch_size=payload.batch_size,
            now=payload.now,
        )
    except Exception as e:
        logger.error("Erreur trigger_runtime_cycle: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
