"""Calcul du Net Sentiment Score (NSS) pour RamyPulse."""
import logging

import pandas as pd

logger = logging.getLogger(__name__)

# Classes positives et négatives selon le standard RamyPulse
CLASSES_POSITIVES = {"positif", "très_positif"}
CLASSES_NEGATIVES = {"négatif", "très_négatif"}


def calculate_nss(df: pd.DataFrame) -> float:
    """Calcule le NSS global sur un DataFrame ABSA.

    Formule: NSS = (nb_très_positif + nb_positif - nb_négatif - nb_très_négatif) / total × 100

    Args:
        df: DataFrame avec colonne 'sentiment_label'.

    Returns:
        NSS entre -100.0 et 100.0. Retourne 0.0 si DataFrame vide.
    """
    if df.empty:
        return 0.0
    total = len(df)
    nb_positifs = int(df["sentiment_label"].isin(CLASSES_POSITIVES).sum())
    nb_negatifs = int(df["sentiment_label"].isin(CLASSES_NEGATIVES).sum())
    nss = (nb_positifs - nb_negatifs) / total * 100
    logger.debug(
        "NSS calculé: %.2f (pos=%d, neg=%d, total=%d)", nss, nb_positifs, nb_negatifs, total
    )
    return round(float(nss), 2)


def calculate_nss_by_channel(df: pd.DataFrame) -> dict:
    """Calcule le NSS par canal de collecte.

    Args:
        df: DataFrame avec colonnes 'sentiment_label' et 'channel'.

    Returns:
        Dict {canal: nss_value} pour chaque canal présent dans df.
    """
    if df.empty:
        return {}
    result = {}
    for channel, group in df.groupby("channel"):
        result[str(channel)] = calculate_nss(group)
    return result


def calculate_nss_by_aspect(df: pd.DataFrame) -> dict:
    """Calcule le NSS par aspect produit.

    Args:
        df: DataFrame avec colonnes 'sentiment_label' et 'aspect'.

    Returns:
        Dict {aspect: nss_value} pour chaque aspect présent dans df.
    """
    if df.empty:
        return {}
    result = {}
    for aspect, group in df.groupby("aspect"):
        result[str(aspect)] = calculate_nss(group)
    return result
