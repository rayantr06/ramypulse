# RamyPulse — INTERFACES.md
## Source de vérité partagée entre agents de codage parallèles

---

> **RÈGLE ABSOLUE**
> Tout agent qui implémente un module RamyPulse DOIT lire ce fichier en premier.
> Ne jamais dévier des signatures, noms de colonnes, chemins, ou types définis ici.
> Si une ambiguïté existe entre ce fichier et le PRD, ce fichier a priorité pour l'implémentation.

---

## 1. Structure de fichiers — Arborescence complète

```
ramypulse/
├── app.py                          # Point d'entrée Streamlit — NE PAS MODIFIER
├── config.py                       # Constantes globales — lire avant tout
├── requirements.txt
├── data/
│   ├── processed/
│   │   ├── clean.parquet           # Output de scripts/process_data_02.py
│   │   └── annotated.parquet       # Output de scripts/classify_sentiment_03.py
│   └── raw/
├── models/
│   └── dziribert/                  # Modèle fine-tuné (si disponible)
├── index/
│   ├── faiss.index                 # Output de scripts/build_index_04.py
│   └── bm25_metadata.json          # Metadata BM25 parallèle
├── core/
│   ├── database.py                 # CRUD SQLite — NE PAS MODIFIER le schéma
│   ├── source_registry.py          # CRUD sources — existant
│   ├── business_catalog.py         # ProductCatalog, WilayaCatalog — existant
│   ├── entity_resolver.py          # Résolution entités — existant
│   ├── ingestion/
│   │   └── normalizer.py           # Normalisation dual-script — existant
│   ├── analysis/
│   │   ├── sentiment_classifier.py # DziriBERT + fallback — existant
│   │   ├── aspect_extractor.py     # Dictionnaire aspects — existant
│   │   ├── absa_engine.py          # Pipeline ABSA — existant
│   │   └── nss_calculator.py       # Calcul NSS — existant
│   ├── rag/
│   │   ├── embedder.py             # multilingual-e5-base — existant
│   │   ├── vector_store.py         # FAISS — existant
│   │   ├── retriever.py            # Hybride dense+BM25 — existant
│   │   └── generator.py            # Ollama — existant
│   ├── whatif/
│   │   └── simulator.py            # What-If engine — existant
│   ├── campaigns/                  # NOUVEAU — Agent 1
│   │   ├── __init__.py
│   │   ├── campaign_manager.py     # CRUD campaigns SQLite
│   │   └── impact_calculator.py   # compute_campaign_impact()
│   ├── alerts/                     # NOUVEAU — Agent 3
│   │   ├── __init__.py
│   │   ├── alert_manager.py        # CRUD alerts SQLite
│   │   └── alert_detector.py      # Moteur de détection
│   ├── watchlists/                 # NOUVEAU — Agent 3
│   │   ├── __init__.py
│   │   └── watchlist_manager.py   # CRUD watchlists SQLite
│   └── recommendation/             # NOUVEAU — Agent 2
│       ├── __init__.py
│       ├── context_builder.py      # Assemble le contexte pour l'agent
│       ├── agent_client.py         # Appel API (Anthropic/OpenAI/Ollama)
│       └── prompt_manager.py      # Prompt système versionné
├── pages/
│   ├── 01_dashboard.py             # Existant — NE PAS MODIFIER
│   ├── 02_explorer.py              # Existant — NE PAS MODIFIER
│   ├── 03_chat.py                  # Existant — NE PAS MODIFIER
│   ├── 04_whatif.py                # Existant — NE PAS MODIFIER
│   ├── 05_campaigns.py             # NOUVEAU — Agent 1
│   ├── 06_watchlists.py            # NOUVEAU — Agent 3
│   ├── 07_alerts.py                # NOUVEAU — Agent 3
│   ├── 08_recommendations.py       # NOUVEAU — Agent 2
│   ├── 09_admin_sources.py         # Existant — NE PAS MODIFIER
│   └── 10_admin_catalog.py         # Existant — NE PAS MODIFIER
└── scripts/
    ├── process_data_02.py          # Existant
    ├── classify_sentiment_03.py    # Existant
    ├── build_index_04.py           # Existant
    └── run_demo_05.py              # Existant
```

---

## 2. Schéma SQLite — Tables existantes dans core/database.py

**NE JAMAIS recréer ces tables. NE JAMAIS modifier le schéma existant.**
**Utiliser uniquement les fonctions CRUD de `core/database.py`.**

