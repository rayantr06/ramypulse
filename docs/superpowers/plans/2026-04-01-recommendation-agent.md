# Recommendation Agent (Agent 2 / Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `core/recommendation/` module + `pages/08_recommendations.py` for RamyPulse Wave 5.4 — multi-provider AI recommendation agent that assembles structured context from DataFrame + SQLite and produces actionable marketing recommendations.

**Architecture:** A synchronous pipeline: `context_builder` assembles a rich dict (metrics, alerts, campaigns, RAG chunks) → `agent_client` calls Anthropic/OpenAI/Ollama with a versioned system prompt → `recommendation_manager` persists to SQLite. The Streamlit page wires these together with a configurable UI.

**Tech Stack:** Python 3.10+, Streamlit 1.35+, pandas, requests, SQLite (via `core/database.py`), existing `core/rag/Retriever` (optional — degrades gracefully if FAISS index absent).

---

## Pre-flight: Key constraints to remember

- NEVER call `sqlite3` directly — always use `_get_connection()` pattern (Section 7 of INTERFACES.md)
- `target_aspects`, `target_regions`, `keywords`, `recommendations`, `watchlist_priorities` → always JSON-serialized in DB, always deserialized in return values
- Use `logging`, not `print()`
- Docstrings in French
- No `st.experimental_rerun()` — use `st.rerun()`
- `st.cache_data(ttl=300)` on every data-loading function
- The `recommendations` column in the DB stores a JSON-serialized list — do not confuse with the table name

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `config.py` | Modify | Add Wave 5 constants (API keys, agent config, paths) |
| `core/database.py` | Modify | Migrate `recommendations` table to INTERFACES.md schema |
| `core/recommendation/__init__.py` | Create | Empty package marker |
| `core/recommendation/prompt_manager.py` | Create | Versioned system prompt |
| `core/recommendation/agent_client.py` | Create | Multi-provider LLM client + robust JSON parse |
| `core/recommendation/context_builder.py` | Create | Assembles context from DataFrame + SQLite + RAG |
| `core/recommendation/recommendation_manager.py` | Create | SQLite CRUD for recommendations table |
| `pages/08_recommendations.py` | Create | Streamlit Recommendation Center |
| `tests/test_recommendations.py` | Create | Full TDD test suite |

---

## Task 1: Branch setup + config.py Wave 5 constants

**Files:**
- Modify: `config.py`
- Create: `tests/test_recommendations.py` (first stubs)

- [ ] **Step 1.1 — Create the working branch**

```bash
cd g:/ramypulse
git checkout -b agent2/p2-recommendations main
```

- [ ] **Step 1.2 — Write failing tests for config constants**

Create `tests/test_recommendations.py`:

```python
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
```

- [ ] **Step 1.3 — Run tests to verify they fail**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_config_anthropic_api_key_existe tests/test_recommendations.py::test_config_openai_api_key_existe tests/test_recommendations.py::test_config_default_agent_provider_valide -v
```

Expected: `ImportError` or `AssertionError` — constants don't exist yet.

- [ ] **Step 1.4 — Add Wave 5 constants to config.py**

Append after `APIFY_API_KEY` in `config.py`:

```python
# ---------------------------------------------------------------------------
# Wave 5 — AI Recommendation Agent
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
"""Clé API Anthropic pour le Recommendation Agent. Optionnelle si provider = ollama_local."""

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
"""Clé API OpenAI pour le Recommendation Agent. Optionnelle si provider = ollama_local."""

DEFAULT_AGENT_PROVIDER: str = os.getenv("AGENT_PROVIDER", "ollama_local")
"""Provider LLM actif : anthropic | openai | ollama_local."""

DEFAULT_AGENT_MODEL: str = os.getenv("AGENT_MODEL", "qwen2.5:14b")
"""Modèle par défaut selon le provider sélectionné."""

RECOMMENDATION_AGENT_PROMPT_VERSION: str = "1.0"
"""Version active du prompt système de l'agent de recommandations."""

# ---------------------------------------------------------------------------
# Wave 5 — Campaign Intelligence (partagé avec Agent 1)
# ---------------------------------------------------------------------------

DEFAULT_PRE_WINDOW_DAYS: int = 14
"""Fenêtre pré-campagne en jours (baseline)."""

DEFAULT_POST_WINDOW_DAYS: int = 14
"""Fenêtre post-campagne en jours (mesure d'impact)."""

MIN_SIGNALS_FOR_ATTRIBUTION: int = 20
"""Volume minimum de signaux pour qu'une attribution campagne soit fiable."""

# ---------------------------------------------------------------------------
# Wave 5 — Alertes (partagé avec Agent 3)
# ---------------------------------------------------------------------------

SOURCE_HEALTH_THRESHOLD: int = 60
"""Score en dessous duquel une alerte source_health est créée."""

ALERT_DETECTION_INTERVAL_MINUTES: int = 30
"""Intervalle entre deux cycles de détection d'alertes."""

# ---------------------------------------------------------------------------
# Chemins données annotées (partagé Wave 5)
# ---------------------------------------------------------------------------

ANNOTATED_PARQUET_PATH: Path = PROCESSED_DATA_DIR / "annotated.parquet"
"""Chemin vers annotated.parquet — lecture seule pour tous les modules Wave 5."""

CLEAN_PARQUET_PATH: Path = PROCESSED_DATA_DIR / "clean.parquet"
"""Chemin vers clean.parquet."""

BM25_METADATA_PATH: Path = EMBEDDINGS_DIR / "bm25_metadata.json"
"""Chemin vers les métadonnées BM25 de l'index FAISS."""
```

- [ ] **Step 1.5 — Run tests to verify they pass**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_config_anthropic_api_key_existe tests/test_recommendations.py::test_config_openai_api_key_existe tests/test_recommendations.py::test_config_default_agent_provider_valide tests/test_recommendations.py::test_config_default_agent_model_est_string tests/test_recommendations.py::test_config_prompt_version_est_string tests/test_recommendations.py::test_config_annotated_parquet_path_existe -v
```

Expected: all PASS.

- [ ] **Step 1.6 — Commit**

```bash
git add config.py tests/test_recommendations.py
git commit -m "feat(config): add Wave 5 constants for Recommendation Agent"
```

---

## Task 2: database.py — migrate recommendations to INTERFACES.md schema

**Files:**
- Modify: `core/database.py`

> **Context:** The existing `recommendations` table (Phase 1) has columns: `recommendation_id, alert_id, signal_type, problem, ...`. INTERFACES.md Wave 5 schema needs: `recommendation_id, client_id, trigger_type, trigger_id, alert_id, analysis_summary, recommendations, watchlist_priorities, confidence_score, data_quality_note, provider_used, model_used, context_tokens, generation_ms, status, created_at`.

- [ ] **Step 2.1 — Write failing test for new schema**

Add to `tests/test_recommendations.py`:

```python
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
    from core.database import DatabaseManager
    import uuid
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
```

- [ ] **Step 2.2 — Run to verify failure**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_recommendations_table_schema_wave5 -v
```

Expected: FAIL — columns `trigger_type`, `client_id`, etc. are absent.

- [ ] **Step 2.3 — Update `_SCHEMA_STATEMENTS["recommendations"]` in core/database.py**

In `core/database.py`, find the `"recommendations"` key in `_SCHEMA_STATEMENTS` and replace its value:

```python
    "recommendations": """
        CREATE TABLE IF NOT EXISTS recommendations (
            recommendation_id    TEXT PRIMARY KEY,
            client_id            TEXT DEFAULT 'ramy_client_001',
            trigger_type         TEXT,
            trigger_id           TEXT,
            alert_id             TEXT,
            analysis_summary     TEXT,
            recommendations      TEXT DEFAULT '[]',
            watchlist_priorities TEXT DEFAULT '[]',
            confidence_score     REAL,
            data_quality_note    TEXT,
            provider_used        TEXT,
            model_used           TEXT,
            context_tokens       INTEGER,
            generation_ms        INTEGER,
            status               TEXT DEFAULT 'active',
            created_at           TEXT
        )
    """,
```

- [ ] **Step 2.4 — Add `_migrate_recommendations_if_needed` function in core/database.py**

Add after `_migrate_competitors_if_needed` (before the `DatabaseManager` class):

```python
def _migrate_recommendations_if_needed(connection: sqlite3.Connection) -> None:
    """Migre la table recommendations du schema Phase 1 vers le schema Wave 5.

    Si la table n'existe pas, la fonction n'intervient pas (CREATE IF NOT EXISTS s'en charge).
    Si la table possède déjà trigger_type (schema Wave 5), aucune action.
    Sinon, renomme la table legacy et crée la nouvelle.
    """
    if not _table_exists(connection, "recommendations"):
        return
    columns = _column_definitions(connection, "recommendations")
    if "trigger_type" in columns:
        return
    logger.info("Migration SQLite : realignement de la table recommendations vers schema Wave 5")
    connection.execute("ALTER TABLE recommendations RENAME TO recommendations_legacy")
