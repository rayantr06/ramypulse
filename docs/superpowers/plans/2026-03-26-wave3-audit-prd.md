# Wave 3 Audit — PRD Compliance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring all Wave 3 Streamlit pages to full PRD compliance — mock fallback on every page, missing `03_chat.py` created, testable logic extracted, all tests passing.

**Architecture:** Extract testable business logic from each page into `*_helpers.py` files (pattern established by `whatif_helpers.py`). Create shared `demo_data.py` for mock DataFrame generation with varied timestamps. Chat page uses RAG pipeline with graceful demo-mode fallback.

**Tech Stack:** Python 3.10+, Streamlit, Plotly, pandas, numpy, core.rag.* (retriever + generator)

**Constraints:**
- TDD: Red → Green → Refactor
- No modifications to Wave 1/2 modules (`core/`, `scripts/`)
- No `print()` — use `logging`
- Docstrings in French
- Plotly only for charts
- All local, no cloud dependencies
- Standard 7-column DataFrame: text, sentiment_label, channel, aspect, source_url, timestamp, confidence

**Working directory:** Create a new worktree from `main` on branch `feat/wave3-audit`

---

## File Structure

### Create
| File | Responsibility |
|------|---------------|
| `pages/demo_data.py` | Shared demo DataFrame generator (varied timestamps for trends) |
| `pages/dashboard_helpers.py` | Extracted `nss_color()`, `nss_arrow()` from dashboard |
| `pages/explorer_helpers.py` | Extracted `SENTIMENT_COLORS`, `truncate_text()` from explorer |
| `pages/chat_helpers.py` | `confidence_badge()`, `format_source_markdown()`, `build_demo_response()` |
| `pages/03_chat.py` | Full chat Q&A page with RAG + demo mode |
| `tests/test_demo_data.py` | Tests for demo data generator |
| `tests/test_dashboard_helpers.py` | Tests for dashboard helper functions |
| `tests/test_explorer_helpers.py` | Tests for explorer helper functions |
| `tests/test_chat_helpers.py` | Tests for chat helper functions |

### Modify
| File | Change |
|------|--------|
| `app.py` | Add Chat and What-If page description cards |
| `pages/01_dashboard.py` | Import helpers + mock fallback in `_load_data()` |
| `pages/02_explorer.py` | Import helpers + mock fallback in `_load_data()` |

---

## Task 1: Shared demo data generator

**Files:**
- Create: `pages/demo_data.py`
- Test: `tests/test_demo_data.py`

- [ ] **Step 1: Write failing tests for demo data**

```python
# tests/test_demo_data.py
"""Tests pour le générateur de données de démonstration partagé."""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pages.demo_data import build_demo_df


def test_demo_df_colonnes_standard() -> None:
    """Le DataFrame démo doit avoir les 7 colonnes standard RamyPulse."""
    df = build_demo_df()
    colonnes = {"text", "sentiment_label", "channel", "aspect", "source_url", "timestamp", "confidence"}
    assert colonnes.issubset(set(df.columns))


def test_demo_df_nombre_lignes() -> None:
    """Le DataFrame démo a le nombre de lignes demandé."""
    df = build_demo_df(n=100)
    assert len(df) == 100


def test_demo_df_5_sentiments() -> None:
    """Le DataFrame démo couvre les 5 classes de sentiment."""
    df = build_demo_df(n=500)
    assert set(df["sentiment_label"].unique()) == {
        "très_positif", "positif", "neutre", "négatif", "très_négatif"
    }


def test_demo_df_5_aspects() -> None:
    """Le DataFrame démo couvre les 5 aspects Ramy."""
    df = build_demo_df(n=500)
    assert set(df["aspect"].unique()) == {
        "goût", "emballage", "prix", "disponibilité", "fraîcheur"
    }


def test_demo_df_4_canaux() -> None:
    """Le DataFrame démo couvre les 4 canaux."""
    df = build_demo_df(n=500)
    assert set(df["channel"].unique()) == {
        "facebook", "google_maps", "audio", "youtube"
    }


def test_demo_df_timestamps_varies() -> None:
    """Les timestamps couvrent au moins 2 semaines (pour les tendances)."""
    df = build_demo_df(n=500)
    ts = pd.to_datetime(df["timestamp"])
    ecart = (ts.max() - ts.min()).days
    assert ecart >= 14


def test_demo_df_confidence_dans_plage() -> None:
    """La confiance est entre 0.6 et 1.0."""
    df = build_demo_df()
    assert df["confidence"].min() >= 0.6
    assert df["confidence"].max() <= 1.0


def test_demo_df_source_urls_http() -> None:
    """Les source_url commencent par http."""
    df = build_demo_df(n=10)
    assert all(url.startswith("http") for url in df["source_url"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_demo_data.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pages.demo_data'`