### Table `campaigns`
```sql
-- Colonnes garanties présentes dans core/database.py
campaign_id       TEXT PRIMARY KEY    -- UUID string
client_id         TEXT                -- Pour l'instant toujours "ramy_client_001"
campaign_name     TEXT NOT NULL
campaign_type     TEXT                -- influencer, paid_ad, sponsoring, launch, promotion, organic
platform          TEXT                -- instagram, facebook, youtube, tiktok, offline, multi_platform
description       TEXT
influencer_handle TEXT
influencer_tier   TEXT                -- nano, micro, macro, mega
target_segment    TEXT
target_aspects    TEXT                -- JSON array sérialisé : '["packaging", "gout"]'
target_regions    TEXT                -- JSON array sérialisé : '["oran", "tlemcen"]'
keywords          TEXT                -- JSON array sérialisé : '["ramy", "jus"]'
budget_dza        INTEGER
start_date        TEXT                -- ISO date : "2026-03-01"
end_date          TEXT                -- ISO date : "2026-03-15"
pre_window_days   INTEGER DEFAULT 14
post_window_days  INTEGER DEFAULT 14
status            TEXT DEFAULT 'planned'  -- planned, active, completed, cancelled
created_at        TEXT                -- ISO datetime
updated_at        TEXT                -- ISO datetime
```

### Table `alerts`
```sql
alert_id          TEXT PRIMARY KEY    -- UUID string
client_id         TEXT DEFAULT 'ramy_client_001'
watchlist_id      TEXT                -- FK nullable
alert_rule_id     TEXT                -- FK nullable
title             TEXT NOT NULL
description       TEXT
severity          TEXT                -- critical, high, medium, low
status            TEXT DEFAULT 'new' -- new, acknowledged, investigating, resolved, dismissed
detected_at       TEXT                -- ISO datetime
resolved_at       TEXT
alert_payload     TEXT                -- JSON sérialisé
dedup_key         TEXT
navigation_url    TEXT
```

### Table `watchlists`
```sql
watchlist_id      TEXT PRIMARY KEY    -- UUID string
client_id         TEXT DEFAULT 'ramy_client_001'
watchlist_name    TEXT NOT NULL
description       TEXT
scope_type        TEXT                -- product, region, channel, cross_dimension
filters           TEXT                -- JSON sérialisé : voir Section 4
is_active         INTEGER DEFAULT 1
created_at        TEXT
updated_at        TEXT
```

### Table `recommendations`
```sql
recommendation_id TEXT PRIMARY KEY    -- UUID string
client_id         TEXT DEFAULT 'ramy_client_001'
trigger_type      TEXT                -- manual, alert_triggered, scheduled
trigger_id        TEXT                -- alert_id ou watchlist_id ou campaign_id (nullable)
alert_id          TEXT                -- FK nullable vers alerts
analysis_summary  TEXT
recommendations   TEXT                -- JSON array sérialisé (voir Section 5)
watchlist_priorities TEXT             -- JSON array sérialisé
confidence_score  REAL
data_quality_note TEXT
provider_used     TEXT                -- anthropic, openai, ollama_local
model_used        TEXT
context_tokens    INTEGER
generation_ms     INTEGER
status            TEXT DEFAULT 'active' -- active, archived, dismissed
created_at        TEXT
```

### Table `notifications`
```sql
notification_id   TEXT PRIMARY KEY
client_id         TEXT DEFAULT 'ramy_client_001'
notification_type TEXT                -- alert, campaign, recommendation, system
reference_id      TEXT                -- alert_id ou campaign_id ou recommendation_id
title             TEXT NOT NULL
message           TEXT
channel           TEXT                -- in_app, email, slack
status            TEXT DEFAULT 'unread' -- unread, read, dismissed
created_at        TEXT
read_at           TEXT
```

---

## 3. Constantes globales — config.py

Chaque agent doit lire ces constantes depuis `config.py`. Ne jamais hardcoder ces valeurs.

