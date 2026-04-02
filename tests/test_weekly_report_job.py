"""Tests TDD pour le job hebdomadaire de recommandations."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402


def _config_module():
    """Retourne le module config courant, meme apres reload."""
    return importlib.import_module("config")


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Base SQLite temporaire pour le job hebdo."""
    from core.database import DatabaseManager

    db_path = tmp_path / "weekly_report.db"
    monkeypatch.setattr(_config_module(), "SQLITE_DB_PATH", db_path, raising=False)
    db = DatabaseManager(str(db_path))
    db.create_tables()
    db.close()
    return db_path


def _minimal_df() -> pd.DataFrame:
    """Construit un DataFrame annote minimal."""
    return pd.DataFrame(
        [
            {
                "text": "ramy disponible",
                "text_original": "ramy disponible",
                "sentiment_label": "positif",
                "confidence": 0.9,
                "channel": "google_maps",
                "aspect": "disponibilité",
                "timestamp": pd.Timestamp("2026-04-06T10:00:00"),
                "source_url": "https://example.test/1",
            }
        ]
    )


def test_run_weekly_report_job_retourne_none_si_desactive(tmp_db: Path) -> None:
    """Le job ne doit rien faire si le rapport hebdo est desactive."""
    from core.recommendation.weekly_report_job import run_weekly_recommendation_job

    result = run_weekly_recommendation_job(_minimal_df(), current_date=pd.Timestamp("2026-04-06"))

    assert result is None