- [ ] **Step 3: Write minimal implementation**

```python
# pages/demo_data.py
"""Générateur de DataFrame de démonstration partagé pour toutes les pages RamyPulse.

Produit un DataFrame ABSA synthétique avec des timestamps variés,
adapté au mode démo quand aucune donnée réelle n'est disponible.
"""
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def build_demo_df(n: int = 500) -> pd.DataFrame:
    """Génère un DataFrame ABSA synthétique pour le mode démo.

    Couvre les 5 aspects, 5 sentiments et 4 canaux du standard RamyPulse.
    Les timestamps sont répartis sur 8 semaines pour permettre les tendances.

    Args:
        n: Nombre d'enregistrements à générer.

    Returns:
        DataFrame avec les 7 colonnes standard RamyPulse.
    """
    rng = np.random.default_rng(42)

    sentiments = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]
    aspects = ["goût", "emballage", "prix", "disponibilité", "fraîcheur"]
    canaux = ["facebook", "google_maps", "audio", "youtube"]

    base = datetime(2024, 1, 1)
    timestamps = [
        (base + timedelta(days=int(d))).isoformat()
        for d in rng.integers(0, 56, n)
    ]

    logger.info("Génération de %d enregistrements de démonstration.", n)

    return pd.DataFrame(
        {
            "text": [f"Commentaire de démonstration #{i}" for i in range(n)],
            "sentiment_label": rng.choice(sentiments, n).tolist(),
            "channel": rng.choice(canaux, n).tolist(),
            "aspect": rng.choice(aspects, n).tolist(),
            "source_url": [f"https://demo.ramypulse.local/{i}" for i in range(n)],
            "timestamp": timestamps,
            "confidence": rng.uniform(0.6, 1.0, n).round(3).tolist(),
        }
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_demo_data.py -v`
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add pages/demo_data.py tests/test_demo_data.py
git commit -m "feat: add shared demo data generator for all pages"
```

---

## Task 2: Dashboard helpers + mock fallback

**Files:**
- Create: `pages/dashboard_helpers.py`
- Modify: `pages/01_dashboard.py`
- Test: `tests/test_dashboard_helpers.py`

- [ ] **Step 1: Write failing tests for dashboard helpers**

```python
# tests/test_dashboard_helpers.py
"""Tests pour les helpers du dashboard."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pages.dashboard_helpers import nss_arrow, nss_color


# ---------------------------------------------------------------------------
# nss_color
# ---------------------------------------------------------------------------

def test_nss_color_excellent() -> None:
    """NSS > 50 → vert foncé (excellent)."""
    assert nss_color(55.0) == "#2E7D32"


def test_nss_color_bon() -> None:
    """20 < NSS ≤ 50 → vert clair (bon)."""
    assert nss_color(35.0) == "#66BB6A"


def test_nss_color_moyen() -> None:
    """0 ≤ NSS ≤ 20 → orange (moyen)."""
    assert nss_color(10.0) == "#FFA726"
    assert nss_color(0.0) == "#FFA726"


def test_nss_color_problematique() -> None:
    """NSS < 0 → rouge (problématique)."""
    assert nss_color(-15.0) == "#E53935"


# ---------------------------------------------------------------------------
# nss_arrow
# ---------------------------------------------------------------------------

def test_nss_arrow_positif() -> None:
    """NSS > 0 → '▲'."""
    assert nss_arrow(25.0) == "▲"


def test_nss_arrow_negatif() -> None:
    """NSS < 0 → '▼'."""
    assert nss_arrow(-10.0) == "▼"


def test_nss_arrow_zero() -> None:
    """NSS == 0 → '●'."""
    assert nss_arrow(0.0) == "●"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dashboard_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pages.dashboard_helpers'`

- [ ] **Step 3: Write minimal implementation**

```python
# pages/dashboard_helpers.py
"""Fonctions helper testables pour le dashboard RamyPulse.