```python
# Chemins
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
INDEX_DIR = BASE_DIR / "index"

CLEAN_PARQUET_PATH    = DATA_DIR / "processed" / "clean.parquet"
ANNOTATED_PARQUET_PATH = DATA_DIR / "processed" / "annotated.parquet"
FAISS_INDEX_PATH      = INDEX_DIR / "faiss.index"
BM25_METADATA_PATH    = INDEX_DIR / "bm25_metadata.json"
SQLITE_DB_PATH        = BASE_DIR / "ramypulse.db"

# Modèles
OLLAMA_BASE_URL       = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL          = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
EMBEDDING_MODEL       = "intfloat/multilingual-e5-base"
EMBEDDING_DIM         = 768

# Métier
SENTIMENT_LABELS = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]
ASPECT_LIST      = ["goût", "emballage", "prix", "disponibilité", "fraîcheur"]
CHANNELS         = ["facebook", "google_maps", "audio", "youtube", "instagram"]

# Client par défaut (PoC mono-client)
DEFAULT_CLIENT_ID = "ramy_client_001"

# Recommendation Agent
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "")
DEFAULT_AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "ollama_local")
DEFAULT_AGENT_MODEL    = os.getenv("AGENT_MODEL", "qwen2.5:14b")
RECOMMENDATION_AGENT_PROMPT_VERSION = "1.0"

# Campaign Intelligence
DEFAULT_PRE_WINDOW_DAYS  = 14
DEFAULT_POST_WINDOW_DAYS = 14
MIN_SIGNALS_FOR_ATTRIBUTION = 20   # Volume minimum pour qu'une attribution soit fiable

# Alertes
SOURCE_HEALTH_THRESHOLD = 60       # Score en dessous duquel une alerte source_health est créée
ALERT_DETECTION_INTERVAL_MINUTES = 30
```

---

## 4. Interfaces des fonctions partagées

### 4.1 `core/campaigns/impact_calculator.py`

```python
def compute_campaign_impact(
    campaign_id: str,
    df_annotated: pd.DataFrame       # annotated.parquet chargé
) -> dict:
    """
    Calcule l'impact d'une campagne sur les métriques NSS.
    
    Returns:
    {
        "campaign_id": str,
        "campaign_name": str,
        "phases": {
            "pre":    {"nss": float|None, "volume": int, "aspect_breakdown": dict, "sentiment_breakdown": dict},
            "active": {"nss": float|None, "volume": int, "aspect_breakdown": dict, "sentiment_breakdown": dict},
            "post":   {"nss": float|None, "volume": int, "aspect_breakdown": dict, "sentiment_breakdown": dict}
        },
        "uplift_nss": float|None,          # post.nss - pre.nss, None si données insuffisantes
        "uplift_volume_pct": float|None,   # % variation volume post vs pre
        "is_reliable": bool,               # True si volume >= MIN_SIGNALS_FOR_ATTRIBUTION dans chaque phase
        "reliability_note": str            # Message si is_reliable = False
    }
    """
```

```python
def filter_signals_for_campaign(
    df: pd.DataFrame,
    campaign: dict,
    start_date: str,    # ISO date
    end_date: str       # ISO date
) -> pd.DataFrame:
    """
    Filtre le DataFrame selon les dimensions de la campagne dans une fenêtre temporelle.
    
    Filtres appliqués (AND logique, champ ignoré si None/vide) :
    - timestamp entre start_date et end_date
    - channel == campaign["platform"] (si platform != "multi_platform")
    - aspect in campaign["target_aspects"] (si non vide)
    - wilaya in campaign["target_regions"] (si non vide)
    - text contient au moins 1 keyword de campaign["keywords"] (si non vide)
    
    Returns: DataFrame filtré, peut être vide.
    """
```

```python
def compute_attribution_score(row: pd.Series, campaign: dict) -> float:
    """
    Calcule le score d'attribution d'un signal à une campagne.
    Score entre 0.0 et 1.0.
    
    Logique :
    - Base (fenêtre temporelle + plateforme) : 0.3
    - Handle influenceur mentionné dans text : +0.4
    - >= 1 keyword présent dans text : +0.2 (max)
    - aspect correspond à target_aspects : +0.1
    
    Returns: float entre 0.0 et 1.0
    """
```

### 4.2 `core/campaigns/campaign_manager.py`

```python
def create_campaign(campaign_data: dict) -> str:
    """Insère une campagne. Returns campaign_id (UUID str)."""

def get_campaign(campaign_id: str) -> dict | None:
    """Returns dict avec tous les champs, target_aspects/target_regions/keywords désérialisés en list."""

def list_campaigns(
    status: str | None = None,
    platform: str | None = None,
    limit: int = 50
) -> list[dict]:
    """Returns liste de campagnes. Champs JSON désérialisés automatiquement."""

def update_campaign_status(campaign_id: str, status: str) -> bool:
    """status doit être dans : planned, active, completed, cancelled"""

def delete_campaign(campaign_id: str) -> bool:
    """Suppression définitive."""
```

