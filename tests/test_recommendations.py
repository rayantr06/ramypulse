"""Tests TDD pour le module core/recommendation (Agent 2 — Wave 5.4).

Ordre d'exécution : pytest tests/test_recommendations.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────────────────────────────────────
# Task 1 — Config constants
# ─────────────────────────────────────────────────────────────────────────────

def test_config_anthropic_api_key_existe() -> None:
    """config.py doit exposer ANTHROPIC_API_KEY (str, peut être vide)."""
    from config import ANTHROPIC_API_KEY
    assert isinstance(ANTHROPIC_API_KEY, str)


def test_config_openai_api_key_existe() -> None:
    """config.py doit exposer OPENAI_API_KEY (str, peut être vide)."""
    from config import OPENAI_API_KEY
    assert isinstance(OPENAI_API_KEY, str)


def test_config_default_agent_provider_valide() -> None:
    """DEFAULT_AGENT_PROVIDER doit être l'un des trois providers supportés."""
    from config import DEFAULT_AGENT_PROVIDER
    assert DEFAULT_AGENT_PROVIDER in ("anthropic", "openai", "ollama_local")


def test_config_default_agent_model_est_string() -> None:
    """DEFAULT_AGENT_MODEL doit être une chaîne non vide."""
    from config import DEFAULT_AGENT_MODEL
    assert isinstance(DEFAULT_AGENT_MODEL, str)
    assert len(DEFAULT_AGENT_MODEL) > 0


def test_config_prompt_version_est_string() -> None:
    """RECOMMENDATION_AGENT_PROMPT_VERSION doit être une chaîne."""
    from config import RECOMMENDATION_AGENT_PROMPT_VERSION
    assert isinstance(RECOMMENDATION_AGENT_PROMPT_VERSION, str)


def test_config_annotated_parquet_path_existe() -> None:
    """ANNOTATED_PARQUET_PATH doit être un Path pointant vers processed/."""
    from config import ANNOTATED_PARQUET_PATH
    assert "annotated" in str(ANNOTATED_PARQUET_PATH)


def test_config_default_client_id_existe() -> None:
    """DEFAULT_CLIENT_ID doit être une chaîne non vide."""
    from config import DEFAULT_CLIENT_ID
    assert isinstance(DEFAULT_CLIENT_ID, str)
    assert len(DEFAULT_CLIENT_ID) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Task 2 — Database schema migration
# ─────────────────────────────────────────────────────────────────────────────

def test_recommendations_table_schema_wave5() -> None:
    """La table recommendations doit avoir le schema Wave 5 d'INTERFACES.md."""
    from core.database import DatabaseManager
    db = DatabaseManager(":memory:")
    db.create_tables()
    rows = db.connection.execute("PRAGMA table_info(recommendations)").fetchall()
    col_names = {row["name"] for row in rows}
    required = {
        "recommendation_id", "client_id", "trigger_type", "trigger_id",
        "alert_id", "analysis_summary", "recommendations",
        "watchlist_priorities", "confidence_score", "data_quality_note",
        "provider_used", "model_used", "context_tokens", "generation_ms",
        "status", "created_at",
    }
    assert required.issubset(col_names), f"Colonnes manquantes: {required - col_names}"
    db.close()


def test_recommendations_default_status_active() -> None:
    """Le statut par défaut d'une recommandation doit être 'active'."""
    import uuid
    from core.database import DatabaseManager
    db = DatabaseManager(":memory:")
    db.create_tables()
    rec_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO recommendations (recommendation_id, trigger_type, recommendations) VALUES (?, ?, ?)",
        (rec_id, "manual", "[]"),
    )
    db.commit()
    row = db.execute(
        "SELECT status FROM recommendations WHERE recommendation_id = ?", (rec_id,)
    ).fetchone()
    assert row["status"] == "active"
    db.close()