```

- [ ] **Step 2.5 — Call migration in `create_tables` method**

In `DatabaseManager.create_tables()`, add the call before the loop:

```python
    def create_tables(self) -> None:
        """Cree l'ensemble des tables SQLite du PRD et migre le legacy."""
        connection = self.get_connection()
        connection.execute("PRAGMA foreign_keys = OFF")
        try:
            _migrate_products_if_needed(connection)
            _migrate_wilayas_if_needed(connection)
            _migrate_competitors_if_needed(connection)
            _migrate_recommendations_if_needed(connection)   # ← ADD THIS LINE

            for statement in _SCHEMA_STATEMENTS.values():
                connection.execute(statement)
            connection.commit()
        finally:
            connection.execute("PRAGMA foreign_keys = ON")
```

- [ ] **Step 2.6 — Run all database tests to verify no regressions**

```bash
cd g:/ramypulse && python -m pytest tests/test_database.py tests/test_recommendations.py::test_recommendations_table_schema_wave5 tests/test_recommendations.py::test_recommendations_default_status_active -v
```

Expected: all PASS.

- [ ] **Step 2.7 — Commit**

```bash
git add core/database.py tests/test_recommendations.py
git commit -m "feat(db): migrate recommendations table to Wave 5 schema (INTERFACES.md)"
```

---

## Task 3: `core/recommendation/__init__.py` + `prompt_manager.py`

**Files:**
- Create: `core/recommendation/__init__.py`
- Create: `core/recommendation/prompt_manager.py`

- [ ] **Step 3.1 — Write failing tests for prompt_manager**

Add to `tests/test_recommendations.py`:

```python
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
```

- [ ] **Step 3.2 — Run to verify failure**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_get_system_prompt_retourne_string -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3.3 — Create `core/recommendation/__init__.py`**

```python
"""Module de recommandations marketing AI — Wave 5.4 RamyPulse."""
```

- [ ] **Step 3.4 — Create `core/recommendation/prompt_manager.py`**

```python
"""Gestionnaire de prompts versionnés pour l'agent de recommandations.

Chaque version du prompt système est une constante nommée SYSTEM_PROMPT_Vx_y.
La fonction get_system_prompt() retourne la version demandée ou lève ValueError.
"""

import logging

from config import RECOMMENDATION_AGENT_PROMPT_VERSION

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt système v1.0
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_V1_0 = """Tu es un expert en stratégie marketing digital pour le marché algérien, spécialisé dans l'industrie agroalimentaire et les boissons.

Tu vas recevoir des données structurées issues d'une plateforme d'analyse de sentiment (RamyPulse) pour la marque Ramy.

Ton travail est de générer des recommandations marketing concrètes et actionnables basées UNIQUEMENT sur ces données.

RÈGLES STRICTES :
- Ne génère JAMAIS de recommandations sans base dans les données fournies
- Chaque recommandation doit être liée à un signal, une métrique, ou une alerte spécifique
- Adapte toujours le ton et le style au canal et au segment cible
- Le marché algérien a ses spécificités culturelles : respecte-les (Darija, références locales, contexte socio-culturel)
- Si les données sont insuffisantes pour une recommandation fiable, indique-le explicitement

FORMAT DE RÉPONSE :
Réponds UNIQUEMENT en JSON valide. Aucun texte avant ou après le JSON.

Structure obligatoire :
{
  "analysis_summary": "string — 2-3 phrases résumant la situation détectée",
  "recommendations": [
    {
      "id": "rec_001",
      "priority": "critical|high|medium|low",
      "type": "influencer_campaign|paid_ad|content_organic|community_response|product_action|distribution_action",
      "title": "string — titre court et actionnable",
      "rationale": "string — pourquoi cette recommandation, liée aux données",
      "target_platform": "instagram|facebook|youtube|tiktok|offline|multi_platform",
      "target_segment": "string — ex: gen_z_18_25, famille_algéroise, hommes_actifs",
      "target_regions": ["string"],
      "target_aspects": ["string"],
      "timing": {
        "urgency": "immediate|within_week|within_month",
        "best_moment": "string — ex: weekend matin, période ramadan, après-match"
      },
      "influencer_profile": {
        "tier": "nano|micro|macro|mega|none",
        "niche": "string — ex: lifestyle algérien, food content, sport",
        "tone": "string — ex: authentique darija, humoristique, aspirationnel",
        "engagement_focus": "string"
      },
      "content": {
        "hooks": ["string", "string", "string"],
        "script_outline": "string — 3-5 phrases décrivant la structure du contenu",
        "key_messages": ["string"],
        "visual_direction": "string — direction créative visuelle",
        "call_to_action": "string"
      },
      "kpi_to_track": ["string"],
      "data_basis": "string — référence explicite aux données RamyPulse ayant motivé cette recommandation"
    }
  ],
  "watchlist_priorities": ["string — watchlists à surveiller en priorité après ces actions"],
  "confidence_score": 0.0,
  "data_quality_note": "string — qualité et quantité des données disponibles pour cette analyse"
}"""


_REGISTRY: dict[str, str] = {
    "1.0": _SYSTEM_PROMPT_V1_0,
}


def get_system_prompt(version: str = RECOMMENDATION_AGENT_PROMPT_VERSION) -> str:
    """Retourne le prompt système pour la version demandée.

    Args:
        version: Version du prompt (ex: '1.0'). Défaut = RECOMMENDATION_AGENT_PROMPT_VERSION.

    Returns:
        Chaîne du prompt système.

    Raises:
        ValueError: Si la version n'est pas connue.
    """
    if version not in _REGISTRY:
        raise ValueError(
            f"Version de prompt inconnue : {version!r}. "
            f"Versions disponibles : {sorted(_REGISTRY)}"
        )
    logger.debug("Chargement du prompt système v%s", version)
    return _REGISTRY[version]
```

- [ ] **Step 3.5 — Run tests to verify pass**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_get_system_prompt_retourne_string tests/test_recommendations.py::test_get_system_prompt_contient_format_json tests/test_recommendations.py::test_get_system_prompt_version_inconnue_leve_erreur tests/test_recommendations.py::test_get_system_prompt_version_explicite -v
```

Expected: all PASS.

- [ ] **Step 3.6 — Commit**

```bash
git add core/recommendation/__init__.py core/recommendation/prompt_manager.py tests/test_recommendations.py
git commit -m "feat(reco): prompt_manager v1.0 avec system prompt algérien"
```

---

## Task 4: `core/recommendation/agent_client.py`

**Files:**
- Create: `core/recommendation/agent_client.py`

> **Note:** Uses `requests` (sync). The PRD uses async/httpx but RamyPulse is Streamlit (sync). `requests` is in requirements.txt.

- [ ] **Step 4.1 — Write failing tests for agent_client**

Add to `tests/test_recommendations.py`:

```python
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
        "analysis_summary": "NSS faible sur disponibilité.",
        "recommendations": [{"id": "rec_001", "priority": "high", "title": "Test"}],
        "watchlist_priorities": [],
        "confidence_score": 0.7,
        "data_quality_note": "Données suffisantes.",
    }

    with patch("core.recommendation.agent_client._call_ollama") as mock_call:
        mock_call.return_value = mock_payload
        result = generate_recommendations({"trigger": {"type": "manual"}}, provider="ollama_local")

    assert "recommendations" in result
    assert "analysis_summary" in result
    assert "provider_used" in result
    assert "model_used" in result
    assert "generation_ms" in result
    assert isinstance(result["recommendations"], list)


def test_generate_recommendations_provider_inconnu_leve_erreur() -> None:
    """Un provider non supporté doit lever ValueError."""
    from core.recommendation.agent_client import generate_recommendations
    with pytest.raises(ValueError, match="Provider non supporté"):
        generate_recommendations({}, provider="grok_local")
```

- [ ] **Step 4.2 — Run to verify failure**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_parse_json_response_json_valide -v
```

Expected: `ImportError`.

- [ ] **Step 4.3 — Create `core/recommendation/agent_client.py`**

```python
"""Client LLM multi-provider pour la génération de recommandations marketing.

Supporte : anthropic, openai, ollama_local.
Utilise requests (synchrone) compatible avec Streamlit.
Parse JSON robuste avec fallback si le LLM retourne du texte libre.
"""