Logique métier extraite de la page Streamlit pour permettre le TDD.
"""
import logging

logger = logging.getLogger(__name__)

_NSS_COLORS = {
    "excellent": "#2E7D32",
    "bon": "#66BB6A",
    "moyen": "#FFA726",
    "problematique": "#E53935",
}


def nss_color(nss: float) -> str:
    """Retourne la couleur CSS adaptée au score NSS.

    Seuils PRD :
      > 50  → vert foncé (excellent)
      20-50 → vert clair (bon)
      0-20  → orange (moyen)
      < 0   → rouge (problématique)

    Args:
        nss: Valeur du Net Sentiment Score.

    Returns:
        Code couleur hexadécimal.
    """
    if nss > 50:
        return _NSS_COLORS["excellent"]
    if nss > 20:
        return _NSS_COLORS["bon"]
    if nss >= 0:
        return _NSS_COLORS["moyen"]
    return _NSS_COLORS["problematique"]


def nss_arrow(nss: float) -> str:
    """Retourne la flèche directionnelle pour le NSS.

    Args:
        nss: Valeur du Net Sentiment Score.

    Returns:
        '▲' si positif, '▼' si négatif, '●' si nul.
    """
    if nss > 0:
        return "▲"
    if nss < 0:
        return "▼"
    return "●"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dashboard_helpers.py -v`
Expected: 7 PASSED

- [ ] **Step 5: Update `01_dashboard.py` — import helpers + add mock fallback**

Replace the private `_nss_color`, `_nss_arrow` functions and `_NSS_COLORS` dict with imports from `dashboard_helpers`. Add mock fallback to `_load_data()`.

Changes to `pages/01_dashboard.py`:

1. Add import at top (after existing imports):
```python
from pages.dashboard_helpers import nss_arrow, nss_color
from pages.demo_data import build_demo_df
```

2. Remove these sections (lines ~27-52):
   - `_NSS_COLORS` dict
   - `_nss_color()` function
   - `_nss_arrow()` function

3. Replace all `_nss_color(` calls with `nss_color(` and `_nss_arrow(` with `nss_arrow(`.

4. Update `_load_data()` to fallback to demo data instead of empty DataFrame:
```python
@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    """Charge le dataset annoté depuis le Parquet ou fallback démo."""
    if _PARQUET_PATH.exists():
        df = pd.read_parquet(_PARQUET_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    logger.warning("Aucune donnée trouvée — mode démo avec données synthétiques.")
    df = build_demo_df()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df
```

5. Remove the early return in `main()` when `raw.empty` — the demo data ensures it's never empty. Replace with a demo banner:
```python
    raw = _load_data()
    if not _PARQUET_PATH.exists():
        st.info("📊 **Mode démo** — Données synthétiques. "
                "Placez un fichier annoté dans `data/processed/` pour les vraies données.")
```

6. Add `import logging` at the top and `logger = logging.getLogger(__name__)`.

- [ ] **Step 6: Run all dashboard tests**

Run: `pytest tests/test_dashboard_helpers.py -v`
Expected: 7 PASSED

- [ ] **Step 7: Commit**

```bash
git add pages/dashboard_helpers.py pages/01_dashboard.py tests/test_dashboard_helpers.py
git commit -m "feat: extract dashboard helpers + add demo fallback"
```

---

## Task 3: Explorer helpers + mock fallback

**Files:**
- Create: `pages/explorer_helpers.py`
- Modify: `pages/02_explorer.py`
- Test: `tests/test_explorer_helpers.py`

- [ ] **Step 1: Write failing tests for explorer helpers**

```python
# tests/test_explorer_helpers.py
"""Tests pour les helpers de l'explorateur."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pages.explorer_helpers import SENTIMENT_COLORS, truncate_text


# ---------------------------------------------------------------------------
# SENTIMENT_COLORS
# ---------------------------------------------------------------------------

