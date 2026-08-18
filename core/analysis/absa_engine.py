"""Orchestration du pipeline ABSA pour RamyPulse."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import pandas as pd

from core.analysis.aspect_extractor import extract_aspects

logger = logging.getLogger(__name__)

# ── Pipeline hybride DziriBERT (lazy init — chargé au premier appel) ─────────
_pipeline = None


def _get_pipeline():
    """Retourne le pipeline de sentiment (lazy init singleton)."""
    global _pipeline
    if _pipeline is None:
        try:
            from inference.pipeline import SentimentPipeline
            from config import DZIRIBERT_MODEL_PATH
            gemini_key = os.getenv("GOOGLE_API_KEY", "") or None
            _pipeline = SentimentPipeline(
                model_dir=str(DZIRIBERT_MODEL_PATH),
                gemini_api_key=gemini_key,
            )
            logger.info("SentimentPipeline chargé depuis %s", DZIRIBERT_MODEL_PATH)
        except Exception as exc:
            logger.error("Impossible de charger SentimentPipeline : %s", exc)
            raise RuntimeError(
                f"SentimentPipeline indisponible : {exc}. "
                "Vérifier que models/dziribert-sentiment/ existe."
            ) from exc
    return _pipeline


def _map_to_5_classes(label: str, confidence: float) -> str:
    """Convertit les 3 labels DziriBERT (EN) vers les 5 classes RamyPulse (FR).

    DziriBERT retourne : positive | negative | neutral
    RamyPulse attend   : très_positif | positif | neutre | négatif | très_négatif

    Seuil de confiance 0.75 pour distinguer le degré fort du degré modéré.
    """
    if label == "positive":
        return "très_positif" if confidence >= 0.75 else "positif"
    if label == "negative":
        return "très_négatif" if confidence >= 0.75 else "négatif"
    return "neutre"


def _classify(text: str) -> dict:
    """Classe un texte et retourne {'label': str, 'confidence': float}."""
    result = _get_pipeline().predict(text)
    label_5 = _map_to_5_classes(result.label, result.confidence)
    return {"label": label_5, "confidence": result.confidence}


def _default_output_path() -> Path:
    """Retourne le chemin de sortie par défaut du parquet annoté."""
    return Path("data") / "processed" / "annotated.parquet"


def _ensure_classifier_available() -> None:
    """Vérifie que le pipeline de sentiment est chargeable."""
    _get_pipeline()  # lève RuntimeError si indisponible


def _extract_sentence_for_span(text: str, start: int, end: int) -> str:
    """Retourne la phrase qui contient la mention d'aspect ciblée."""
    if not text:
        return ""

    for match in re.finditer(r"[^.!?\u061f\u061b\n]+[.!?\u061f\u061b\n]?", text):
        sentence = match.group(0).strip()
        if not sentence:
            continue
        if match.start() <= start < match.end() and end <= match.end():
            return sentence
    return text.strip()


def _deduplicate_aspects(aspect_mentions: list[dict[str, object]]) -> list[str]:
    """Construit la liste ordonnée des aspects uniques détectés."""
    ordered = []
    for item in aspect_mentions:
        aspect = str(item["aspect"])
        if aspect not in ordered:
            ordered.append(aspect)
    return ordered


def _build_aspect_sentiments(text: str, aspect_mentions: list[dict[str, object]]) -> list[dict[str, object]]:
    """Construit les annotations de sentiment par aspect pour un texte donné."""
    annotations = []
    for mention in aspect_mentions:
        sentence = _extract_sentence_for_span(text, int(mention["start"]), int(mention["end"]))
        classification = _classify(sentence)
        annotations.append(
            {
                "aspect": mention["aspect"],
                "mention": mention["mention"],
                "sentiment": classification["label"],
                "confidence": classification["confidence"],
            }
        )
    return annotations


def run_absa_pipeline(
    dataframe: pd.DataFrame,
    output_path: str | Path | None = None,
    persist_output: bool = True,
) -> pd.DataFrame:
    """Enrichit un DataFrame source avec le sentiment global et les sentiments par aspect."""
    _ensure_classifier_available()

    working = dataframe.copy()
    sentiment_labels = []
    confidences = []
    aspects_column = []
    aspect_sentiments_column = []

    for row in working.itertuples(index=False):
        text = getattr(row, "text", "")
        global_classification = _classify(text)
        aspect_mentions = extract_aspects(text)
        aspect_sentiments = _build_aspect_sentiments(text, aspect_mentions)

        sentiment_labels.append(global_classification["label"])
        confidences.append(global_classification["confidence"])
        aspects_column.append(_deduplicate_aspects(aspect_mentions))
        aspect_sentiments_column.append(aspect_sentiments)

    working["sentiment_label"] = sentiment_labels
    working["confidence"] = confidences
    working["aspects"] = aspects_column
    working["aspect_sentiments"] = aspect_sentiments_column

    final_columns = [
        "text",
        "channel",
        "source_url",
        "timestamp",
        "sentiment_label",
        "confidence",
        "aspects",
        "aspect_sentiments",
    ]
    result = working.loc[:, final_columns]

    if persist_output:
        output = Path(output_path) if output_path is not None else _default_output_path()
        output.parent.mkdir(parents=True, exist_ok=True)
        result.to_parquet(output, index=False)

    return result


def analyze_text(text: str, aspects: list[str] | None = None) -> dict[str, object]:
    """Analyse un texte unique et retourne un payload ABSA unifie.

    Ce wrapper stabilise l'interface pour les futurs jobs de normalisation
    plateforme sans remplacer le pipeline batch existant.
    """
    _ensure_classifier_available()
    safe_text = str(text or "")
    global_classification = _classify(safe_text)
    aspect_mentions = extract_aspects(safe_text)
    unique_aspects = _deduplicate_aspects(aspect_mentions)
    aspect_sentiments = _build_aspect_sentiments(safe_text, aspect_mentions)

    if aspects:
        requested = {str(item) for item in aspects}
        unique_aspects = [aspect for aspect in unique_aspects if aspect in requested]
        aspect_sentiments = [
            item for item in aspect_sentiments if str(item.get("aspect")) in requested
        ]

    return {
        "global_sentiment": global_classification["label"],
        "confidence": global_classification["confidence"],
        "aspects": unique_aspects,
        "aspect_sentiments": aspect_sentiments,
    }