import json
import logging
import re
import time

import requests

from config import (
    ANTHROPIC_API_KEY,
    DEFAULT_AGENT_MODEL,
    DEFAULT_AGENT_PROVIDER,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
    RECOMMENDATION_AGENT_PROMPT_VERSION,
)
from core.recommendation.prompt_manager import get_system_prompt

logger = logging.getLogger(__name__)

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_ANTHROPIC_VERSION_HEADER = "2023-06-01"
_DEFAULT_MAX_TOKENS = 2000
_TIMEOUT_SECONDS = 120


# ---------------------------------------------------------------------------
# Parse JSON robuste
# ---------------------------------------------------------------------------

def _parse_json_response(raw_text: str) -> dict:
    """Parse la réponse brute du LLM en JSON avec fallback robuste.

    Tente d'abord un parse direct. Si échec, nettoie les fences markdown.
    Si toujours invalide, retourne une structure d'erreur exploitable.

    Args:
        raw_text: Texte brut retourné par le LLM.

    Returns:
        Dict avec les clés du schema de recommandation + parse_success (bool).
    """
    def _enrich(data: dict) -> dict:
        data.setdefault("parse_success", True)
        return data

    # Tentative 1 : parse direct
    try:
        return _enrich(json.loads(raw_text))
    except json.JSONDecodeError:
        pass

    # Tentative 2 : nettoyer les fences ```json ... ```
    cleaned = re.sub(r"```json\s*|\s*```", "", raw_text, flags=re.DOTALL).strip()
    try:
        return _enrich(json.loads(cleaned))
    except json.JSONDecodeError:
        pass

    # Tentative 3 : extraire le premier bloc JSON entre { et }
    match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
    if match:
        try:
            return _enrich(json.loads(match.group()))
        except json.JSONDecodeError:
            pass

    # Fallback : structure d'erreur exploitable
    logger.warning("Impossible de parser la réponse LLM en JSON. Retour du fallback.")
    return {
        "analysis_summary": "Erreur de parsing de la réponse agent.",
        "recommendations": [],
        "watchlist_priorities": [],
        "confidence_score": 0.0,
        "data_quality_note": f"JSON parse error — raw_response_prefix: {raw_text[:200]}",
        "parse_success": False,
    }


# ---------------------------------------------------------------------------
# Construction du prompt utilisateur
# ---------------------------------------------------------------------------

def _build_user_prompt(context: dict) -> str:
    """Construit le prompt utilisateur à partir du contexte assemblé.

    Args:
        context: Dict retourné par build_recommendation_context().

    Returns:
        Chaîne de prompt utilisateur formatée.
    """
    client_name = context.get("client_profile", {}).get("client_name", "Ramy")
    trigger = context.get("trigger", {})
    trigger_type = trigger.get("type", "manual")
    trigger_id = trigger.get("id") or "global"

    active_alerts = context.get("active_alerts", [])
    active_watchlists = context.get("active_watchlists", [])
    recent_campaigns = context.get("recent_campaigns", [])
    rag_chunks = context.get("rag_chunks", [])
    metrics = context.get("current_metrics", {})

    return (
        f"Voici les données de la plateforme RamyPulse pour cette analyse :\n\n"
        f"CLIENT : {client_name}\n"
        f"DÉCLENCHEUR : {trigger_type} — {trigger_id}\n\n"
        f"=== MÉTRIQUES ACTUELLES ===\n"
        f"{json.dumps(metrics, ensure_ascii=False, indent=2)}\n\n"
        f"=== ALERTES ACTIVES ({len(active_alerts)} alertes non résolues) ===\n"
        f"{json.dumps(active_alerts, ensure_ascii=False, indent=2)}\n\n"
        f"=== WATCHLISTS ACTIVES ===\n"
        f"{json.dumps(active_watchlists, ensure_ascii=False, indent=2)}\n\n"
        f"=== CAMPAGNES RÉCENTES ===\n"
        f"{json.dumps(recent_campaigns, ensure_ascii=False, indent=2)}\n\n"
        f"=== EXTRAITS SOURCES PERTINENTS ===\n"
        f"{json.dumps(rag_chunks, ensure_ascii=False, indent=2)}\n\n"
        "Génère les recommandations marketing les plus actionnables pour cette situation.\n"
        "Réponds UNIQUEMENT en JSON selon le format défini."
    )


# ---------------------------------------------------------------------------
# Appels providers
# ---------------------------------------------------------------------------

