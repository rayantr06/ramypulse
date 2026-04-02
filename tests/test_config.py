"""Tests unitaires pour config.py."""

import importlib
import sys
from pathlib import Path


def _reload_config():
    """Recharge config pour isoler les tests."""
    if "config" in sys.modules:
        del sys.modules["config"]
    return importlib.import_module("config")


class TestConfigImportable:
    """config.py est importable sans erreur."""

    def test_import_sans_erreur(self):
        """Le module config s'importe sans lever d'exception."""
        cfg = _reload_config()
        assert cfg is not None

    def test_pas_de_logique_metier(self):
        """Aucune fonction métier n'est exposée au niveau module."""
        cfg = _reload_config()
        metier_interdits = ["predict", "classify", "analyze", "scrape"]
        for nom in metier_interdits:
            assert not hasattr(cfg, nom), f"Attribut métier interdit: {nom}"


class TestChemins:
    """Tous les chemins existent ou sont créés automatiquement."""

    def test_base_dir_est_path(self):
        cfg = _reload_config()
        assert isinstance(cfg.BASE_DIR, Path)

    def test_data_dir_existe(self):
        cfg = _reload_config()
        assert cfg.DATA_DIR.exists(), f"DATA_DIR manquant: {cfg.DATA_DIR}"

    def test_models_dir_existe(self):
        cfg = _reload_config()
        assert cfg.MODELS_DIR.exists(), f"MODELS_DIR manquant: {cfg.MODELS_DIR}"

    def test_data_dir_est_sous_base(self):
        cfg = _reload_config()
        assert cfg.DATA_DIR.is_relative_to(cfg.BASE_DIR) or cfg.DATA_DIR.exists()

    def test_models_dir_est_sous_base(self):
        cfg = _reload_config()
        assert cfg.MODELS_DIR.is_relative_to(cfg.BASE_DIR) or cfg.MODELS_DIR.exists()

    def test_faiss_index_path_est_path(self):
        cfg = _reload_config()
        assert isinstance(cfg.FAISS_INDEX_PATH, Path)

    def test_dziribert_model_path_est_path(self):
        cfg = _reload_config()
        assert isinstance(cfg.DZIRIBERT_MODEL_PATH, Path)


class TestModeles:
    """Paramètres des modèles ML."""

    def test_whisper_model_size_valide(self):
        cfg = _reload_config()
        tailles_valides = {"tiny", "base", "small", "medium", "large", "large-v2", "large-v3"}
        assert cfg.WHISPER_MODEL_SIZE in tailles_valides

    def test_ollama_model_est_string(self):
        cfg = _reload_config()
        assert isinstance(cfg.OLLAMA_MODEL, str)
        assert len(cfg.OLLAMA_MODEL) > 0

    def test_ollama_model_defaut(self):
        cfg = _reload_config()
        assert cfg.OLLAMA_MODEL == "llama3.2:3b"

    def test_ollama_base_url_est_string(self):
        cfg = _reload_config()
        assert isinstance(cfg.OLLAMA_BASE_URL, str)
        assert cfg.OLLAMA_BASE_URL.startswith("http")

    def test_embedding_model_est_string(self):
        cfg = _reload_config()
        assert isinstance(cfg.EMBEDDING_MODEL, str)
        assert "e5" in cfg.EMBEDDING_MODEL or "multilingual" in cfg.EMBEDDING_MODEL

    def test_embedding_dim_est_768(self):
        cfg = _reload_config()
        assert cfg.EMBEDDING_DIM == 768

    def test_embedding_dim_est_entier(self):
        cfg = _reload_config()
        assert isinstance(cfg.EMBEDDING_DIM, int)