**Important** : `target_aspects`, `target_regions`, `keywords` sont stockés en JSON string dans SQLite mais doivent être automatiquement sérialisés/désérialisés dans toutes les fonctions CRUD. Le consommateur reçoit toujours des `list[str]`, jamais une string JSON.

### 4.3 `core/alerts/alert_manager.py`

```python
def create_alert(
    title: str,
    description: str,
    severity: str,              # critical, high, medium, low
    alert_payload: dict,
    watchlist_id: str | None = None,
    dedup_key: str | None = None,
    navigation_url: str | None = None
) -> str | None:
    """
    Crée une alerte. Si dedup_key existe déjà en statut actif (new/acknowledged/investigating),
    retourne None sans créer de doublon.
    Returns alert_id (UUID str) ou None si dupliqué.
    """

def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    limit: int = 100
) -> list[dict]:
    """alert_payload désérialisé en dict automatiquement."""

def update_alert_status(alert_id: str, status: str) -> bool:
    """status doit être dans : new, acknowledged, investigating, resolved, dismissed"""

def get_alert(alert_id: str) -> dict | None:
    """Returns dict complet, alert_payload désérialisé."""
```

### 4.4 `core/alerts/alert_detector.py`

```python
def run_alert_detection(df_annotated: pd.DataFrame) -> list[str]:
    """
    Job principal de détection. Lit toutes les watchlists actives,
    calcule les métriques, applique les règles, crée les alertes.
    
    Returns: liste des alert_ids créés lors de ce cycle (peut être vide).
    
    Règles implémentées en v1 :
    1. NSS global < 20 → alerte "nss_critical_low"
    2. Volume négatif+très_négatif > 60% du volume total → "negative_volume_surge"
    3. Aucun signal depuis 7 jours → "no_recent_signals"
    4. NSS aspect < -10 (très mauvais sur un aspect) → "aspect_critical_[aspect]"
    5. Volume total cette semaine < 50% de la semaine précédente → "volume_drop"
    """

def compute_watchlist_metrics(
    watchlist: dict,
    df_annotated: pd.DataFrame
) -> dict:
    """
    Calcule les métriques pour une watchlist selon ses filtres.
    
    Returns:
    {
        "watchlist_id": str,
        "nss_current": float | None,
        "nss_previous": float | None,       # Semaine précédente
        "volume_current": int,
        "volume_previous": int,
        "delta_nss": float | None,
        "delta_volume_pct": float | None,
        "aspect_breakdown": dict,           # {aspect: nss_value}
        "computed_at": str                  # ISO datetime
    }
    """
```

### 4.5 `core/watchlists/watchlist_manager.py`

```python
def create_watchlist(
    name: str,
    description: str,
    scope_type: str,
    filters: dict               # Voir structure ci-dessous
) -> str:
    """Returns watchlist_id."""

def list_watchlists(is_active: bool = True) -> list[dict]:
    """filters désérialisé en dict automatiquement."""

def get_watchlist(watchlist_id: str) -> dict | None:
    """filters désérialisé en dict."""

def update_watchlist(watchlist_id: str, updates: dict) -> bool:
    """updates peut contenir n'importe quel sous-ensemble des champs."""

def deactivate_watchlist(watchlist_id: str) -> bool:
    """Met is_active = 0."""
```

**Structure du champ `filters` (stocké en JSON string, exposé en dict)** :

```python
filters = {
    "channel": "facebook" | None,          # None = tous les canaux
    "aspect": "emballage" | None,           # None = tous les aspects
    "wilaya": "oran" | None,                # None = toutes les wilayas
    "product": "ramy_citron" | None,        # None = tous les produits
    "sentiment": "négatif" | None,          # None = tous les sentiments
    "period_days": 7,                       # Fenêtre d'analyse en jours (défaut: 7)
    "min_volume": 10                        # Volume minimum pour que la métrique soit fiable
}
```

### 4.6 `core/recommendation/context_builder.py`