def test_run_weekly_report_job_genere_et_persiste_une_recommandation(
    tmp_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le job hebdo doit generer une recommendation planifiee quand la config est active."""
    import core.recommendation.agent_client as agent_client
    import core.recommendation.context_builder as context_builder
    import core.recommendation.weekly_report_job as weekly_report_job
    from core.recommendation.recommendation_manager import (
        list_recommendations,
        update_client_agent_config,
    )

    update_client_agent_config(
        {
            "provider": "ollama_local",
            "model": "qwen2.5:14b",
            "weekly_report_enabled": True,
            "weekly_report_day": 1,
        },
        db_path=tmp_db,
    )
    monkeypatch.setattr(
        context_builder,
        "build_recommendation_context",
        lambda trigger_type, trigger_id, df_annotated, max_rag_chunks=8: {
            "trigger": {"type": trigger_type, "id": trigger_id},
            "estimated_tokens": 123,
            "client_profile": {"client_name": "Ramy"},
            "current_metrics": {},
            "active_alerts": [],
            "active_watchlists": [],
            "recent_campaigns": [],
            "rag_chunks": [],
        },
    )
    monkeypatch.setattr(
        agent_client,
        "generate_recommendations",
        lambda **kwargs: {
            "analysis_summary": "Resume hebdo",
            "recommendations": [{"id": "rec-1", "title": "Action", "priority": "high"}],
            "watchlist_priorities": ["Livraison Oran"],
            "confidence_score": 0.7,
            "data_quality_note": "ok",
            "provider_used": "ollama_local",
            "model_used": "qwen2.5:14b",
            "parse_success": True,
        },
    )
    monkeypatch.setattr(weekly_report_job, "send_email_notification", lambda **kwargs: None)
    monkeypatch.setattr(weekly_report_job, "send_slack_notification", lambda **kwargs: None)

    result = weekly_report_job.run_weekly_recommendation_job(
        _minimal_df(),
        current_date=pd.Timestamp("2026-04-06"),
    )

    assert result is not None
    assert result["trigger_type"] == "scheduled"
    recommendations = list_recommendations(db_path=tmp_db)
    assert len(recommendations) == 1
    assert recommendations[0]["trigger_type"] == "scheduled"


def test_run_weekly_report_job_declenche_notifications_si_cibles_definies(
    tmp_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le job doit appeler les canaux de delivery quand ils sont configures."""
    import core.recommendation.agent_client as agent_client
    import core.recommendation.context_builder as context_builder
    import core.recommendation.weekly_report_job as weekly_report_job
    from core.recommendation.recommendation_manager import update_client_agent_config

    update_client_agent_config(
        {
            "provider": "ollama_local",
            "model": "qwen2.5:14b",
            "weekly_report_enabled": True,
            "weekly_report_day": 1,
        },
        db_path=tmp_db,
    )
    monkeypatch.setattr(
        context_builder,
        "build_recommendation_context",
        lambda trigger_type, trigger_id, df_annotated, max_rag_chunks=8: {
            "trigger": {"type": trigger_type, "id": trigger_id},
            "estimated_tokens": 123,
            "client_profile": {"client_name": "Ramy"},
            "current_metrics": {},
            "active_alerts": [],
            "active_watchlists": [],
            "recent_campaigns": [],
            "rag_chunks": [],
        },
    )
    monkeypatch.setattr(
        agent_client,
        "generate_recommendations",
        lambda **kwargs: {
            "analysis_summary": "Resume hebdo",
            "recommendations": [{"id": "rec-1", "title": "Action", "priority": "high"}],
            "watchlist_priorities": ["Livraison Oran"],
            "confidence_score": 0.7,
            "data_quality_note": "ok",
            "provider_used": "ollama_local",
            "model_used": "qwen2.5:14b",
            "parse_success": True,
        },
    )
    sent_email = MagicMock()
    sent_slack = MagicMock()
    monkeypatch.setattr(weekly_report_job, "send_email_notification", sent_email)
    monkeypatch.setattr(weekly_report_job, "send_slack_notification", sent_slack)
    cfg = _config_module()
    monkeypatch.setattr(cfg, "WEEKLY_REPORT_EMAIL_TO", "team@example.com", raising=False)
    monkeypatch.setattr(
        cfg,
        "WEEKLY_REPORT_SLACK_WEBHOOK_REFERENCE",
        "env:TEST_SLACK_WEBHOOK",
        raising=False,
    )
    monkeypatch.setenv("TEST_SLACK_WEBHOOK", "https://hooks.slack.test/services/abc")

    weekly_report_job.run_weekly_recommendation_job(
        _minimal_df(),
        current_date=pd.Timestamp("2026-04-06"),
    )

    assert sent_email.called
    assert sent_slack.called


def test_run_weekly_report_job_lit_le_config_courant_apres_reload(
    tmp_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le job doit relire le config courant pour ses cibles de delivery."""
    import core.recommendation.agent_client as agent_client
    import core.recommendation.context_builder as context_builder
    import core.recommendation.weekly_report_job as weekly_report_job
    from core.recommendation.recommendation_manager import update_client_agent_config

    update_client_agent_config(
        {
            "provider": "ollama_local",
            "model": "qwen2.5:14b",
            "weekly_report_enabled": True,
            "weekly_report_day": 1,
        },
        db_path=tmp_db,
    )
    monkeypatch.setattr(
        context_builder,
        "build_recommendation_context",
        lambda trigger_type, trigger_id, df_annotated, max_rag_chunks=8: {
            "trigger": {"type": trigger_type, "id": trigger_id},
            "estimated_tokens": 123,
            "client_profile": {"client_name": "Ramy"},
            "current_metrics": {},
            "active_alerts": [],
            "active_watchlists": [],
            "recent_campaigns": [],
            "rag_chunks": [],
        },
    )
    monkeypatch.setattr(
        agent_client,
        "generate_recommendations",
        lambda **kwargs: {
            "analysis_summary": "Resume hebdo",
            "recommendations": [{"id": "rec-1", "title": "Action", "priority": "high"}],
            "watchlist_priorities": ["Livraison Oran"],
            "confidence_score": 0.7,
            "data_quality_note": "ok",
            "provider_used": "ollama_local",
            "model_used": "qwen2.5:14b",
            "parse_success": True,
        },
    )
    sent_email = MagicMock()
    sent_slack = MagicMock()
    monkeypatch.setattr(weekly_report_job, "send_email_notification", sent_email)
    monkeypatch.setattr(weekly_report_job, "send_slack_notification", sent_slack)

    if "config" in sys.modules:
        del sys.modules["config"]
    reloaded_config = importlib.import_module("config")
    monkeypatch.setattr(reloaded_config, "SQLITE_DB_PATH", tmp_db, raising=False)
    monkeypatch.setattr(reloaded_config, "WEEKLY_REPORT_EMAIL_TO", "team@example.com", raising=False)
    monkeypatch.setattr(
        reloaded_config,
        "WEEKLY_REPORT_SLACK_WEBHOOK_REFERENCE",
        "env:TEST_SLACK_WEBHOOK",
        raising=False,
    )
    monkeypatch.setenv("TEST_SLACK_WEBHOOK", "https://hooks.slack.test/services/abc")

    weekly_report_job.run_weekly_recommendation_job(
        _minimal_df(),
        current_date=pd.Timestamp("2026-04-06"),
    )

    assert sent_email.called
    assert sent_slack.called
