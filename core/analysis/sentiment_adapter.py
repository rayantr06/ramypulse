"""Adapter DziriBERT 3→5 classes pour RamyPulse.

Branche le SentimentPipeline v3 (DziriBERT fine-tuné 3 classes + lexicon check
+ fenêtre glissante + LLM arbitrage Gemini) dans le système existant 5 classes
(très_positif, positif, neutre, négatif, très_négatif).

Le mapping utilise la confiance du pipeline :
    positive + conf ≥ 0.85  → très_positif
    positive + conf < 0.85  → positif
    neutral                 → neutre
    negative + conf ≥ 0.85  → très_négatif
    negative + conf < 0.85  → négatif

Ce fichier ne modifie AUCUN fichier existant du repo.
Pour activer l'adapter, il suffit de changer l'import dans absa_engine.py :
    from core.analysis.sentiment_adapter import classify_sentiment

Usage standalone :
    from core.analysis.sentiment_adapter import SentimentAdapter, classify_sentiment

    adapter = SentimentAdapter(
        model_dir="/path/to/dziribert-sentiment",
        gemini_api_key="AIza...",
    )
    result = adapter.predict("ممتاز هاد المنتوج ممتاز خلاني مريض 3 يام")
    # → {"label": "très_négatif", "confidence": 0.92, "logits": [...]}
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Union
from pathlib import Path

import torch

try:
    from config import SENTIMENT_LABELS, DZIRIBERT_MODEL_PATH
except ImportError:
    SENTIMENT_LABELS = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]
    DZIRIBERT_MODEL_PATH = Path("models/dziribert")

# Import du pipeline v3 (inference/pipeline.py)
try:
    from inference.pipeline import SentimentPipeline, PredictionResult
except ImportError:
    SentimentPipeline = None
    PredictionResult = None

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Mapping 3 → 5 classes
# ─────────────────────────────────────────────────────────────────────

# Seuils de confiance pour la granularité très/standard
_INTENSITY_THRESHOLD = 0.85

_LABEL_MAP_HIGH = {
    "positive": "très_positif",
    "negative": "très_négatif",
    "neutral": "neutre",
}

_LABEL_MAP_LOW = {
    "positive": "positif",
    "negative": "négatif",
    "neutral": "neutre",
}


def _map_3_to_5(label_3: str, confidence: float) -> str:
    """Convertit un label 3-classes en label 5-classes selon la confiance."""
    if confidence >= _INTENSITY_THRESHOLD:
        return _LABEL_MAP_HIGH.get(label_3, "neutre")
    return _LABEL_MAP_LOW.get(label_3, "neutre")


def _build_logits_5(label_5: str, confidence: float) -> list[float]:
    """Génère des logits synthétiques 5-classes compatibles avec le système existant.

    Le système existant attend un vecteur de 5 logits aligné sur SENTIMENT_LABELS.
    On place un logit élevé sur la classe prédite et des logits bas sur les autres.
    """
    logits = [0.0] * len(SENTIMENT_LABELS)
    if label_5 in SENTIMENT_LABELS:
        idx = SENTIMENT_LABELS.index(label_5)
        # Logit proportionnel à la confiance (softmax inverse approximatif)
        logits[idx] = 2.0 + confidence * 3.0  # range ~ [2.0, 5.0]
    return logits


# ─────────────────────────────────────────────────────────────────────
# Adapter class
# ─────────────────────────────────────────────────────────────────────

class SentimentAdapter:
    """Adapter qui expose l'interface SentimentClassifier 5-classes
    en utilisant le SentimentPipeline v3 (3-classes + sarcasm detection)."""

    def __init__(
        self,
        model_dir: Optional[Union[str, Path]] = None,
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-2.5-flash",
        device: Optional[str] = None,
    ):
        """Initialise l'adapter.

        Args:
            model_dir: Chemin vers le modèle DziriBERT fine-tuné 3-classes.
                       Par défaut: DZIRIBERT_MODEL_PATH de config.py.
            gemini_api_key: Clé API Gemini pour l'arbitrage LLM.
                           Par défaut: variable d'environnement GEMINI_API_KEY.
            gemini_model: Nom du modèle Gemini à utiliser.
            device: Device torch ("cuda", "cpu", ou None pour auto-détection).
        """
        if SentimentPipeline is None:
            raise ImportError(
                "inference.pipeline est requis. Vérifiez que le dossier "
                "inference/ est dans le PYTHONPATH."
            )

        resolved_model_dir = str(model_dir) if model_dir else str(DZIRIBERT_MODEL_PATH)
        resolved_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")

        logger.info(
            "SentimentAdapter: chargement pipeline v3 (model=%s, gemini=%s)",
            resolved_model_dir,
            "activé" if resolved_api_key else "désactivé",
        )

        self._pipeline = SentimentPipeline(
            model_dir=resolved_model_dir,
            gemini_api_key=resolved_api_key,
            gemini_model=gemini_model,
            device=device,
        )

    def predict(self, text: str) -> dict:
        """Prédit le sentiment 5-classes d'un texte.

        Interface compatible avec SentimentClassifier.predict() :
        retourne {"label": str, "confidence": float, "logits": list[float]}

        Champs additionnels (pour debug) :
        - "method": str — comment la prédiction a été faite
        - "label_3": str — le label 3-classes original
        - "incongruity": dict | None — détails de l'incongruité détectée
        - "llm_reasoning": str | None — explication du LLM si arbitrage
        """
        result_3 = self._pipeline.predict(text)

        label_5 = _map_3_to_5(result_3.label, result_3.confidence)
        logits_5 = _build_logits_5(label_5, result_3.confidence)

        return {
            "label": label_5,
            "confidence": result_3.confidence,
            "logits": logits_5,
            # Champs de debug (ignorés par le système existant)
            "method": result_3.method,
            "label_3": result_3.label,
            "incongruity": result_3.incongruity,
            "llm_reasoning": result_3.llm_reasoning,
        }

    def predict_batch(self, texts: list[str], batch_size: int = 32) -> list[dict]:
        """Prédit le sentiment 5-classes pour une liste de textes."""
        return [self.predict(text) for text in texts]

    def get_stats(self) -> dict:
        """Retourne les statistiques du pipeline sous-jacent."""
        return self._pipeline.get_stats()


# ─────────────────────────────────────────────────────────────────────
# Drop-in replacement pour classify_sentiment()
# ─────────────────────────────────────────────────────────────────────

_default_adapter: Optional[SentimentAdapter] = None


def classify_sentiment(
    text: str,
    classifier: Optional[SentimentAdapter] = None,
) -> dict:
    """Drop-in replacement pour core.analysis.sentiment_classifier.classify_sentiment().

    Utilise le SentimentPipeline v3 avec mapping 3→5 classes.

    Pour activer dans absa_engine.py, changer :
        from core.analysis.sentiment_classifier import classify_sentiment
    en :
        from core.analysis.sentiment_adapter import classify_sentiment
    """
    global _default_adapter

    if classifier is not None:
        return classifier.predict(text)

    if _default_adapter is None:
        _default_adapter = SentimentAdapter()

    return _default_adapter.predict(text)