def test_sentiment_colors_5_classes() -> None:
    """Les 5 classes de sentiment ont chacune une couleur."""
    expected = {"très_positif", "positif", "neutre", "négatif", "très_négatif"}
    assert set(SENTIMENT_COLORS.keys()) == expected


def test_sentiment_colors_sont_hex() -> None:
    """Toutes les couleurs sont des codes hex valides."""
    for color in SENTIMENT_COLORS.values():
        assert color.startswith("#")
        assert len(color) == 7


# ---------------------------------------------------------------------------
# truncate_text
# ---------------------------------------------------------------------------

def test_truncate_court() -> None:
    """Un texte court n'est pas tronqué."""
    assert truncate_text("court", 100) == "court"


def test_truncate_long() -> None:
    """Un texte long est tronqué avec '...'."""
    text = "a" * 150
    result = truncate_text(text, 100)
    assert len(result) == 103  # 100 + "..."
    assert result.endswith("...")


def test_truncate_exact() -> None:
    """Un texte de longueur exacte n'est pas tronqué."""
    text = "a" * 100
    assert truncate_text(text, 100) == text


def test_truncate_default_100() -> None:
    """La longueur par défaut est 100."""
    text = "a" * 150
    result = truncate_text(text)
    assert len(result) == 103
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_explorer_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pages.explorer_helpers'`

- [ ] **Step 3: Write minimal implementation**

```python
# pages/explorer_helpers.py
"""Fonctions helper testables pour l'explorateur de données RamyPulse.

Logique métier extraite de la page Streamlit pour permettre le TDD.
"""
import logging

logger = logging.getLogger(__name__)

SENTIMENT_COLORS: dict[str, str] = {
    "très_positif": "#2E7D32",
    "positif": "#66BB6A",
    "neutre": "#BDBDBD",
    "négatif": "#FF7043",
    "très_négatif": "#E53935",
}
"""Couleur associée à chaque classe de sentiment pour les visualisations."""


def truncate_text(text: str, max_len: int = 100) -> str:
    """Tronque un texte avec '...' s'il dépasse la longueur maximale.

    Args:
        text: Texte source.
        max_len: Longueur maximale avant troncature.

    Returns:
        Texte tronqué ou original si assez court.
    """
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_explorer_helpers.py -v`
Expected: 6 PASSED

- [ ] **Step 5: Update `02_explorer.py` — import helpers + add mock fallback**

Changes to `pages/02_explorer.py`:

1. Add imports at top (after existing imports):
```python
from pages.demo_data import build_demo_df
from pages.explorer_helpers import SENTIMENT_COLORS, truncate_text
```

2. Add `import logging` and `logger = logging.getLogger(__name__)`.

3. Remove the `_SENTIMENT_COLORS` dict (lines ~22-28) and `_TEXT_TRUNCATE = 100` constant.

4. Replace all `_SENTIMENT_COLORS` references with `SENTIMENT_COLORS`.

5. In `_render_table()`, replace inline truncation:
```python
# Old:
truncated = text[:_TEXT_TRUNCATE] + "..." if len(text) > _TEXT_TRUNCATE else text
# New:
truncated = truncate_text(text)
```

6. Update `_load_data()` to fallback to demo data:
```python
@st.cache_data(ttl=300)
def _load_data() -> pd.DataFrame:
    """Charge le dataset annoté depuis le Parquet ou fallback démo."""
    if _PARQUET_PATH.exists():
        df = pd.read_parquet(_PARQUET_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    logger.warning("Aucune donnée trouvée — mode démo avec données synthétiques.")
    df = build_demo_df()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df
```

7. In `main()`, replace the early return with a demo banner (same pattern as dashboard):
```python
    raw = _load_data()
    if not _PARQUET_PATH.exists():
        st.info("🔍 **Mode démo** — Données synthétiques. "
                "Placez un fichier annoté dans `data/processed/` pour les vraies données.")
```

- [ ] **Step 6: Run all explorer tests**

Run: `pytest tests/test_explorer_helpers.py -v`
Expected: 6 PASSED

- [ ] **Step 7: Commit**

```bash
git add pages/explorer_helpers.py pages/02_explorer.py tests/test_explorer_helpers.py
git commit -m "feat: extract explorer helpers + add demo fallback"
```

---

## Task 4: Chat helpers