def test_migration_recommendations_renomme_ancien_schema() -> None:
    """Si la table recommendations a l'ancien schema Phase 1, elle doit être renommée."""
    import sqlite3
    from core.database import DatabaseManager, _migrate_recommendations_if_needed

    # Simuler l'ancien schema Phase 1
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE recommendations (
            recommendation_id TEXT PRIMARY KEY,
            alert_id TEXT,
            signal_type TEXT NOT NULL,
            problem TEXT NOT NULL,
            confidence TEXT NOT NULL,
            generation_mode TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # Appliquer la migration
    _migrate_recommendations_if_needed(conn)
    conn.commit()

    # Vérifier que l'ancienne table a été renommée
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "recommendations_legacy" in tables
    assert "recommendations" not in tables  # elle sera recréée par CREATE TABLE IF NOT EXISTS
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Task 3 — prompt_manager
# ─────────────────────────────────────────────────────────────────────────────

def test_get_system_prompt_retourne_string() -> None:
    """get_system_prompt() doit retourner une chaîne non vide."""
    from core.recommendation.prompt_manager import get_system_prompt
    prompt = get_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 100


def test_get_system_prompt_contient_format_json() -> None:
    """Le prompt système doit mentionner le format JSON attendu."""
    from core.recommendation.prompt_manager import get_system_prompt
    prompt = get_system_prompt()
    assert "analysis_summary" in prompt
    assert "recommendations" in prompt


def test_get_system_prompt_version_inconnue_leve_erreur() -> None:
    """Une version inconnue doit lever ValueError."""
    from core.recommendation.prompt_manager import get_system_prompt
    with pytest.raises(ValueError):
        get_system_prompt(version="99.0")


def test_get_system_prompt_version_explicite() -> None:
    """get_system_prompt(version='1.0') doit fonctionner."""
    from core.recommendation.prompt_manager import get_system_prompt
    assert isinstance(get_system_prompt(version="1.0"), str)


# ─────────────────────────────────────────────────────────────────────────────
# Task 4 — agent_client
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_json_response_json_valide() -> None:
    """Un JSON valide doit être parsé correctement."""
    from core.recommendation.agent_client import _parse_json_response
    raw = '{"analysis_summary": "test", "recommendations": [], "confidence_score": 0.8}'
    result = _parse_json_response(raw)
    assert result["analysis_summary"] == "test"
    assert result["confidence_score"] == 0.8


def test_parse_json_response_avec_fences_markdown() -> None:
    """Les fences ```json ... ``` doivent être nettoyées avant le parse."""
    from core.recommendation.agent_client import _parse_json_response
    raw = '```json\n{"analysis_summary": "ok", "recommendations": []}\n```'
    result = _parse_json_response(raw)
    assert result["analysis_summary"] == "ok"


def test_parse_json_response_fallback_json_invalide() -> None:
    """Un JSON invalide doit retourner une structure d'erreur avec parse_success=False."""
    from core.recommendation.agent_client import _parse_json_response
    raw = "Voici mes recommandations : bla bla bla (pas de JSON)"
    result = _parse_json_response(raw)
    assert result["parse_success"] is False
    assert result["recommendations"] == []
    assert result["confidence_score"] == 0.0


def test_parse_json_response_ajoute_parse_success_true() -> None:
    """Un JSON valide doit avoir parse_success=True dans le résultat."""
    from core.recommendation.agent_client import _parse_json_response
    raw = '{"analysis_summary": "x", "recommendations": [], "confidence_score": 0.5}'
    result = _parse_json_response(raw)
    assert result["parse_success"] is True


def test_generate_recommendations_structure_retour_ollama_mock() -> None:
    """generate_recommendations doit retourner les clés obligatoires (mock Ollama)."""
    from core.recommendation.agent_client import generate_recommendations

    mock_payload = {
        "analysis_summary": "NSS faible sur disponibilite.",
        "recommendations": [{"id": "rec_001", "priority": "high", "title": "Test"}],
        "watchlist_priorities": [],
        "confidence_score": 0.7,
        "data_quality_note": "Donnees suffisantes.",
    }

    with patch("core.recommendation.agent_client._call_ollama") as mock_call:
        mock_call.return_value = mock_payload
        result = generate_recommendations({"trigger": {"type": "manual"}}, provider="ollama_local")

    assert "recommendations" in result
    assert "analysis_summary" in result
    assert "provider_used" in result
    assert "model_used" in result
    assert "generation_ms" in result
    assert "parse_success" in result
    assert isinstance(result["recommendations"], list)


def test_generate_recommendations_provider_inconnu_leve_erreur() -> None:
    """Un provider non supporte doit lever ValueError."""
    from core.recommendation.agent_client import generate_recommendations
    with pytest.raises(ValueError, match="Provider non supporte"):
        generate_recommendations({}, provider="grok_local")


def test_cle_api_absente_des_logs(caplog) -> None:
    """La cle API ne doit jamais apparaitre dans les logs."""
    import logging
    from core.recommendation.agent_client import generate_recommendations

    fake_key = "sk-ant-fake-secret-key-12345"

    with patch("core.recommendation.agent_client._call_anthropic") as mock_call:
        mock_call.return_value = {
            "analysis_summary": "ok",
            "recommendations": [],
            "watchlist_priorities": [],
            "confidence_score": 0.5,
            "data_quality_note": "",
        }
        with caplog.at_level(logging.DEBUG):
            generate_recommendations(
                {"trigger": {"type": "manual"}},
                provider="anthropic",
                api_key=fake_key,
            )

    for record in caplog.records:
        assert fake_key not in record.getMessage(), f"Cle API trouvee dans les logs: {record.getMessage()}"


# ─────────────────────────────────────────────────────────────────────────────
# Task 5 — context_builder
# ─────────────────────────────────────────────────────────────────────────────

def _make_minimal_df() -> pd.DataFrame:
    """DataFrame annote minimal pour les tests."""
    import numpy as np
    n = 50
    rng = np.random.default_rng(42)
    sentiments = ["tres_positif", "positif", "neutre", "negatif", "tres_negatif"]
    # Utiliser les vrais labels du projet
    real_sentiments = ["tres_positif", "positif", "neutre", "negatif", "tres_negatif"]
    real_sentiments_fr = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]
    aspects = ["gout", "emballage", "prix", "disponibilite", "fraicheur"]
    real_aspects = ["goût", "emballage", "prix", "disponibilité", "fraîcheur"]
    channels = ["facebook", "google_maps", "audio", "youtube"]
    return pd.DataFrame({
        "text": [f"avis numero {i}" for i in range(n)],
        "text_original": [f"avis original {i}" for i in range(n)],
        "sentiment_label": [real_sentiments_fr[i % 5] for i in range(n)],
        "confidence": rng.uniform(0.6, 1.0, n),
        "channel": [channels[i % 4] for i in range(n)],
        "aspect": [real_aspects[i % 5] for i in range(n)],
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="D"),
        "source_url": [f"http://source/{i}" for i in range(n)],
    })


