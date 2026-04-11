"""Adapter ABSA context-aware pour RamyPulse.

Remplace la logique de sentiment par aspect de absa_engine.py en ajoutant
la propagation du contexte global vers les aspects individuels.

Problème résolu :
    Dans absa_engine.py, chaque aspect reçoit le sentiment de sa phrase isolée.
    Si le sarcasme est détecté au niveau global mais pas dans la phrase isolée
    de l'aspect, l'aspect est mal classé (faux positif).

Solution — Global-to-Aspect Propagation (inspirée de GCNet / Arctic-ABSA) :
    1. On calcule le sentiment GLOBAL du texte complet via le pipeline v3
       (DziriBERT + lexicon + sliding window + Gemini arbitrage)
    2. Pour chaque aspect :
       a) Si le commentaire = 1 phrase → aspect hérite du global directement
       b) Si multi-phrase → on classifie la phrase isolée de l'aspect
          - Conflit (global négatif + local positif) + confiance locale < 0.70
            → sarcasme cross-phrase probable → propager le global
          - Sinon (confiance locale forte ou pas de conflit)
            → opinion spécifique légitime → garder le local
    Cas légitime préservé : "El prix raisonnable. Bla goût."
       → prix=positif (gardé), goût=négatif, global=négatif

Ce fichier ne modifie AUCUN fichier existant du repo.
Pour activer l'adapter, changer l'import dans normalizer_pipeline.py :
    from core.analysis.absa_adapter import analyze_text

Usage standalone :
    from core.analysis.absa_adapter import analyze_text
    result = analyze_text("ممتاز هاد الطعم ممتاز خلاني مريض 3 يام")
    # → {"global_sentiment": "très_négatif", "aspects": ["goût"],
    #    "aspect_sentiments": [{"aspect": "goût", "sentiment": "très_négatif",
    #    "propagated": True, "reason": "global_override_sarcasm"}]}
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from core.analysis.aspect_extractor import extract_aspects

try:
    from core.analysis.sentiment_adapter import classify_sentiment, SentimentAdapter
except ImportError:
    # Fallback vers le classifieur original si l'adapter sentiment n'est pas dispo
    from core.analysis.sentiment_classifier import classify_sentiment
    SentimentAdapter = None

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Labels considérés comme "positifs" et "négatifs" dans le système 5-classes
# ─────────────────────────────────────────────────────────────────────

_POSITIVE_LABELS = {"très_positif", "positif"}
_NEGATIVE_LABELS = {"très_négatif", "négatif"}


# ─────────────────────────────────────────────────────────────────────
# Fonctions utilitaires (reproduites de absa_engine.py pour rester séparé)
# ─────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────
# Logique de propagation Global → Aspect
# ─────────────────────────────────────────────────────────────────────

def _should_propagate_global(global_label: str, aspect_label: str) -> bool:
    """Détermine si le sentiment global doit écraser le sentiment de l'aspect.

    Règle : GLOBAL négatif + ASPECT positif = conflit sarcasme → propagation.
    Tous les autres cas sont cohérents ou légitimes.
    """
    return global_label in _NEGATIVE_LABELS and aspect_label in _POSITIVE_LABELS


def _build_aspect_sentiments_context_aware(
    text: str,
    aspect_mentions: list[dict[str, object]],
    global_classification: dict,
) -> list[dict[str, object]]:
    """Construit les annotations de sentiment par aspect avec propagation contextuelle.

    Pour chaque aspect :
    1. Classifie la phrase isolée de l'aspect (sentiment local)
    2. Compare avec le sentiment global du texte complet
    3. Si conflit (global négatif + local positif) → propage le global
    """
    global_label = global_classification["label"]
    global_confidence = global_classification["confidence"]
    global_method = global_classification.get("method", "unknown")

    annotations = []
    for mention in aspect_mentions:
        sentence = _extract_sentence_for_span(text, int(mention["start"]), int(mention["end"]))

        is_single_sentence = sentence.strip() == text.strip()

        if is_single_sentence:
            # Texte = 1 seule phrase → le global EST le local
            # Si conflit (global négatif + aspect positif dans la même phrase),
            # c'est du sarcasme → propager le global
            annotations.append({
                "aspect": mention["aspect"],
                "mention": mention["mention"],
                "sentiment": global_label,
                "confidence": global_confidence,
                "propagated": False,
                "reason": "sentence_is_full_text",
            })
            continue

        # ── Multi-phrase : l'aspect a sa propre phrase distincte ──
        # Classifier la phrase isolée de l'aspect
        local_classification = classify_sentiment(sentence)
        local_label = local_classification["label"]
        local_confidence = local_classification["confidence"]

        # Propagation UNIQUEMENT si l'aspect n'a pas de sentiment propre
        # explicite (phrase trop courte / neutre) et que le global est négatif
        # → indique un sarcasme cross-phrase
        #
        # Si l'aspect a un sentiment LOCAL clair (positif OU négatif),
        # on le garde : c'est une opinion spécifique à cet aspect.
        # Ex: "El prix raisonnable. Bla goût." → prix=positif (garder), goût=négatif
        if _should_propagate_global(global_label, local_label) and local_confidence < 0.70:
            # Conflit + faible confiance locale → sarcasme cross-phrase probable
            logger.info(
                "ABSA propagation: aspect '%s' local=%s (%.2f) → global=%s (%.2f) [%s]",
                mention["aspect"], local_label, local_confidence,
                global_label, global_confidence, global_method,
            )
            annotations.append({
                "aspect": mention["aspect"],
                "mention": mention["mention"],
                "sentiment": global_label,
                "confidence": global_confidence,
                "propagated": True,
                "reason": "global_override_sarcasm",
                "local_sentiment": local_label,
                "local_confidence": local_confidence,
            })
        else:
            # Pas de conflit OU confiance locale forte → garder le local
            annotations.append({
                "aspect": mention["aspect"],
                "mention": mention["mention"],
                "sentiment": local_label,
                "confidence": local_confidence,
                "propagated": False,
                "reason": "local_confident" if local_confidence >= 0.70 else "local_consistent",
            })

    return annotations


# ─────────────────────────────────────────────────────────────────────
# API publique — drop-in replacement pour absa_engine.analyze_text
# ─────────────────────────────────────────────────────────────────────

def analyze_text(text: str, aspects: list[str] | None = None) -> dict[str, object]:
    """Analyse un texte unique avec propagation de contexte global → aspects.

    Drop-in replacement pour absa_engine.analyze_text().
    Même interface de sortie, champs additionnels pour debug.
    """
    safe_text = str(text or "")

    # 1. Sentiment global (pipeline v3 complet : sarcasm-aware)
    global_classification = classify_sentiment(safe_text)

    # 2. Extraction des aspects
    aspect_mentions = extract_aspects(safe_text)
    unique_aspects = _deduplicate_aspects(aspect_mentions)

    # 3. Sentiment par aspect avec propagation contextuelle
    aspect_sentiments = _build_aspect_sentiments_context_aware(
        safe_text, aspect_mentions, global_classification,
    )

    # 4. Filtrer si aspects spécifiques demandés
    if aspects:
        requested = {str(item) for item in aspects}
        unique_aspects = [a for a in unique_aspects if a in requested]
        aspect_sentiments = [
            item for item in aspect_sentiments
            if str(item.get("aspect")) in requested
        ]

    return {
        "global_sentiment": global_classification["label"],
        "confidence": global_classification["confidence"],
        "aspects": unique_aspects,
        "aspect_sentiments": aspect_sentiments,
    }


def run_absa_pipeline_context_aware(
    dataframe,
    output_path=None,
    persist_output: bool = True,
):
    """Version context-aware de absa_engine.run_absa_pipeline().

    Même interface, même sortie, mais avec propagation global → aspect.
    """
    import pandas as pd
    from pathlib import Path

    working = dataframe.copy()
    sentiment_labels = []
    confidences = []
    aspects_column = []
    aspect_sentiments_column = []

    for row in working.itertuples(index=False):
        text = getattr(row, "text", "")
        analysis = analyze_text(text)

        sentiment_labels.append(analysis["global_sentiment"])
        confidences.append(analysis["confidence"])
        aspects_column.append(analysis["aspects"])
        aspect_sentiments_column.append(analysis["aspect_sentiments"])

    working["sentiment_label"] = sentiment_labels
    working["confidence"] = confidences
    working["aspects"] = aspects_column
    working["aspect_sentiments"] = aspect_sentiments_column

    final_columns = [
        "text", "channel", "source_url", "timestamp",
        "sentiment_label", "confidence", "aspects", "aspect_sentiments",
    ]
    result = working.loc[:, [c for c in final_columns if c in working.columns]]

    if persist_output:
        output = Path(output_path) if output_path else Path("data/processed/annotated.parquet")
        output.parent.mkdir(parents=True, exist_ok=True)
        result.to_parquet(output, index=False)

    return result