**Files:**
- Create: `pages/chat_helpers.py`
- Test: `tests/test_chat_helpers.py`

- [ ] **Step 1: Write failing tests for chat helpers**

```python
# tests/test_chat_helpers.py
"""Tests pour les helpers de la page Chat Q&A."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pages.chat_helpers import (
    build_demo_response,
    confidence_badge,
    format_source_markdown,
)


# ---------------------------------------------------------------------------
# confidence_badge
# ---------------------------------------------------------------------------

def test_confidence_badge_high() -> None:
    """Confiance 'high' → badge vert."""
    result = confidence_badge("high")
    assert "élevée" in result
    assert "🟢" in result


def test_confidence_badge_medium() -> None:
    """Confiance 'medium' → badge jaune."""
    result = confidence_badge("medium")
    assert "moyenne" in result
    assert "🟡" in result


def test_confidence_badge_low() -> None:
    """Confiance 'low' → badge rouge."""
    result = confidence_badge("low")
    assert "faible" in result
    assert "🔴" in result


def test_confidence_badge_inconnu() -> None:
    """Valeur inconnue → badge rouge par défaut."""
    result = confidence_badge("unknown")
    assert "🔴" in result


# ---------------------------------------------------------------------------
# format_source_markdown
# ---------------------------------------------------------------------------

def test_format_source_avec_url_http() -> None:
    """Une source avec URL http → lien cliquable markdown."""
    source = {
        "text": "Un bon jus",
        "channel": "facebook",
        "url": "https://facebook.com/post/123",
        "timestamp": "2024-01-15",
    }
    result = format_source_markdown(source)
    assert "facebook" in result
    assert "[https://facebook.com/post/123]" in result
    assert "2024-01-15" in result


def test_format_source_sans_url() -> None:
    """Une source sans URL → pas de lien affiché."""
    source = {"text": "Un avis", "channel": "audio", "url": "", "timestamp": ""}
    result = format_source_markdown(source)
    assert "audio" in result
    assert "http" not in result


def test_format_source_url_non_http() -> None:
    """Une source avec URL non-http → affichage en code inline."""
    source = {"text": "Avis", "channel": "audio", "url": "local/audio_001.wav", "timestamp": ""}
    result = format_source_markdown(source)
    assert "`local/audio_001.wav`" in result


def test_format_source_texte_tronque() -> None:
    """Le texte de la source est tronqué à 200 caractères."""
    source = {"text": "a" * 300, "channel": "facebook", "url": "", "timestamp": ""}
    result = format_source_markdown(source)
    assert "a" * 200 in result
    assert "a" * 201 not in result


# ---------------------------------------------------------------------------
# build_demo_response
# ---------------------------------------------------------------------------

def test_demo_response_structure() -> None:
    """La réponse démo a les clés answer, sources, confidence."""
    result = build_demo_response("Quel est le sentiment sur le goût ?")
    assert "answer" in result
    assert "sources" in result
    assert "confidence" in result


def test_demo_response_confidence_low() -> None:
    """En mode démo, la confiance est toujours low."""
    result = build_demo_response("test")
    assert result["confidence"] == "low"


def test_demo_response_answer_non_vide() -> None:
    """La réponse démo n'est pas vide."""
    result = build_demo_response("test")
    assert len(result["answer"]) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_chat_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pages.chat_helpers'`

- [ ] **Step 3: Write minimal implementation**