def _call_anthropic(api_key: str, model: str, user_prompt: str, system_prompt: str) -> dict:
    """Appelle l'API Anthropic Messages et parse la réponse JSON.

    Args:
        api_key: Clé API Anthropic.
        model: Nom du modèle (ex: 'claude-sonnet-4-6').
        user_prompt: Prompt utilisateur avec le contexte.
        system_prompt: Prompt système versionné.

    Returns:
        Dict parsé de la réponse LLM.

    Raises:
        requests.HTTPError: Si l'API retourne une erreur HTTP.
    """
    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION_HEADER,
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": _DEFAULT_MAX_TOKENS,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    logger.info("Appel Anthropic API — modèle : %s", model)
    response = requests.post(_ANTHROPIC_API_URL, headers=headers, json=payload, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    raw_text = data["content"][0]["text"]
    return _parse_json_response(raw_text)


def _call_openai(api_key: str, model: str, user_prompt: str, system_prompt: str) -> dict:
    """Appelle l'API OpenAI Chat Completions et parse la réponse JSON.

    Args:
        api_key: Clé API OpenAI.
        model: Nom du modèle (ex: 'gpt-4o').
        user_prompt: Prompt utilisateur.
        system_prompt: Prompt système.

    Returns:
        Dict parsé de la réponse LLM.

    Raises:
        requests.HTTPError: Si l'API retourne une erreur HTTP.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": _DEFAULT_MAX_TOKENS,
    }
    logger.info("Appel OpenAI API — modèle : %s", model)
    response = requests.post(_OPENAI_API_URL, headers=headers, json=payload, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    raw_text = data["choices"][0]["message"]["content"]
    return _parse_json_response(raw_text)


def _call_ollama(model: str, user_prompt: str, system_prompt: str) -> dict:
    """Appelle Ollama local et parse la réponse JSON.

    Args:
        model: Nom du modèle Ollama (ex: 'qwen2.5:14b').
        user_prompt: Prompt utilisateur.
        system_prompt: Prompt système.

    Returns:
        Dict parsé de la réponse LLM.

    Raises:
        requests.HTTPError: Si Ollama retourne une erreur HTTP.
    """
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
    }
    logger.info("Appel Ollama local — modèle : %s", model)
    response = requests.post(url, json=payload, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    raw_text = data["message"]["content"]
    return _parse_json_response(raw_text)


# ---------------------------------------------------------------------------
# Interface publique
# ---------------------------------------------------------------------------

def generate_recommendations(
    context: dict,
    provider: str = DEFAULT_AGENT_PROVIDER,
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Appelle le LLM sélectionné et retourne les recommandations parsées.

    Mesure le temps de génération. Enrichit le résultat avec les métadonnées
    du provider et du modèle utilisés.

    Args:
        context: Dict retourné par build_recommendation_context().
        provider: 'anthropic' | 'openai' | 'ollama_local'.
        model: Nom du modèle. None = utiliser le défaut du provider.
        api_key: Clé API. None = lire depuis config/env.

    Returns:
        Dict avec clés : analysis_summary, recommendations (list), watchlist_priorities,
        confidence_score, data_quality_note, provider_used, model_used,
        generation_ms, parse_success.

    Raises:
        ValueError: Si le provider n'est pas supporté.
    """
    system_prompt = get_system_prompt()
    user_prompt = _build_user_prompt(context)

    t_start = time.monotonic()

    if provider == "anthropic":
        resolved_model = model or "claude-sonnet-4-6"
        resolved_key = api_key or ANTHROPIC_API_KEY
        result = _call_anthropic(resolved_key, resolved_model, user_prompt, system_prompt)
    elif provider == "openai":
        resolved_model = model or "gpt-4o"
        resolved_key = api_key or OPENAI_API_KEY
        result = _call_openai(resolved_key, resolved_model, user_prompt, system_prompt)
    elif provider == "ollama_local":
        resolved_model = model or DEFAULT_AGENT_MODEL
        result = _call_ollama(resolved_model, user_prompt, system_prompt)
    else:
        raise ValueError(f"Provider non supporté : {provider!r}. Valeurs valides : anthropic, openai, ollama_local")

    generation_ms = int((time.monotonic() - t_start) * 1000)

    result["provider_used"] = provider
    result["model_used"] = resolved_model
    result["generation_ms"] = generation_ms
    result.setdefault("parse_success", True)
    result.setdefault("recommendations", [])
    result.setdefault("watchlist_priorities", [])
    result.setdefault("confidence_score", 0.0)
    result.setdefault("data_quality_note", "")
    result.setdefault("analysis_summary", "")

    logger.info(
        "Génération complète — provider=%s modèle=%s durée=%dms parse_success=%s",
        provider, resolved_model, generation_ms, result["parse_success"],
    )
    return result
```

- [ ] **Step 4.4 — Run tests to verify pass**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_parse_json_response_json_valide tests/test_recommendations.py::test_parse_json_response_avec_fences_markdown tests/test_recommendations.py::test_parse_json_response_fallback_json_invalide tests/test_recommendations.py::test_parse_json_response_ajoute_parse_success_true tests/test_recommendations.py::test_generate_recommendations_structure_retour_ollama_mock tests/test_recommendations.py::test_generate_recommendations_provider_inconnu_leve_erreur -v
```

Expected: all PASS.

- [ ] **Step 4.5 — Commit**

```bash
git add core/recommendation/agent_client.py tests/test_recommendations.py
git commit -m "feat(reco): agent_client multi-provider avec parse JSON robuste"
```

---

## Task 5: `core/recommendation/context_builder.py`

**Files:**
- Create: `core/recommendation/context_builder.py`

> **Design decision:** Agent 1 (campaigns) and Agent 3 (alerts/watchlists) modules may not exist yet. All imports from those modules are wrapped in try/except — context_builder degrades gracefully, returning empty lists when those modules are absent. RAG is also optional (if FAISS index not built, returns []).

- [ ] **Step 5.1 — Write failing tests for context_builder**

Add to `tests/test_recommendations.py`:

```python
# ─────────────────────────────────────────────────────────────────────────────
# Task 5 — context_builder
# ─────────────────────────────────────────────────────────────────────────────

def _make_minimal_df() -> pd.DataFrame:
    """DataFrame annoté minimal pour les tests."""
    import numpy as np
    n = 50
    rng = np.random.default_rng(42)
    sentiments = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]
    aspects = ["goût", "emballage", "prix", "disponibilité", "fraîcheur"]
    channels = ["facebook", "google_maps", "audio", "youtube"]
    return pd.DataFrame({
        "text": [f"avis numéro {i}" for i in range(n)],
        "text_original": [f"avis original {i}" for i in range(n)],
        "sentiment_label": [sentiments[i % 5] for i in range(n)],
        "confidence": rng.uniform(0.6, 1.0, n),
        "channel": [channels[i % 4] for i in range(n)],
        "aspect": [aspects[i % 5] for i in range(n)],
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="D"),
        "source_url": [f"http://source/{i}" for i in range(n)],
        "wilaya": ["oran"] * 25 + ["alger"] * 25,
        "product": ["ramy_citron"] * n,
    })


def test_build_context_retourne_cles_requises() -> None:
    """build_recommendation_context doit retourner toutes les clés INTERFACES.md."""
    from core.recommendation.context_builder import build_recommendation_context
    df = _make_minimal_df()
    ctx = build_recommendation_context("manual", None, df)
    required_keys = {
        "client_profile", "trigger", "current_metrics",
        "active_alerts", "active_watchlists", "recent_campaigns",
        "rag_chunks", "estimated_tokens",
    }
    assert required_keys.issubset(ctx.keys()), f"Clés manquantes: {required_keys - ctx.keys()}"


def test_build_context_trigger_type_preservé() -> None:
    """Le trigger_type passé doit être préservé dans le contexte."""
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
    df = pd.DataFrame(columns=["text", "sentiment_label", "channel", "aspect", "timestamp", "source_url", "confidence"])
    ctx = build_recommendation_context("manual", None, df)
    assert ctx["current_metrics"]["nss_global"] is None
    assert ctx["current_metrics"]["volume_total"] == 0


def test_build_context_estimated_tokens_positif() -> None:
    """estimated_tokens doit être > 0 si le DataFrame n'est pas vide."""
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
```

- [ ] **Step 5.2 — Run to verify failure**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_build_context_retourne_cles_requises -v
```

Expected: `ImportError`.

- [ ] **Step 5.3 — Create `core/recommendation/context_builder.py`**

```python
"""Assembleur de contexte pour l'agent de recommandations.

Construit le payload complet (métriques, alertes, campagnes, RAG chunks)
à partir du DataFrame annoté + SQLite, avant d'appeler le LLM.
Dégrade gracieusement si les modules d'autres agents ne sont pas encore disponibles.
"""

import json
import logging
from typing import Any

import pandas as pd

from config import ASPECT_LIST, DEFAULT_CLIENT_ID, FAISS_INDEX_PATH, SENTIMENT_LABELS

logger = logging.getLogger(__name__)

# Importations optionnelles — modules des autres agents (Agent 1, Agent 3)
try:
    from core.campaigns.campaign_manager import list_campaigns as _list_campaigns
    _HAS_CAMPAIGNS = True
except ImportError:
    _HAS_CAMPAIGNS = False
    logger.debug("core.campaigns non disponible — recent_campaigns sera vide")

try:
    from core.alerts.alert_manager import list_alerts as _list_alerts
    _HAS_ALERTS = True
except ImportError:
    _HAS_ALERTS = False
    logger.debug("core.alerts non disponible — active_alerts sera vide")

try:
    from core.watchlists.watchlist_manager import list_watchlists as _list_watchlists
    _HAS_WATCHLISTS = True
except ImportError:
    _HAS_WATCHLISTS = False
    logger.debug("core.watchlists non disponible — active_watchlists sera vide")

# Importation optionnelle du RAG
try:
    from core.rag.embedder import Embedder
    from core.rag.retriever import Retriever
    from core.rag.vector_store import VectorStore
    _HAS_RAG_DEPS = True
except ImportError:
    _HAS_RAG_DEPS = False
    logger.debug("core.rag non disponible — rag_chunks sera vide")


# ---------------------------------------------------------------------------
# Calcul NSS inline (évite la dépendance circulaire avec nss_calculator)
# ---------------------------------------------------------------------------

_POSITIVE_LABELS = {"très_positif", "positif"}
_NEGATIVE_LABELS = {"négatif", "très_négatif"}


def _compute_nss(df: pd.DataFrame) -> float | None:
    """Calcule le Net Sentiment Score sur un DataFrame de signaux.

    Formule : (positifs + très_positifs - négatifs - très_négatifs) / total × 100.

    Args:
        df: DataFrame avec colonne 'sentiment_label'.

    Returns:
        Score NSS entre -100 et 100, ou None si le DataFrame est vide.
    """
    if df.empty:
        return None
    total = len(df)
    positives = df["sentiment_label"].isin(_POSITIVE_LABELS).sum()
    negatives = df["sentiment_label"].isin(_NEGATIVE_LABELS).sum()
    return round((positives - negatives) / total * 100, 2)


def _compute_nss_by_aspect(df: pd.DataFrame) -> dict[str, float | None]:
    """Calcule le NSS par aspect.

    Args:
        df: DataFrame avec colonnes 'sentiment_label' et 'aspect'.

    Returns:
        Dict {aspect: nss_value}. Les aspects sans données ont None.
    """
    result: dict[str, float | None] = {}
    for aspect in ASPECT_LIST:
        sub = df[df["aspect"] == aspect]
        result[aspect] = _compute_nss(sub)
    return result


def _compute_nss_by_channel(df: pd.DataFrame) -> dict[str, float | None]:
    """Calcule le NSS par canal de collecte.

    Args:
        df: DataFrame avec colonnes 'sentiment_label' et 'channel'.

    Returns:
        Dict {channel: nss_value}.
    """
    result: dict[str, float | None] = {}
    for channel in df["channel"].dropna().unique():
        sub = df[df["channel"] == channel]
        result[str(channel)] = _compute_nss(sub)
    return result


def _top_negative_aspects(df: pd.DataFrame, n: int = 3) -> list[str]:
    """Retourne les n aspects avec le NSS le plus faible.

    Args:
        df: DataFrame annoté.
        n: Nombre d'aspects à retourner.

    Returns:
        Liste des noms d'aspects, triés du NSS le plus bas au plus élevé.
    """
    nss_by_aspect = _compute_nss_by_aspect(df)
    scored = [(asp, nss) for asp, nss in nss_by_aspect.items() if nss is not None]
    scored.sort(key=lambda x: x[1])
    return [asp for asp, _ in scored[:n]]


# ---------------------------------------------------------------------------
# Chargement RAG optionnel
# ---------------------------------------------------------------------------

def _load_retriever() -> Any | None:
    """Tente de charger le Retriever FAISS + BM25.

    Returns:
        Retriever si l'index existe et que les dépendances sont disponibles.
        None sinon (dégrade silencieusement).
    """
    if not _HAS_RAG_DEPS:
        return None
    try:
        vs = VectorStore()
        vs.load(str(FAISS_INDEX_PATH))
        if not vs.metadata:
            logger.debug("Index FAISS vide — rag_chunks sera vide")
            return None
        embedder = Embedder()
        return Retriever(vs, embedder)
    except Exception as exc:
        logger.debug("Impossible de charger le RAG : %s", exc)
        return None


# ---------------------------------------------------------------------------
# Estimation de tokens (approximation 1 token ≈ 4 caractères)
# ---------------------------------------------------------------------------

def _estimate_tokens(context: dict) -> int:
    """Estime le nombre de tokens du contexte JSON serialisé.

    Args:
        context: Dict du contexte assemblé.

    Returns:
        Estimation entière (approximative).
    """
    try:
        serialized = json.dumps(context, ensure_ascii=False)
        return max(1, len(serialized) // 4)
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Interface publique
# ---------------------------------------------------------------------------

def build_recommendation_context(
    trigger_type: str,
    trigger_id: str | None,
    df_annotated: pd.DataFrame,
    max_rag_chunks: int = 8,
) -> dict:
    """Assemble le contexte complet pour l'agent de recommandations.

    Lit les alertes actives, watchlists actives et campagnes récentes depuis
    SQLite (via les managers des autres agents si disponibles). Calcule les
    métriques NSS directement depuis le DataFrame. Récupère les chunks RAG
    les plus pertinents selon le déclencheur.

    Args:
        trigger_type: 'manual' | 'alert_triggered' | 'scheduled'.
        trigger_id: ID de l'alerte, watchlist ou campagne déclencheuse. None si global.
        df_annotated: DataFrame annoté chargé depuis annotated.parquet.
        max_rag_chunks: Nombre maximum de chunks RAG à inclure.

    Returns:
        Dict avec clés : client_profile, trigger, current_metrics,
        active_alerts, active_watchlists, recent_campaigns, rag_chunks,
        estimated_tokens.
    """
    context: dict = {}

    # 1. Profil client (statique pour PoC mono-client)
    context["client_profile"] = {
        "client_name": "Ramy",
        "industry": "Agroalimentaire algérien",
        "main_products": ["Ramy Citron", "Ramy Orange", "Ramy Fraise", "Ramy Multivitamines"],
        "active_regions": ["alger", "oran", "constantine", "annaba", "tlemcen", "sétif"],
    }

    # 2. Déclencheur
    context["trigger"] = {"type": trigger_type, "id": trigger_id}

    # 3. Métriques courantes depuis le DataFrame
    nss_global = _compute_nss(df_annotated)
    nss_by_aspect = _compute_nss_by_aspect(df_annotated)
    nss_by_channel = _compute_nss_by_channel(df_annotated)
    top_neg = _top_negative_aspects(df_annotated) if not df_annotated.empty else []

    context["current_metrics"] = {
        "nss_global": nss_global,
        "nss_by_aspect": nss_by_aspect,
        "nss_by_channel": nss_by_channel,
        "volume_total": len(df_annotated),
        "top_negative_aspects": top_neg,
    }

    # 4. Alertes actives (Agent 3 — optionnel)
    active_alerts: list[dict] = []
    if _HAS_ALERTS:
        try:
            all_alerts = _list_alerts(limit=100)
            active = [
                a for a in all_alerts
                if a.get("status") in ("new", "acknowledged", "investigating")
            ]
            # Trier par sévérité : critical > high > medium > low
            _sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            active.sort(key=lambda a: _sev_order.get(a.get("severity", "low"), 4))
            active_alerts = active[:5]
        except Exception as exc:
            logger.warning("Erreur lors du chargement des alertes : %s", exc)

    context["active_alerts"] = active_alerts

    # 5. Watchlists actives (Agent 3 — optionnel)
    active_watchlists: list[dict] = []
    if _HAS_WATCHLISTS:
        try:
            active_watchlists = _list_watchlists(is_active=True)[:5]
        except Exception as exc:
            logger.warning("Erreur lors du chargement des watchlists : %s", exc)

    context["active_watchlists"] = active_watchlists

    # 6. Campagnes récentes (Agent 1 — optionnel)
    recent_campaigns: list[dict] = []
    if _HAS_CAMPAIGNS:
        try:
            recent_campaigns = _list_campaigns(limit=3)
        except Exception as exc:
            logger.warning("Erreur lors du chargement des campagnes : %s", exc)

    context["recent_campaigns"] = recent_campaigns

    # 7. Chunks RAG pertinents (optionnel)
    rag_chunks: list[dict] = []
    retriever = _load_retriever()
    if retriever is not None:
        try:
            query = _build_rag_query(trigger_type, trigger_id, context["current_metrics"])
            raw_chunks = retriever.search(query, top_k=max_rag_chunks)
            rag_chunks = [
                {
                    "text": c["text"],
                    "channel": c["channel"],
                    "timestamp": c["timestamp"],
                }
                for c in raw_chunks
            ]
        except Exception as exc:
            logger.warning("Erreur lors de la récupération RAG : %s", exc)

    context["rag_chunks"] = rag_chunks

    # 8. Estimation de la taille du contexte
    context["estimated_tokens"] = _estimate_tokens(context)

    logger.info(
        "Contexte assemblé — trigger=%s alertes=%d watchlists=%d campagnes=%d chunks=%d tokens≈%d",
        trigger_type,
        len(active_alerts),
        len(active_watchlists),
        len(recent_campaigns),
        len(rag_chunks),
        context["estimated_tokens"],
    )
    return context


def _build_rag_query(
    trigger_type: str,
    trigger_id: str | None,
    metrics: dict,
) -> str:
    """Construit la requête RAG à partir du déclencheur et des métriques.

    Args:
        trigger_type: Type de déclencheur.
        trigger_id: ID de déclencheur.
        metrics: Dict des métriques courantes.

    Returns:
        Requête textuelle pour la recherche RAG.
    """
    top_negative = metrics.get("top_negative_aspects", [])
    base = "recommandations marketing Ramy"
    if top_negative:
        aspects_str = " ".join(top_negative[:2])
        base += f" {aspects_str} problèmes clients"
    if trigger_type == "alert_triggered" and trigger_id:
        base += f" alerte critique"
    return base
```

- [ ] **Step 5.4 — Run tests to verify pass**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_build_context_retourne_cles_requises tests/test_recommendations.py::test_build_context_trigger_type_preservé tests/test_recommendations.py::test_build_context_current_metrics_contient_nss tests/test_recommendations.py::test_build_context_df_vide_ne_crash_pas tests/test_recommendations.py::test_build_context_estimated_tokens_positif tests/test_recommendations.py::test_build_context_listes_sont_des_listes -v
```

Expected: all PASS.

- [ ] **Step 5.5 — Commit**

```bash
git add core/recommendation/context_builder.py tests/test_recommendations.py
git commit -m "feat(reco): context_builder avec degradation gracieuse agents 1&3"
```

---

## Task 6: `core/recommendation/recommendation_manager.py`

**Files:**
- Create: `core/recommendation/recommendation_manager.py`

- [ ] **Step 6.1 — Write failing tests**

Add to `tests/test_recommendations.py`:

```python
# ─────────────────────────────────────────────────────────────────────────────
# Task 6 — recommendation_manager
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    """Base SQLite temporaire avec schema Wave 5 pour les tests."""
    from core.database import DatabaseManager
    db_path = tmp_path / "test_reco.db"
    db = DatabaseManager(str(db_path))
    db.create_tables()
    db.close()
    return str(db_path)


def test_save_recommendation_retourne_uuid(tmp_db) -> None:
    """save_recommendation doit retourner un UUID string non vide."""
    from core.recommendation.recommendation_manager import save_recommendation
    rec_id = save_recommendation(
        db_path=tmp_db,
        result={
            "analysis_summary": "Baisse NSS disponibilité.",
            "recommendations": [{"id": "rec_001", "priority": "high", "title": "Test"}],
            "watchlist_priorities": ["NSS Oran"],
            "confidence_score": 0.8,
            "data_quality_note": "Données ok.",
            "provider_used": "ollama_local",
            "model_used": "qwen2.5:14b",
            "generation_ms": 3200,
            "parse_success": True,
        },
        trigger_type="manual",
        trigger_id=None,
    )
    assert isinstance(rec_id, str)
    assert len(rec_id) == 36  # UUID v4 format


def test_list_recommendations_retourne_liste(tmp_db) -> None:
    """list_recommendations doit retourner une liste (vide ou non)."""
    from core.recommendation.recommendation_manager import list_recommendations
    result = list_recommendations(db_path=tmp_db)
    assert isinstance(result, list)


def test_save_and_list_roundtrip(tmp_db) -> None:
    """Une recommandation sauvée doit apparaître dans list_recommendations."""
    from core.recommendation.recommendation_manager import save_recommendation, list_recommendations
    save_recommendation(
        db_path=tmp_db,
        result={
            "analysis_summary": "Test.",
            "recommendations": [],
            "watchlist_priorities": [],
            "confidence_score": 0.5,
            "data_quality_note": "",
            "provider_used": "ollama_local",
            "model_used": "llama3.2:3b",
            "generation_ms": 1000,
            "parse_success": True,
        },
        trigger_type="manual",
        trigger_id=None,
    )
    results = list_recommendations(db_path=tmp_db)
    assert len(results) == 1
    assert results[0]["trigger_type"] == "manual"
    assert isinstance(results[0]["recommendations"], list)


def test_get_recommendation_retourne_dict(tmp_db) -> None:
    """get_recommendation doit retourner le dict complet ou None si absent."""
    from core.recommendation.recommendation_manager import save_recommendation, get_recommendation
    rec_id = save_recommendation(
        db_path=tmp_db,
        result={
            "analysis_summary": "OK.",
            "recommendations": [{"id": "rec_001"}],
            "watchlist_priorities": ["w1"],
            "confidence_score": 0.9,
            "data_quality_note": "good",
            "provider_used": "anthropic",
            "model_used": "claude-sonnet-4-6",
            "generation_ms": 5000,
            "parse_success": True,
        },
        trigger_type="alert_triggered",
        trigger_id="alert-123",
    )
    rec = get_recommendation(rec_id, db_path=tmp_db)
    assert rec is not None
    assert rec["recommendation_id"] == rec_id
    assert isinstance(rec["recommendations"], list)
    assert rec["recommendations"][0]["id"] == "rec_001"
    assert get_recommendation("non-existent-id", db_path=tmp_db) is None


def test_update_recommendation_status(tmp_db) -> None:
    """update_recommendation_status doit modifier le statut correctement."""
    from core.recommendation.recommendation_manager import (
        save_recommendation, get_recommendation, update_recommendation_status,
    )
    rec_id = save_recommendation(
        db_path=tmp_db,
        result={"analysis_summary": "", "recommendations": [], "watchlist_priorities": [],
                "confidence_score": 0.0, "data_quality_note": "", "provider_used": "ollama_local",
                "model_used": "test", "generation_ms": 0, "parse_success": True},
        trigger_type="manual",
        trigger_id=None,
    )
    assert update_recommendation_status(rec_id, "archived", db_path=tmp_db) is True
    rec = get_recommendation(rec_id, db_path=tmp_db)
    assert rec["status"] == "archived"
```

- [ ] **Step 6.2 — Run to verify failure**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_save_recommendation_retourne_uuid -v
```

Expected: `ImportError`.

- [ ] **Step 6.3 — Create `core/recommendation/recommendation_manager.py`**

```python
"""Gestionnaire SQLite pour les recommandations générées par l'agent AI.

CRUD complet sur la table `recommendations` selon le schema INTERFACES.md.
Utilise le pattern de connexion de la Section 7 (core/database.py).
Jamais d'accès direct à sqlite3 — toujours via _get_connection().
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from config import DEFAULT_CLIENT_ID, SQLITE_DB_PATH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers SQLite (Section 7 de INTERFACES.md)
# ---------------------------------------------------------------------------

def _get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Ouvre une connexion SQLite avec row_factory.

    Args:
        db_path: Chemin vers la base. None = utiliser SQLITE_DB_PATH.

    Returns:
        Connexion SQLite avec sqlite3.Row factory.
    """
    resolved = str(db_path) if db_path else str(SQLITE_DB_PATH)
    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    return conn


def _serialize_list(value: list | None) -> str:
    """Sérialise une liste en JSON string pour SQLite."""
    return json.dumps(value or [], ensure_ascii=False)


def _deserialize_list(value: str | None) -> list:
    """Désérialise une JSON string en liste."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _new_id() -> str:
    """Génère un UUID string."""
    return str(uuid.uuid4())


def _now() -> str:
    """Timestamp ISO courant."""
    return datetime.now().isoformat()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def save_recommendation(
    result: dict,
    trigger_type: str,
    trigger_id: str | None,
    client_id: str = DEFAULT_CLIENT_ID,
    db_path: str | Path | None = None,
) -> str:
    """Persiste une recommandation générée par l'agent AI.

    Args:
        result: Dict retourné par generate_recommendations().
        trigger_type: 'manual' | 'alert_triggered' | 'scheduled'.
        trigger_id: ID de l'alerte/watchlist/campagne déclencheuse. None si global.
        client_id: Identifiant client. Défaut : DEFAULT_CLIENT_ID.
        db_path: Chemin DB optionnel (pour les tests).

    Returns:
        recommendation_id (UUID string).
    """
    rec_id = _new_id()
    sql = """
        INSERT INTO recommendations (
            recommendation_id, client_id, trigger_type, trigger_id, alert_id,
            analysis_summary, recommendations, watchlist_priorities,
            confidence_score, data_quality_note, provider_used, model_used,
            context_tokens, generation_ms, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        rec_id,
        client_id,
        trigger_type,
        trigger_id,
        result.get("alert_id"),
        result.get("analysis_summary", ""),
        _serialize_list(result.get("recommendations", [])),
        _serialize_list(result.get("watchlist_priorities", [])),
        result.get("confidence_score"),
        result.get("data_quality_note", ""),
        result.get("provider_used", ""),
        result.get("model_used", ""),
        result.get("context_tokens"),
        result.get("generation_ms"),
        "active",
        _now(),
    )
    conn = _get_connection(db_path)
    try:
        conn.execute(sql, params)
        conn.commit()
        logger.info("Recommandation sauvegardée : %s (trigger=%s)", rec_id, trigger_type)
    except sqlite3.Error as exc:
        logger.error("Erreur lors de la sauvegarde de la recommandation : %s", exc)
        raise
    finally:
        conn.close()
    return rec_id


def list_recommendations(
    status: str | None = None,
    limit: int = 20,
    db_path: str | Path | None = None,
) -> list[dict]:
    """Retourne la liste des recommandations, triées par date décroissante.

    Args:
        status: Filtre sur le statut ('active', 'archived', 'dismissed'). None = tous.
        limit: Nombre maximum de résultats.
        db_path: Chemin DB optionnel (pour les tests).

    Returns:
        Liste de dicts avec recommendations et watchlist_priorities désérialisés.
    """
    if status:
        sql = "SELECT * FROM recommendations WHERE status = ? ORDER BY created_at DESC LIMIT ?"
        params: tuple = (status, limit)
    else:
        sql = "SELECT * FROM recommendations ORDER BY created_at DESC LIMIT ?"
        params = (limit,)

    conn = _get_connection(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def get_recommendation(
    recommendation_id: str,
    db_path: str | Path | None = None,
) -> dict | None:
    """Retourne une recommandation par son ID.

    Args:
        recommendation_id: UUID string de la recommandation.
        db_path: Chemin DB optionnel.

    Returns:
        Dict avec champs désérialisés, ou None si non trouvé.
    """
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM recommendations WHERE recommendation_id = ?",
            (recommendation_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def update_recommendation_status(
    recommendation_id: str,
    status: str,
    db_path: str | Path | None = None,
) -> bool:
    """Met à jour le statut d'une recommandation.

    Args:
        recommendation_id: UUID string.
        status: 'active' | 'archived' | 'dismissed'.
        db_path: Chemin DB optionnel.

    Returns:
        True si la mise à jour a affecté une ligne, False sinon.
    """
    valid_statuses = ("active", "archived", "dismissed")
    if status not in valid_statuses:
        raise ValueError(f"Statut invalide : {status!r}. Valeurs valides : {valid_statuses}")

    conn = _get_connection(db_path)
    try:
        cursor = conn.execute(
            "UPDATE recommendations SET status = ? WHERE recommendation_id = ?",
            (status, recommendation_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Erreur lors de la mise à jour du statut : %s", exc)
        return False
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Helper interne — conversion Row → dict
# ---------------------------------------------------------------------------

def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convertit un sqlite3.Row en dict avec désérialisation des champs JSON.

    Args:
        row: Ligne SQLite.

    Returns:
        Dict avec recommendations et watchlist_priorities sous forme de list.
    """
    d = dict(row)
    d["recommendations"] = _deserialize_list(d.get("recommendations"))
    d["watchlist_priorities"] = _deserialize_list(d.get("watchlist_priorities"))
    return d
```

- [ ] **Step 6.4 — Run tests to verify pass**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py::test_save_recommendation_retourne_uuid tests/test_recommendations.py::test_list_recommendations_retourne_liste tests/test_recommendations.py::test_save_and_list_roundtrip tests/test_recommendations.py::test_get_recommendation_retourne_dict tests/test_recommendations.py::test_update_recommendation_status -v
```

Expected: all PASS.

- [ ] **Step 6.5 — Commit**

```bash
git add core/recommendation/recommendation_manager.py tests/test_recommendations.py
git commit -m "feat(reco): recommendation_manager CRUD SQLite Wave 5"
```

---

## Task 7: `pages/08_recommendations.py`

**Files:**
- Create: `pages/08_recommendations.py`

> **No tests for Streamlit pages** (requires browser rendering). Visual verification only.

- [ ] **Step 7.1 — Create `pages/08_recommendations.py`**

```python
"""Recommendation Center — Page Streamlit 08.

Génère des recommandations marketing actionnables via un LLM externe
(Anthropic, OpenAI, ou Ollama local) à partir du contexte RamyPulse.

Sections :
  1. Générer maintenant (déclencheur + périmètre + bouton)
  2. Recommandations actives (cartes expandables)
  3. Historique des recommandations (tableau)
  4. Configuration de l'agent (provider, modèle, clé API)
"""

import logging

import pandas as pd
import streamlit as st

from config import (
    ANNOTATED_PARQUET_PATH,
    DEFAULT_AGENT_MODEL,
    DEFAULT_AGENT_PROVIDER,
    DEFAULT_CLIENT_ID,
)

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Recommendation Center — RamyPulse", layout="wide")

# ─── Chargement des données ───────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Charge annotated.parquet avec TTL 300 secondes.

    Returns:
        DataFrame annoté, ou DataFrame vide si le fichier est absent.
    """
    try:
        df = pd.read_parquet(ANNOTATED_PARQUET_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["wilaya"] = df["wilaya"].fillna("").str.lower().str.strip()
        df["aspect"] = df["aspect"].fillna("")
        return df
    except FileNotFoundError:
        return pd.DataFrame()


df = load_data()

# ─── Header ──────────────────────────────────────────────────────────────────

st.title("🤖 Recommendation Center")
st.caption("Génère des recommandations marketing actionnables à partir des données RamyPulse.")

if df.empty:
    st.warning("⚠️ Données non disponibles. Lancez d'abord `scripts/run_demo_05.py`")
    st.stop()

# ─── Session state initialization ────────────────────────────────────────────

if "reco_provider" not in st.session_state:
    st.session_state["reco_provider"] = DEFAULT_AGENT_PROVIDER
if "reco_model" not in st.session_state:
    st.session_state["reco_model"] = DEFAULT_AGENT_MODEL
if "reco_api_key" not in st.session_state:
    st.session_state["reco_api_key"] = ""


# ─── Section 1 — Générer maintenant ──────────────────────────────────────────

st.header("1. Générer des recommandations")

col_trigger, col_scope = st.columns([1, 2])

with col_trigger:
    trigger_type = st.selectbox(
        "Déclencheur",
        options=["manual", "alert_triggered", "scheduled"],
        format_func=lambda x: {
            "manual": "🖱️ Manuel (global)",
            "alert_triggered": "🚨 Depuis une alerte",
            "scheduled": "📅 Rapport planifié",
        }.get(x, x),
    )

trigger_id: str | None = None
with col_scope:
    if trigger_type == "alert_triggered":
        trigger_id_input = st.text_input(
            "ID de l'alerte déclencheuse",
            placeholder="UUID de l'alerte...",
        )
        trigger_id = trigger_id_input.strip() or None
    elif trigger_type == "scheduled":
        st.info("📅 Mode planifié — utilise toutes les watchlists actives comme contexte.")

generate_btn = st.button("🚀 Générer les recommandations", type="primary")

if generate_btn:
    provider = st.session_state["reco_provider"]
    model = st.session_state["reco_model"] or None
    api_key = st.session_state["reco_api_key"] or None

    with st.spinner("⏳ Analyse en cours — assemblage du contexte, appel à l'agent..."):
        try:
            from core.recommendation.agent_client import generate_recommendations
            from core.recommendation.context_builder import build_recommendation_context
            from core.recommendation.recommendation_manager import save_recommendation

            context = build_recommendation_context(
                trigger_type=trigger_type,
                trigger_id=trigger_id,
                df_annotated=df,
                max_rag_chunks=8,
            )

            result = generate_recommendations(
                context=context,
                provider=provider,
                model=model,
                api_key=api_key,
            )

            rec_id = save_recommendation(
                result=result,
                trigger_type=trigger_type,
                trigger_id=trigger_id,
            )

            if result.get("parse_success", True):
                st.success(
                    f"✅ {len(result.get('recommendations', []))} recommandation(s) générée(s) "
                    f"en {result.get('generation_ms', 0) / 1000:.1f}s — "
                    f"confiance : {result.get('confidence_score', 0):.0%}"
                )
            else:
                st.warning(
                    "⚠️ Le modèle n'a pas retourné un JSON valide. "
                    "Résultats partiels affichés ci-dessous."
                )

            load_data.clear()
            st.rerun()

        except Exception as exc:
            st.error(f"❌ Erreur lors de la génération : {exc}")
            logger.exception("Erreur generate_recommendations")

st.divider()

# ─── Section 2 — Recommandations actives ─────────────────────────────────────

st.header("2. Recommandations actives")

try:
    from core.recommendation.recommendation_manager import (
        list_recommendations,
        update_recommendation_status,
    )

    active_recos = list_recommendations(status="active", limit=10)

    if not active_recos:
        st.info("Aucune recommandation active. Générez-en une depuis la section 1.")
    else:
        for reco_row in active_recos:
            recs = reco_row.get("recommendations", [])
            summary = reco_row.get("analysis_summary", "")
            provider_label = reco_row.get("provider_used", "?")
            created_at = reco_row.get("created_at", "")[:19]
            confidence = reco_row.get("confidence_score") or 0.0
            rec_id = reco_row["recommendation_id"]

            header_label = (
                f"🤖 {len(recs)} reco(s) · "
                f"confiance {confidence:.0%} · "
                f"provider: {provider_label} · "
                f"généré le {created_at}"
            )

            with st.expander(header_label, expanded=False):
                if summary:
                    st.markdown(f"**Résumé de situation :** {summary}")
                    st.divider()

                for rec in recs:
                    priority = rec.get("priority", "medium")
                    priority_icon = {
                        "critical": "🔴", "high": "🟠",
                        "medium": "🟡", "low": "🟢",
                    }.get(priority, "⚪")

                    st.markdown(f"#### {priority_icon} [{priority.upper()}] {rec.get('title', '')}")

                    col_why, col_target = st.columns(2)
                    with col_why:
                        st.markdown(f"**Pourquoi :** {rec.get('rationale', '')}")
                        st.markdown(
                            f"**Données :** _{rec.get('data_basis', 'N/A')}_"
                        )
                    with col_target:
                        st.markdown(
                            f"**Cible :** {rec.get('target_segment', 'N/A')} · "
                            f"{rec.get('target_platform', 'N/A')}"
                        )
                        regions = rec.get("target_regions", [])
                        if regions:
                            st.markdown(f"**Régions :** {', '.join(regions)}")

                    # Profil influenceur
                    inf = rec.get("influencer_profile", {})
                    if inf and inf.get("tier") != "none":
                        st.markdown(
                            f"**Influenceur :** Tier {inf.get('tier', '?')} · "
                            f"Niche : {inf.get('niche', '?')} · "
                            f"Ton : {inf.get('tone', '?')}"
                        )

                    # Hooks créatifs
                    content = rec.get("content", {})
                    hooks = content.get("hooks", [])
                    if hooks:
                        st.markdown("**Hooks créatifs :**")
                        for hook in hooks:
                            st.markdown(f"- {hook}")

                    # Script outline
                    script = content.get("script_outline", "")
                    if script:
                        st.markdown(f"**Outline script :** {script}")

                    # Timing
                    timing = rec.get("timing", {})
                    if timing:
                        st.markdown(
                            f"**Timing :** {timing.get('urgency', '?')} — "
                            f"{timing.get('best_moment', '')}"
                        )

                    # KPIs
                    kpis = rec.get("kpi_to_track", [])
                    if kpis:
                        st.markdown(f"**KPIs :** {' · '.join(kpis)}")

                    st.divider()

                # Actions sur la recommandation
                col_a1, col_a2, col_a3 = st.columns(3)
                with col_a1:
                    if st.button("📥 Archiver", key=f"archive_{rec_id}"):
                        try:
                            update_recommendation_status(rec_id, "archived")
                            st.success("Archivé.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erreur : {exc}")
                with col_a2:
                    if st.button("🚫 Rejeter", key=f"dismiss_{rec_id}"):
                        try:
                            update_recommendation_status(rec_id, "dismissed")
                            st.success("Rejeté.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erreur : {exc}")
                with col_a3:
                    # Lien vers création de campagne (Agent 1 — optionnel)
                    st.caption(f"ID : `{rec_id[:8]}...`")

except Exception as exc:
    st.error(f"❌ Impossible de charger les recommandations : {exc}")
    logger.exception("Erreur chargement recommandations actives")

st.divider()

# ─── Section 3 — Historique ──────────────────────────────────────────────────

st.header("3. Historique")

try:
    from core.recommendation.recommendation_manager import list_recommendations

    all_recos = list_recommendations(limit=50)

    if not all_recos:
        st.info("Aucune recommandation dans l'historique.")
    else:
        import pandas as pd as pd_hist  # noqa: F811 — alias pour éviter confusion

        rows = []
        for r in all_recos:
            rows.append({
                "Date": r.get("created_at", "")[:19],
                "Déclencheur": r.get("trigger_type", ""),
                "# Reco": len(r.get("recommendations", [])),
                "Confiance": f"{(r.get('confidence_score') or 0):.0%}",
                "Provider": r.get("provider_used", ""),
                "Modèle": r.get("model_used", ""),
                "Statut": r.get("status", ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

except Exception as exc:
    st.error(f"❌ Erreur chargement historique : {exc}")

st.divider()

# ─── Section 4 — Configuration ───────────────────────────────────────────────

st.header("4. Configuration de l'agent")

with st.form("agent_config_form"):
    col_prov, col_mod = st.columns(2)

    with col_prov:
        selected_provider = st.selectbox(
            "Provider LLM",
            options=["ollama_local", "anthropic", "openai"],
            index=["ollama_local", "anthropic", "openai"].index(
                st.session_state["reco_provider"]
            ),
            format_func=lambda x: {
                "ollama_local": "🏠 Ollama local",
                "anthropic": "🟣 Anthropic (Claude)",
                "openai": "🟢 OpenAI (GPT)",
            }.get(x, x),
        )

    with col_mod:
        model_defaults = {
            "ollama_local": "qwen2.5:14b",
            "anthropic": "claude-sonnet-4-6",
            "openai": "gpt-4o",
        }
        selected_model = st.text_input(
            "Modèle",
            value=st.session_state.get("reco_model") or model_defaults.get(selected_provider, ""),
            placeholder=model_defaults.get(selected_provider, ""),
        )

    if selected_provider in ("anthropic", "openai"):
        api_key_input = st.text_input(
            f"Clé API {selected_provider.capitalize()}",
            value=st.session_state.get("reco_api_key", ""),
            type="password",
            help="La clé n'est jamais affichée en clair ni stockée en base.",
        )
    else:
        api_key_input = ""
        st.info(f"🏠 Ollama local — URL : `{DEFAULT_AGENT_PROVIDER}` — aucune clé requise.")

    submitted = st.form_submit_button("💾 Sauvegarder la configuration")
    if submitted:
        st.session_state["reco_provider"] = selected_provider
        st.session_state["reco_model"] = selected_model
        st.session_state["reco_api_key"] = api_key_input
        st.success(
            f"✅ Configuration sauvegardée : {selected_provider} / {selected_model or 'défaut'}"
        )
```

- [ ] **Step 7.2 — Fix the double import alias bug in section 3**

In `pages/08_recommendations.py`, the line `import pandas as pd as pd_hist` is invalid Python. Replace the entire Section 3 block with:

```python
# ─── Section 3 — Historique ──────────────────────────────────────────────────

st.header("3. Historique")

try:
    from core.recommendation.recommendation_manager import list_recommendations as _list_all

    all_recos = _list_all(limit=50)

    if not all_recos:
        st.info("Aucune recommandation dans l'historique.")
    else:
        hist_rows = []
        for r in all_recos:
            hist_rows.append({
                "Date": r.get("created_at", "")[:19],
                "Déclencheur": r.get("trigger_type", ""),
                "# Reco": len(r.get("recommendations", [])),
                "Confiance": f"{(r.get('confidence_score') or 0):.0%}",
                "Provider": r.get("provider_used", ""),
                "Modèle": r.get("model_used", ""),
                "Statut": r.get("status", ""),
            })
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True)

except Exception as exc:
    st.error(f"❌ Erreur chargement historique : {exc}")

st.divider()
```

> Write the whole file correctly from the start — see the corrected version in Step 7.3.

- [ ] **Step 7.3 — Syntax check**

```bash
cd g:/ramypulse && python -c "import ast; ast.parse(open('pages/08_recommendations.py').read()); print('OK — pas de SyntaxError')"
```

Expected: `OK — pas de SyntaxError`

- [ ] **Step 7.4 — Commit**

```bash
git add pages/08_recommendations.py
git commit -m "feat(pages): 08_recommendations Streamlit Recommendation Center"
```

---

## Task 8: Validation finale + full test run

- [ ] **Step 8.1 — Run full recommendations test suite**

```bash
cd g:/ramypulse && python -m pytest tests/test_recommendations.py -v
```

Expected: all tests PASS.

- [ ] **Step 8.2 — Run all project tests (no regressions)**

```bash
cd g:/ramypulse && python -m pytest tests/ --tb=short -q
```

Expected: no new failures. Any pre-existing failures are unrelated to Agent 2.

- [ ] **Step 8.3 — Run Section 8 Agent 2 validation test (requires annotated.parquet)**

```bash
cd g:/ramypulse && python -c "
from core.recommendation.context_builder import build_recommendation_context
import pandas as pd, pathlib

parquet = pathlib.Path('data/processed/annotated.parquet')
if not parquet.exists():
    print('SKIP — annotated.parquet absent, test live non disponible')
else:
    df = pd.read_parquet(parquet)
    ctx = build_recommendation_context('manual', None, df)
    assert 'current_metrics' in ctx
    assert 'active_alerts' in ctx
    assert ctx['estimated_tokens'] > 0
    print('✅ Agent 2 — Context Builder OK')
    print(f'   tokens≈{ctx[\"estimated_tokens\"]} alertes={len(ctx[\"active_alerts\"])} chunks={len(ctx[\"rag_chunks\"])}')
"
```

- [ ] **Step 8.4 — Commit final**

```bash
git add tests/test_recommendations.py
git commit -m "[agent2] p2-reco: Recommendation Agent context + client + prompt + page Streamlit"
```

---

## Self-Review: Spec Coverage Check

| Spec requirement | Task |
|---|---|
| `core/recommendation/__init__.py` | Task 3 |
| `prompt_manager.py` — prompt système v1.0 versionné | Task 3 |
| `agent_client.py` — Anthropic + OpenAI + Ollama + parse JSON | Task 4 |
| `context_builder.py` — build_recommendation_context (INTERFACES.md 4.6) | Task 5 |
| `recommendation_manager.py` — save_recommendation() CRUD | Task 6 |
| `pages/08_recommendations.py` — template Section 6 | Task 7 |
| TDD : tests/test_recommendations.py AVANT | Each task writes tests first |
| Wave 5 constants dans config.py | Task 1 |
| Migration recommendations table → INTERFACES.md schema | Task 2 |
| SQLite uniquement via pattern Section 7 | Tasks 2, 6 |
| Docstrings en français, logging pas print() | All tasks |
| st.cache_data(ttl=300) | Task 7 |
| st.rerun() pas st.experimental_rerun() | Task 7 |
| parse JSON robuste (fallback si texte libre) | Task 4 |
| Clé API jamais dans les logs | Task 4, 7 |
| Dégradation gracieuse si agents 1/3 absents | Task 5 |
| Dégradation gracieuse si FAISS index absent | Task 5 |
| Validation Section 8 Agent 2 | Task 8 |
