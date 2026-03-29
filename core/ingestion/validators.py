"""Validation des données importées pour RamyPulse.

Valide les types, valeurs autorisées et contraintes des colonnes
selon le schéma cible du PRD §9.2 et les constantes de config.py.
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

try:
    from config import CHANNELS, SENTIMENT_LABELS
except ImportError:
    SENTIMENT_LABELS = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]
    CHANNELS = ["facebook", "google_maps", "audio", "youtube"]

_VALID_SENTIMENTS = set(SENTIMENT_LABELS)
_VALID_CHANNELS = set(CHANNELS)


def validate_dataframe(df: pd.DataFrame) -> list[str]:
    """Valide un DataFrame importé contre le schéma RamyPulse.

    Vérifie que les colonnes connues contiennent des valeurs autorisées.
    Ne vérifie que les colonnes présentes — les colonnes manquantes
    ne sont pas des erreurs (elles seront ajoutées plus tard).

    Args:
        df: DataFrame à valider.

    Returns:
        Liste de messages d'erreur. Vide si tout est valide.
    """
    errors: list[str] = []

    if df.empty:
        return errors

    # Valider sentiment_label si présent
    if "sentiment_label" in df.columns:
        invalid_sentiments = set(df["sentiment_label"].dropna().unique()) - _VALID_SENTIMENTS
        if invalid_sentiments:
            errors.append(
                f"Valeurs de sentiment_label invalides : {invalid_sentiments}. "
                f"Valeurs autorisées : {_VALID_SENTIMENTS}"
            )
            logger.warning(
                "Sentiment labels invalides trouvés : %s", invalid_sentiments
            )

    # Valider channel si présent
    if "channel" in df.columns:
        invalid_channels = set(df["channel"].dropna().unique()) - _VALID_CHANNELS
        if invalid_channels:
            errors.append(
                f"Valeurs de channel/canal invalides : {invalid_channels}. "
                f"Valeurs autorisées : {_VALID_CHANNELS}"
            )
            logger.warning(
                "Channels invalides trouvés : %s", invalid_channels
            )

    # Valider confidence si présent (doit être entre 0 et 1)
    if "confidence" in df.columns:
        conf = pd.to_numeric(df["confidence"], errors="coerce")
        out_of_range = ((conf < 0) | (conf > 1)).sum()
        if out_of_range > 0:
            errors.append(
                f"{out_of_range} valeurs de confidence hors de [0, 1]."
            )

    # Valider que text n'est pas entièrement vide
    if "text" in df.columns:
        empty_texts = df["text"].isna().sum() + (df["text"].astype(str).str.strip() == "").sum()
        if empty_texts > 0:
            logger.warning(
                "%d lignes avec texte vide ou NaN détectées.", empty_texts
            )

    return errors