```python
# pages/chat_helpers.py
"""Fonctions helper testables pour la page Chat Q&A RamyPulse.

Logique métier extraite de la page Streamlit pour permettre le TDD.
"""
import logging

logger = logging.getLogger(__name__)

_BADGES: dict[str, str] = {
    "high": "🟢 Confiance élevée",
    "medium": "🟡 Confiance moyenne",
    "low": "🔴 Confiance faible",
}


def confidence_badge(confidence: str) -> str:
    """Retourne un badge emoji + libellé pour le niveau de confiance.

    Args:
        confidence: Niveau de confiance ('high', 'medium', 'low').

    Returns:
        Chaîne avec emoji et libellé en français.
    """
    return _BADGES.get(confidence, _BADGES["low"])


def format_source_markdown(source: dict) -> str:
    """Formate une source RAG en markdown lisible pour un st.expander.

    Args:
        source: Dict avec clés text, channel, url, timestamp.

    Returns:
        Chaîne markdown formatée.
    """
    channel = source.get("channel", "inconnu")
    url = source.get("url", "")
    timestamp = source.get("timestamp", "")
    text = source.get("text", "")

    parts = [f"**Canal :** {channel}"]

    if timestamp:
        parts.append(f"**Date :** {timestamp}")

    if url and url.startswith("http"):
        parts.append(f"**Source :** [{url}]({url})")
    elif url:
        parts.append(f"**Source :** `{url}`")

    if text:
        parts.append(f"\n> {text[:200]}")

    return "\n".join(parts)


def build_demo_response(question: str) -> dict:
    """Génère une réponse de démonstration sans pipeline RAG.

    Utilisée quand Ollama ou l'index FAISS ne sont pas disponibles.

    Args:
        question: Question de l'utilisateur (ignorée en mode démo).

    Returns:
        Dict {answer, sources, confidence} avec réponse explicative.
    """
    return {
        "answer": (
            "Ceci est une réponse de démonstration. Le pipeline RAG "
            "(Ollama + FAISS) n'est pas configuré. Lancez les scripts "
            "`03_classify_sentiment.py` et `04_build_index.py` puis "
            "démarrez Ollama pour activer le chat intelligent."
        ),
        "sources": [],
        "confidence": "low",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_chat_helpers.py -v`
Expected: 11 PASSED

- [ ] **Step 5: Commit**

```bash
git add pages/chat_helpers.py tests/test_chat_helpers.py
git commit -m "feat: add chat helpers with TDD (confidence badge, source formatting, demo response)"
```

---

## Task 5: Chat page implementation

**Files:**
- Create: `pages/03_chat.py`

- [ ] **Step 1: Create `pages/03_chat.py`**

```python
# pages/03_chat.py
"""Interface Q&A RAG avec provenance pour RamyPulse.

Permet de poser des questions en langage naturel sur les données
de sentiment. Utilise le pipeline RAG (retriever + generator) avec
fallback en mode démo si le pipeline n'est pas configuré.
"""
import logging
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import FAISS_INDEX_PATH
from pages.chat_helpers import (
    build_demo_response,
    confidence_badge,
    format_source_markdown,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Détection du pipeline RAG
# ---------------------------------------------------------------------------

def _is_rag_available() -> bool:
    """Vérifie si le pipeline RAG (FAISS + Ollama) est opérationnel.

    Returns:
        True si l'index FAISS existe et Ollama répond.
    """
    faiss_path = Path(str(FAISS_INDEX_PATH) + ".faiss")
    if not faiss_path.exists():
        logger.info("Index FAISS introuvable : %s", faiss_path)
        return False
    try:
        import ollama

        ollama.list()
        return True
    except Exception as exc:
        logger.info("Ollama indisponible : %s", exc)
        return False


@st.cache_resource
def _load_pipeline():
    """Charge le pipeline RAG (retriever + generator).

    Returns:
        Tuple (Retriever, Generator).
    """
    from core.rag.embedder import Embedder
    from core.rag.generator import Generator
    from core.rag.retriever import Retriever
    from core.rag.vector_store import VectorStore

    embedder = Embedder()
    vs = VectorStore()
    vs.load(str(FAISS_INDEX_PATH))
    retriever = Retriever(vs, embedder)
    generator = Generator()
    logger.info("Pipeline RAG chargé avec succès.")
    return retriever, generator


# ---------------------------------------------------------------------------
# Page principale
# ---------------------------------------------------------------------------

def main() -> None:
    """Rendu de la page Chat Q&A."""
    st.title("💬 Chat Q&A — Analyse Ramy")
    st.markdown(
        "Posez vos questions en langage naturel sur les données de sentiment. "
        "Chaque réponse cite ses sources avec un lien cliquable."
    )

    demo_mode = not _is_rag_available()

    if demo_mode:
        st.warning(
            "⚠️ **Mode démo** — Pipeline RAG non configuré (Ollama / index FAISS). "
            "Les réponses sont simulées."
        )

    # Initialiser l'historique
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Afficher l'historique
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                for i, src in enumerate(msg["sources"]):
                    with st.expander(f"📎 Source {i + 1}"):
                        st.markdown(format_source_markdown(src))
                if "confidence" in msg:
                    st.caption(confidence_badge(msg["confidence"]))

    # Saisie utilisateur
    question = st.chat_input("Posez votre question sur les données Ramy…")
    if not question:
        return

    # Afficher le message utilisateur
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Générer la réponse
    with st.chat_message("assistant"):
        with st.spinner("Recherche en cours…"):
            if demo_mode:
                result = build_demo_response(question)
            else:
                retriever, generator = _load_pipeline()
                chunks = retriever.search(question, top_k=5)
                result = generator.generate(question, chunks)

        answer = result.get("answer", "")
        sources = result.get("sources", [])
        conf = result.get("confidence", "low")

        st.markdown(answer)

        for i, src in enumerate(sources):
            with st.expander(f"📎 Source {i + 1}"):
                st.markdown(format_source_markdown(src))

        st.caption(confidence_badge(conf))

    # Sauvegarder dans l'historique
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "confidence": conf,
        }
    )


main()
```