```python
def build_recommendation_context(
    trigger_type: str,                  # manual, alert_triggered, scheduled
    trigger_id: str | None,            # alert_id ou watchlist_id ou campaign_id
    df_annotated: pd.DataFrame,
    max_rag_chunks: int = 8
) -> dict:
    """
    Assemble le contexte complet pour l'agent de recommandations.
    
    Returns:
    {
        "client_profile": {
            "client_name": "Ramy",
            "industry": "Agroalimentaire algérien",
            "main_products": list[str],
            "active_regions": list[str]
        },
        "trigger": {
            "type": str,
            "id": str | None
        },
        "current_metrics": {
            "nss_global": float | None,
            "nss_by_aspect": dict,
            "nss_by_channel": dict,
            "volume_total": int,
            "top_negative_aspects": list[str]
        },
        "active_alerts": list[dict],        # Max 5, triés par sévérité
        "active_watchlists": list[dict],    # Max 5, avec métriques
        "recent_campaigns": list[dict],     # Max 3, avec uplift calculé
        "rag_chunks": list[dict],           # Max 8 chunks pertinents
        "estimated_tokens": int             # Estimation de la taille du contexte
    }
    """
```

### 4.7 `core/recommendation/agent_client.py`

```python
def generate_recommendations(
    context: dict,
    provider: str = DEFAULT_AGENT_PROVIDER,     # anthropic, openai, ollama_local
    model: str | None = None,                   # None = utiliser défaut du provider
    api_key: str | None = None                  # None = lire depuis config/env
) -> dict:
    """
    Appelle le LLM et retourne les recommandations parsées.
    Gère les erreurs de parsing avec fallback robuste.
    Mesure le temps de génération.
    
    Returns:
    {
        "analysis_summary": str,
        "recommendations": [
            {
                "id": str,                      # rec_001, rec_002, ...
                "priority": str,                # critical, high, medium, low
                "type": str,                    # influencer_campaign, paid_ad, content_organic,
                                                # community_response, product_action, distribution_action
                "title": str,
                "rationale": str,
                "target_platform": str,
                "target_segment": str,
                "target_regions": list[str],
                "target_aspects": list[str],
                "timing": {
                    "urgency": str,             # immediate, within_week, within_month
                    "best_moment": str
                },
                "influencer_profile": {
                    "tier": str,                # nano, micro, macro, mega, none
                    "niche": str,
                    "tone": str,
                    "engagement_focus": str
                },
                "content": {
                    "hooks": list[str],         # 3 hooks minimum
                    "script_outline": str,
                    "key_messages": list[str],
                    "visual_direction": str,
                    "call_to_action": str
                },
                "kpi_to_track": list[str],
                "data_basis": str               # Référence aux données RamyPulse
            }
        ],
        "watchlist_priorities": list[str],
        "confidence_score": float,              # 0.0 à 1.0
        "data_quality_note": str,
        "provider_used": str,
        "model_used": str,
        "generation_ms": int,
        "parse_success": bool                   # False si fallback JSON utilisé
    }
    """
```

---

## 5. Schéma du DataFrame `annotated.parquet`

**Colonnes garanties présentes. Ne jamais assumer d'autres colonnes sans vérification.**

```python
# Colonnes obligatoires — présentes dans tous les enregistrements
"text"              # str  — texte normalisé
"text_original"     # str  — texte brut original
"sentiment_label"   # str  — dans SENTIMENT_LABELS
"confidence"        # float — entre 0.0 et 1.0
"channel"           # str  — dans CHANNELS
"aspect"            # str  — dans ASPECT_LIST, peut être None/NaN
"timestamp"         # str  — ISO datetime ou date (parser avec pd.to_datetime)
"source_url"        # str  — peut être None/NaN

# Colonnes optionnelles — peuvent être absentes ou NaN
"wilaya"            # str  — nom de wilaya normalisé en minuscules, ex: "oran"
"product"           # str  — nom de produit normalisé
"author"            # str
"language"          # str  — darija, french, mixed
"script_detected"   # str  — arabic, latin, mixed
"aspect_sentiments" # str  — JSON sérialisé : '[{"aspect": "goût", "sentiment": "positif"}]'
```

**Règles de chargement** :
```python
import pandas as pd
from config import ANNOTATED_PARQUET_PATH

def load_annotated() -> pd.DataFrame:
    """Pattern standard de chargement. Toujours utiliser cette fonction."""
    df = pd.read_parquet(ANNOTATED_PARQUET_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["wilaya"]    = df["wilaya"].fillna("").str.lower().str.strip()
    df["product"]   = df["product"].fillna("").str.lower().str.strip()
    df["aspect"]    = df["aspect"].fillna("")
    df["source_url"]= df["source_url"].fillna("")
    return df
```