class TestLabelsEtListes:
    """Constantes métier: labels, aspects, canaux."""

    def test_sentiment_labels_est_liste(self):
        cfg = _reload_config()
        assert isinstance(cfg.SENTIMENT_LABELS, list)

    def test_sentiment_labels_5_elements(self):
        cfg = _reload_config()
        assert len(cfg.SENTIMENT_LABELS) == 5

    def test_sentiment_labels_contenu(self):
        cfg = _reload_config()
        attendus = {"très_positif", "positif", "neutre", "négatif", "très_négatif"}
        assert set(cfg.SENTIMENT_LABELS) == attendus

    def test_aspect_list_est_liste(self):
        cfg = _reload_config()
        assert isinstance(cfg.ASPECT_LIST, list)

    def test_aspect_list_5_elements(self):
        cfg = _reload_config()
        assert len(cfg.ASPECT_LIST) == 5

    def test_aspect_list_contenu(self):
        cfg = _reload_config()
        attendus = {"goût", "emballage", "prix", "disponibilité", "fraîcheur"}
        assert set(cfg.ASPECT_LIST) == attendus

    def test_channels_est_liste(self):
        cfg = _reload_config()
        assert isinstance(cfg.CHANNELS, list)

    def test_channels_5_elements(self):
        cfg = _reload_config()
        assert len(cfg.CHANNELS) == 5

    def test_channels_contenu(self):
        cfg = _reload_config()
        attendus = {"facebook", "google_maps", "audio", "youtube", "instagram"}
        assert set(cfg.CHANNELS) == attendus


class TestNSSFormule:
    """NSS_FORMULA est documentée inline."""

    def test_nss_formula_presente(self):
        cfg = _reload_config()
        assert hasattr(cfg, "NSS_FORMULA")

    def test_nss_formula_est_string(self):
        cfg = _reload_config()
        assert isinstance(cfg.NSS_FORMULA, str)

    def test_nss_formula_contient_composantes(self):
        cfg = _reload_config()
        # La formule doit mentionner positifs, négatifs, total
        formule = cfg.NSS_FORMULA.lower()
        assert "positif" in formule or "positifs" in formule
        assert "négatif" in formule or "negatif" in formule or "négatifs" in formule
        assert "total" in formule or "100" in formule


class TestApifyApiKey:
    """APIFY_API_KEY est optionnel."""

    def test_apify_api_key_existe(self):
        cfg = _reload_config()
        assert hasattr(cfg, "APIFY_API_KEY")

    def test_apify_api_key_none_sans_env(self, monkeypatch):
        """Sans variable d'environnement, la clé vaut None ou chaîne vide."""
        monkeypatch.delenv("APIFY_API_KEY", raising=False)
        cfg = _reload_config()
        # Doit être None ou "" sans .env
        assert cfg.APIFY_API_KEY is None or cfg.APIFY_API_KEY == ""


class TestValeursSansEnv:
    """Les valeurs par défaut permettent de lancer le système sans .env."""

    def test_toutes_constantes_obligatoires_presentes(self):
        cfg = _reload_config()
        obligatoires = [
            "BASE_DIR", "DATA_DIR", "MODELS_DIR", "DZIRIBERT_MODEL_PATH",
            "WHISPER_MODEL_SIZE", "OLLAMA_MODEL", "OLLAMA_BASE_URL",
            "FAISS_INDEX_PATH", "EMBEDDING_MODEL", "EMBEDDING_DIM",
            "SENTIMENT_LABELS", "ASPECT_LIST", "CHANNELS", "NSS_FORMULA",
            "APIFY_API_KEY",
            # Wave 5
            "DEFAULT_CLIENT_ID", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
            "DEFAULT_AGENT_PROVIDER", "DEFAULT_AGENT_MODEL",
            "DEFAULT_PRE_WINDOW_DAYS", "DEFAULT_POST_WINDOW_DAYS",
            "MIN_SIGNALS_FOR_ATTRIBUTION",
            "SOURCE_HEALTH_THRESHOLD", "ALERT_DETECTION_INTERVAL_MINUTES",
            "ANNOTATED_PARQUET_PATH", "CLEAN_PARQUET_PATH",
        ]
        for nom in obligatoires:
            assert hasattr(cfg, nom), f"Constante manquante: {nom}"
