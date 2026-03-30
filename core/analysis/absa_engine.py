"""Orchestration du pipeline ABSA pour RamyPulse."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from core.analysis.aspect_extractor import extract_aspects

try:
    from core.analysis.sentiment_classifier import classify_sentiment
except ModuleNotFoundError:  # pragma: no cover - contrat temporaire jusqu'au merge du classifier
    classify_sentiment = None


def _default_output_path() -> Path:
    """Retourne le chemin de sortie par défaut du parquet annoté."""
    return Path("data") / "processed" / "annotated.parquet"


def _ensure_classifier_available() -> None:
    """Vérifie que le classifieur de sentiment est disponible."""
    if classify_sentiment is None:
        raise RuntimeError(
            "Le module core.analysis.sentiment_classifier est indisponible. "
            "Injecte un mock dans les tests ou merge le classifier avant exécution réelle."
        )


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
        classification = classify_sentiment(sentence)
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
        global_classification = classify_sentiment(text)
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
