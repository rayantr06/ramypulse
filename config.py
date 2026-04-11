"""Configuration centrale de RamyPulse.

Centralise tous les chemins, constantes et paramètres de modèles.
Aucune logique métier ici.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env (optionnel)
load_dotenv()

# ---------------------------------------------------------------------------
# Chemins de base
# ---------------------------------------------------------------------------

BASE_DIR: Path = Path(__file__).parent.resolve()
DATA_DIR: Path = BASE_DIR / "data"
TENANTS_DIR: Path = DATA_DIR / "tenants"
MODELS_DIR: Path = BASE_DIR / "models"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
EMBEDDINGS_DIR: Path = DATA_DIR / "embeddings"
DEMO_DATA_DIR: Path = DATA_DIR / "demo"
SQLITE_DB_PATH: Path = DATA_DIR / "ramypulse.db"
SECRETS_DIR: Path = DATA_DIR / "secrets"
SECRETS_STORE_PATH: Path = SECRETS_DIR / "local_secrets.json"

# Création automatique des dossiers si absents
DATA_DIR.mkdir(parents=True, exist_ok=True)
TENANTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
SECRETS_DIR.mkdir(parents=True, exist_ok=True)
(MODELS_DIR / "dziribert").mkdir(parents=True, exist_ok=True)
(MODELS_DIR / "dziribert-sentiment").mkdir(parents=True, exist_ok=True)
(MODELS_DIR / "whisper").mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Modèles ML
# ---------------------------------------------------------------------------

DZIRIBERT_MODEL_PATH: Path = MODELS_DIR / "dziribert-sentiment"
"""Chemin local vers le modèle DziriBERT fine-tuné (3 classes: positive/negative/neutral)."""

WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "large-v3")
"""Taille du modèle Whisper: tiny, base, small, medium, large, large-v2, large-v3."""

OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
"""Modèle Ollama utilisé pour la génération RAG."""

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
"""URL de base de l'API Ollama locale."""

EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
"""Modèle d'embedding multilingue pour FAISS (768 dimensions)."""

EMBEDDING_DIM: int = 768
"""Dimension des vecteurs d'embedding produits par multilingual-e5-base."""

# ---------------------------------------------------------------------------
# Index FAISS
# ---------------------------------------------------------------------------

FAISS_INDEX_PATH: Path = EMBEDDINGS_DIR / "faiss_index"
"""Chemin vers l'index FAISS sauvegardé sur disque."""

# ---------------------------------------------------------------------------
# Constantes métier
# ---------------------------------------------------------------------------

SENTIMENT_LABELS: list[str] = [
    "très_positif",
    "positif",
    "neutre",
    "négatif",
    "très_négatif",
]
"""5 classes discrètes de sentiment — jamais de score continu."""

ASPECT_LIST: list[str] = [
    "goût",
    "emballage",
    "prix",
    "disponibilité",
    "fraîcheur",
]
"""5 aspects produit Ramy analysés en ABSA."""

CHANNELS: list[str] = [
    "facebook",
    "google_maps",
    "audio",
    "youtube",
    "instagram",
    "public_url_seed",
    "web_search",
    "press",
    "reddit",
]
"""Canaux de collecte supportés."""

ASPECT_KEYWORDS: dict[str, list[str]] = {
    "goût": [
        "ta3m",
        "طعم",
        "goût",
        "saveur",
        "madha9",
        "bnin",
        "ldid",
        "mli7",
        "doux",
        "amer",
        "sucré",
    ],
    "emballage": [
        "bouteille",
        "plastique",
        "تغليف",
        "9ar3a",
        "emballage",
        "packaging",
        "3olba",
        "couvercle",
        "bouchon",
        "fuite",
    ],
    "prix": [
        "ghali",
        "rkhis",
        "سعر",
        "prix",
        "cher",
        "pas_cher",
        "prix_abordable",
        "t7ayol",
        "promotions",
    ],
    "disponibilité": [
        "nlgah",
        "ma_kaynch",
        "متوفر",
        "disponible",
        "rupture",
        "yla9awh",
        "ma_lgitouch",
    ],
    "fraîcheur": [
        "bared",
        "skhoun",
        "طازج",
        "frais",
        "froid",
        "chaud",
        "périmé",
        "fraîcheur",
        "date",
        "expiration",
    ],
}
"""Dictionnaire bilingue des mots-clés d'aspects, surchargeable via config."""

# ---------------------------------------------------------------------------
# Formule NSS (Net Sentiment Score)
# ---------------------------------------------------------------------------

NSS_FORMULA: str = (
    "NSS = (nb_très_positifs + nb_positifs - nb_négatifs - nb_très_négatifs) "
    "/ total × 100"
)
"""Formule du Net Sentiment Score.

Calcul: (très_positif + positif - négatif - très_négatif) / total × 100
Plage: [-100, +100]. Neutre exclue du calcul (pas de contribution).
"""