---

## 6. Conventions Streamlit — Pages nouvelles

Chaque nouvelle page suit exactement ce template :

```python
import streamlit as st
import pandas as pd
from config import ANNOTATED_PARQUET_PATH, DEFAULT_CLIENT_ID

st.set_page_config(page_title="[Nom de la page] — RamyPulse", layout="wide")

# ─── Chargement des données ───────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """TTL 300 secondes. Retourne DataFrame vide si fichier absent."""
    try:
        df = pd.read_parquet(ANNOTATED_PARQUET_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    except FileNotFoundError:
        return pd.DataFrame()

df = load_data()

# ─── Header ──────────────────────────────────────────────────────────────────
st.title("🎯 [Titre de la page]")
st.caption("[Description courte]")

if df.empty:
    st.warning("⚠️ Données non disponibles. Lancez d'abord scripts/run_demo_05.py")
    st.stop()

# ─── Contenu principal ───────────────────────────────────────────────────────
# ... logique de la page
```

**Règles UI obligatoires pour toutes les nouvelles pages** :
- `st.cache_data(ttl=300)` sur chaque fonction de chargement de données
- Toujours gérer le cas `df.empty` avec `st.stop()`
- Toujours gérer les exceptions SQLite avec `try/except` et `st.error()`
- Ne jamais appeler directement `sqlite3` — toujours passer par les managers `core/`
- Pas de `st.experimental_rerun()` — utiliser `st.rerun()` (API Streamlit 1.35+)

---

## 7. Conventions SQLite — Règles communes

```python
# Pattern d'accès SQLite dans les managers core/
import sqlite3
import json
import uuid
from datetime import datetime
from config import SQLITE_DB_PATH

def _get_connection():
    """Toujours utiliser ce pattern. Ne jamais garder de connexion ouverte."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _serialize_list(value: list | None) -> str:
    """Sérialiser une liste en JSON string pour SQLite."""
    return json.dumps(value or [], ensure_ascii=False)

def _deserialize_list(value: str | None) -> list:
    """Désérialiser une JSON string en liste."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

def _deserialize_dict(value: str | None) -> dict:
    """Désérialiser une JSON string en dict."""
    if not value:
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}

def _new_id() -> str:
    """Générer un UUID string."""
    return str(uuid.uuid4())

def _now() -> str:
    """Timestamp ISO courant."""
    return datetime.now().isoformat()
```

---

## 8. Plan d'implémentation par agent

### Agent 1 — Campaign Intelligence
**Lire** : Sections 2 (table campaigns), 4.1 (impact_calculator), 4.2 (campaign_manager), 7 (SQLite)

**Ordre d'implémentation** :
1. `core/campaigns/campaign_manager.py` — CRUD complet
2. `core/campaigns/impact_calculator.py` — compute_campaign_impact + filter_signals + attribution_score
3. `pages/05_campaigns.py` — UI complète
4. Alertes campagne dans `core/alerts/alert_manager.py` : types `campaign_impact_positive` et `campaign_underperformance`

**Test de validation** :
```python
# Ce test doit passer avant de push
from core.campaigns.campaign_manager import create_campaign, get_campaign
from core.campaigns.impact_calculator import compute_campaign_impact
import pandas as pd

cid = create_campaign({
    "campaign_name": "Test Influenceur Oran",
    "campaign_type": "influencer",
    "platform": "instagram",
    "target_aspects": ["emballage"],
    "target_regions": ["oran"],
    "keywords": ["ramy", "bouteille"],
    "start_date": "2026-02-01",
    "end_date": "2026-02-15",
})
assert cid is not None

df = pd.read_parquet("data/processed/annotated.parquet")
result = compute_campaign_impact(cid, df)
assert "phases" in result
assert "uplift_nss" in result
assert result["phases"]["pre"]["volume"] >= 0
print("✅ Agent 1 — Campaign Intelligence OK")
```

---

### Agent 2 — Recommendation Agent
**Lire** : Sections 2 (table recommendations), 4.6 (context_builder), 4.7 (agent_client), 5 (DataFrame), 7 (SQLite)