def test_build_context_retourne_cles_requises() -> None:
    """build_recommendation_context doit retourner toutes les cles INTERFACES.md."""
    from core.recommendation.context_builder import build_recommendation_context
    df = _make_minimal_df()
    ctx = build_recommendation_context("manual", None, df)
    required_keys = {
        "client_profile", "trigger", "current_metrics",
        "active_alerts", "active_watchlists", "recent_campaigns",
        "rag_chunks", "estimated_tokens",
    }
    assert required_keys.issubset(ctx.keys()), f"Cles manquantes: {required_keys - ctx.keys()}"


def test_build_context_trigger_type_preserve() -> None:
    """Le trigger_type passe doit etre preserve dans le contexte."""
    from core.recommendation.context_builder import build_recommendation_context
    df = _make_minimal_df()
    ctx = build_recommendation_context("alert_triggered", "some-alert-id", df)
    assert ctx["trigger"]["type"] == "alert_triggered"
    assert ctx["trigger"]["id"] == "some-alert-id"


def test_build_context_current_metrics_contient_nss() -> None:
    """current_metrics doit contenir nss_global, volume_total, nss_by_aspect."""
    from core.recommendation.context_builder import build_recommendation_context
    df = _make_minimal_df()
    ctx = build_recommendation_context("manual", None, df)
    metrics = ctx["current_metrics"]
    assert "nss_global" in metrics
    assert "volume_total" in metrics
    assert "nss_by_aspect" in metrics
    assert metrics["volume_total"] == 50


def test_build_context_df_vide_ne_crash_pas() -> None:
    """Un DataFrame vide ne doit pas faire planter le contexte."""
    from core.recommendation.context_builder import build_recommendation_context
    df = pd.DataFrame(columns=["text", "sentiment_label", "channel", "aspect", "timestamp", "source_url", "confidence", "text_original"])
    ctx = build_recommendation_context("manual", None, df)
    assert ctx["current_metrics"]["nss_global"] is None
    assert ctx["current_metrics"]["volume_total"] == 0


def test_build_context_estimated_tokens_positif() -> None:
    """estimated_tokens doit etre > 0 si le DataFrame n'est pas vide."""
    from core.recommendation.context_builder import build_recommendation_context
    df = _make_minimal_df()
    ctx = build_recommendation_context("manual", None, df)
    assert ctx["estimated_tokens"] > 0


def test_build_context_listes_sont_des_listes() -> None:
    """active_alerts, active_watchlists, recent_campaigns, rag_chunks sont des list."""
    from core.recommendation.context_builder import build_recommendation_context
    df = _make_minimal_df()
    ctx = build_recommendation_context("manual", None, df)
    assert isinstance(ctx["active_alerts"], list)
    assert isinstance(ctx["active_watchlists"], list)
    assert isinstance(ctx["recent_campaigns"], list)
    assert isinstance(ctx["rag_chunks"], list)


def test_build_context_nss_global_calcule_correctement() -> None:
    """Le NSS global doit etre calcule correctement sur un DataFrame connu."""
    from core.recommendation.context_builder import build_recommendation_context
    # 10 positifs, 10 tres_positifs, 10 negatifs, 10 tres_negatifs, 10 neutres → NSS = 0
    df = pd.DataFrame({
        "text": [f"t{i}" for i in range(50)],
        "text_original": [f"t{i}" for i in range(50)],
        "sentiment_label": (
            ["très_positif"] * 10 + ["positif"] * 10 +
            ["neutre"] * 10 + ["négatif"] * 10 + ["très_négatif"] * 10
        ),
        "confidence": [0.9] * 50,
        "channel": ["facebook"] * 50,
        "aspect": ["goût"] * 50,
        "timestamp": pd.date_range("2026-01-01", periods=50, freq="D"),
        "source_url": ["http://x"] * 50,
    })
    ctx = build_recommendation_context("manual", None, df)
    nss = ctx["current_metrics"]["nss_global"]
    assert nss == 0.0, f"NSS attendu 0.0, obtenu {nss}"