- [ ] **Step 2: Commit**

```bash
git add pages/03_chat.py
git commit -m "feat: implement chat Q&A page with RAG pipeline + demo mode"
```

---

## Task 6: Update app.py — all 4 page links

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Update `app.py`**

Replace the current 2-column layout with 4 columns for all pages:

```python
"""Point d'entrée Streamlit pour RamyPulse.

Lance avec: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="RamyPulse",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar — navigation et branding
# ---------------------------------------------------------------------------

st.sidebar.title("RamyPulse")
st.sidebar.caption("Analyse de sentiment ABSA — Dialecte algérien")
st.sidebar.divider()

# ---------------------------------------------------------------------------
# Page d'accueil
# ---------------------------------------------------------------------------

st.title("RamyPulse")
st.markdown(
    "Bienvenue sur **RamyPulse**, le tableau de bord d'analyse de sentiment "
    "multi-canal pour la marque Ramy."
)
st.markdown("Utilisez la barre latérale pour naviguer entre les pages.")

c1, c2 = st.columns(2)
c3, c4 = st.columns(2)

with c1:
    st.info("📊 **Dashboard** — KPIs, matrice ABSA, tendances")
with c2:
    st.info("🔍 **Explorateur** — Recherche et filtres avancés")
with c3:
    st.info("💬 **Chat Q&A** — Questions en langage naturel + sources")
with c4:
    st.info("🔮 **What-If** — Simulation d'impact par aspect")
```

- [ ] **Step 2: Commit**

```bash
git add app.py
git commit -m "feat: update app.py with all 4 page links"
```

---

## Task 7: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/test_demo_data.py tests/test_dashboard_helpers.py tests/test_explorer_helpers.py tests/test_chat_helpers.py tests/test_whatif_page.py -v`
Expected: ALL PASSED (8 + 7 + 6 + 11 + 17 = 49 tests)

- [ ] **Step 2: Verify no Wave 1/2 files were modified**

Run: `git diff --name-only main` — verify only Wave 3 files appear:
- `app.py`
- `pages/01_dashboard.py`
- `pages/02_explorer.py`
- `pages/03_chat.py` (new)
- `pages/chat_helpers.py` (new)
- `pages/dashboard_helpers.py` (new)
- `pages/demo_data.py` (new)
- `pages/explorer_helpers.py` (new)
- `tests/test_chat_helpers.py` (new)
- `tests/test_dashboard_helpers.py` (new)
- `tests/test_demo_data.py` (new)
- `tests/test_explorer_helpers.py` (new)

No files under `core/`, `scripts/`, or existing test files should appear.

- [ ] **Step 3: Verify file inventory matches PRD Section 2.3**

Confirm these Wave 3 files exist:
- `app.py` ✓
- `pages/01_dashboard.py` ✓
- `pages/02_explorer.py` ✓
- `pages/03_chat.py` ✓
- `pages/04_whatif.py` ✓

- [ ] **Step 4: Integration merge**

Follow the established workflow:
```bash
git checkout -b integration/wave-3-audit
git merge feat/wave3-audit
# Run full test suite
pytest -v
# Fast-forward merge to main
git checkout main
git merge --ff-only integration/wave-3-audit
```