**Ordre d'implémentation** :
1. `core/recommendation/prompt_manager.py` — prompt système v1.0
2. `core/recommendation/agent_client.py` — providers Anthropic + OpenAI + Ollama + parse JSON
3. `core/recommendation/context_builder.py` — assemblage contexte
4. Fonction `save_recommendation()` dans un `recommendation_manager.py`
5. `pages/08_recommendations.py` — UI complète avec config provider + génération + affichage

**Variables d'environnement requises** :
```bash
ANTHROPIC_API_KEY=sk-ant-...   # Optionnel si provider = ollama_local
OPENAI_API_KEY=sk-...           # Optionnel si provider = ollama_local
AGENT_PROVIDER=anthropic        # anthropic | openai | ollama_local
AGENT_MODEL=claude-sonnet-4-20250514
```

**Test de validation** :
```python
from core.recommendation.context_builder import build_recommendation_context
from core.recommendation.agent_client import generate_recommendations
import pandas as pd

df = pd.read_parquet("data/processed/annotated.parquet")
ctx = build_recommendation_context("manual", None, df)
assert "current_metrics" in ctx
assert "active_alerts" in ctx
assert ctx["estimated_tokens"] > 0

# Test avec Ollama local (pas de clé API nécessaire)
result = generate_recommendations(ctx, provider="ollama_local")
assert "recommendations" in result
assert isinstance(result["recommendations"], list)
assert result["parse_success"] == True
print("✅ Agent 2 — Recommendation Agent OK")
```

---

### Agent 3 — Watchlists + Alerts
**Lire** : Sections 2 (tables watchlists + alerts + notifications), 4.3 (alert_manager), 4.4 (alert_detector), 4.5 (watchlist_manager), 7 (SQLite)

**Ordre d'implémentation** :
1. `core/watchlists/watchlist_manager.py` — CRUD complet
2. `core/alerts/alert_manager.py` — CRUD + déduplication
3. `core/alerts/alert_detector.py` — run_alert_detection + compute_watchlist_metrics
4. `pages/06_watchlists.py` — UI création + liste + métriques
5. `pages/07_alerts.py` — Centre d'alertes + cycle de vie + lien vers recommendations

**Test de validation** :
```python
from core.watchlists.watchlist_manager import create_watchlist, list_watchlists
from core.alerts.alert_manager import create_alert, list_alerts
from core.alerts.alert_detector import run_alert_detection
import pandas as pd

wid = create_watchlist(
    name="NSS Livraison Oran",
    description="Surveille le NSS disponibilité sur Oran",
    scope_type="region",
    filters={"channel": "google_maps", "aspect": "disponibilité", "wilaya": "oran", "period_days": 7}
)
assert wid is not None

watchlists = list_watchlists()
assert any(w["watchlist_id"] == wid for w in watchlists)

df = pd.read_parquet("data/processed/annotated.parquet")
alert_ids = run_alert_detection(df)
print(f"Alertes créées : {len(alert_ids)}")

alerts = list_alerts()
assert isinstance(alerts, list)
print("✅ Agent 3 — Watchlists + Alerts OK")
```

---

## 9. Points d'intégration inter-agents

Ces trois points sont les seuls endroits où les modules des agents se touchent. Chaque agent doit respecter ces contrats sans les modifier.

### Point 1 — Alerte → Recommendation (Agent 3 → Agent 2)

Quand une alerte `critical` ou `high` est créée, `alert_manager.create_alert()` peut optionnellement déclencher la génération de recommandations. Ce déclenchement est **optionnel et configurable** via une variable d'état dans la session Streamlit ou une config SQLite.

Interface : `alert_manager.create_alert()` retourne `alert_id` (str). C'est tout ce qu'Agent 2 consomme pour lier une recommandation à une alerte.

### Point 2 — Campaign → Alert (Agent 1 → Agent 3)

Agent 1 crée des alertes de type `campaign_impact_positive` et `campaign_underperformance` en appelant directement `core/alerts/alert_manager.create_alert()`. Agent 1 n'a pas besoin d'importer quoi que ce soit d'Agent 3 au-delà de cette fonction.

### Point 3 — DataFrame partagé (tous les agents)

Tous les agents lisent `annotated.parquet` via `load_annotated()` défini en Section 5. Personne ne modifie ce fichier. C'est une lecture seule pour tous les modules Wave 5.

---

*Version 1.0 — 30 mars 2026*
*Ce fichier doit être passé en contexte à chaque agent avant toute implémentation.*