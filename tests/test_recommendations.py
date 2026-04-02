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