# ---------------------------------------------------------------------------
# Chemins parquet et index
# ---------------------------------------------------------------------------

INDEX_DIR: Path = BASE_DIR / "index"
CLEAN_PARQUET_PATH: Path = PROCESSED_DATA_DIR / "clean.parquet"
ANNOTATED_PARQUET_PATH: Path = PROCESSED_DATA_DIR / "annotated.parquet"
BM25_METADATA_PATH: Path = INDEX_DIR / "bm25_metadata.json"

# ---------------------------------------------------------------------------
# Client par défaut (PoC mono-client)
# ---------------------------------------------------------------------------

DEFAULT_CLIENT_ID: str = "ramy_client_001"
"""Identifiant client unique pour le PoC mono-tenant."""

SAFE_EXPO_CLIENT_ID: str = os.getenv("SAFE_EXPO_CLIENT_ID", "ramy-demo")
"""Client de repli pour l'expo quand aucun tenant actif n'est défini."""
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")

# ---------------------------------------------------------------------------
# Recommendation Agent
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
DEFAULT_AGENT_PROVIDER: str = os.getenv("AGENT_PROVIDER", "google_gemini")
DEFAULT_AGENT_MODEL: str = os.getenv("AGENT_MODEL", "gemini-2.5-flash")
DEFAULT_RUNTIME_MODE: str = os.getenv("RAMYPULSE_RUNTIME_MODE", "")
RECOMMENDATION_AGENT_PROMPT_VERSION: str = "1.1"
WEEKLY_REPORT_EMAIL_TO: str = os.getenv("WEEKLY_REPORT_EMAIL_TO", "")
WEEKLY_REPORT_SLACK_WEBHOOK_REFERENCE: str = os.getenv("WEEKLY_REPORT_SLACK_WEBHOOK_REFERENCE", "")
ALERT_NOTIFICATION_EMAIL_TO: str = os.getenv("ALERT_NOTIFICATION_EMAIL_TO", "")
ALERT_NOTIFICATION_SLACK_WEBHOOK_REFERENCE: str = os.getenv("ALERT_NOTIFICATION_SLACK_WEBHOOK_REFERENCE", "")
ALERT_NOTIFICATION_MIN_SEVERITY: str = os.getenv("ALERT_NOTIFICATION_MIN_SEVERITY", "critical")

# Estimated prompt input pricing, expressed in USD per 1K input tokens.
# Used only for pre-generation cost previews in the UI.
LLM_INPUT_PRICING_USD_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "anthropic": {
        "claude-opus-4-6": 0.015,
        "claude-sonnet-4-6": 0.003,
        "claude-haiku-4-5-20251001": 0.0008,
    },
    "openai": {
        "gpt-4o": 0.0025,
        "gpt-4-turbo": 0.01,
        "o1-preview": 0.015,
    },
    "google_gemini": {
        "gemini-2.5-flash": 0.0003,
        "gemini-2.5-pro": 0.00125,
        "gemini-2.0-flash": 0.0001,
    },
    "ollama_local": {
        "qwen2.5:14b": 0.0,
        "llama3.2:3b": 0.0,
        "mistral:7b": 0.0,
    },
}

# ---------------------------------------------------------------------------
# Notifications / delivery
# ---------------------------------------------------------------------------

SMTP_HOST: str = os.getenv("SMTP_HOST", "")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD_REFERENCE: str = os.getenv("SMTP_PASSWORD_REFERENCE", "")
SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")

# ---------------------------------------------------------------------------
# Campaign Intelligence
# ---------------------------------------------------------------------------

DEFAULT_PRE_WINDOW_DAYS: int = 14
"""Fenêtre d'analyse pré-campagne en jours (défaut)."""

DEFAULT_POST_WINDOW_DAYS: int = 14
"""Fenêtre d'analyse post-campagne en jours (défaut)."""

MIN_SIGNALS_FOR_ATTRIBUTION: int = 20
"""Volume minimum de signaux pour qu'une attribution de campagne soit fiable."""

# ---------------------------------------------------------------------------
# Alertes
# ---------------------------------------------------------------------------

SOURCE_HEALTH_THRESHOLD: int = 60
"""Score en dessous duquel une alerte source_health est créée."""

ALERT_DETECTION_INTERVAL_MINUTES: int = 30
"""Intervalle entre deux cycles de détection d'alertes (minutes)."""

# ---------------------------------------------------------------------------
# Clés API externes (optionnelles)
# ---------------------------------------------------------------------------

APIFY_API_KEY: str | None = os.getenv("APIFY_API_KEY") or None
"""Clé API Apify pour les scrapers Facebook et Google Maps. Optionnelle."""
