"""Calcul du Net Sentiment Score pour RamyPulse."""

from __future__ import annotations

import logging

import pandas as pd

import config

logger = logging.getLogger(__name__)

DEFAULT_SENTIMENT_LABELS = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]


def _get_sentiment_labels() -> list[str]:
    """Retourne les labels de sentiment configurés ou la liste par défaut."""
    return list(getattr(config, "SENTIMENT_LABELS", DEFAULT_SENTIMENT_LABELS))


def _empty_distribution() -> dict[str, int]:
    """Construit une distribution vide pour les cinq classes de sentiment."""
    return {label: 0 for label in _get_sentiment_labels()}


def _build_distribution(dataframe: pd.DataFrame) -> dict[str, int]:
    """Compte chaque classe de sentiment et complète les labels absents à zéro."""
    distribution = _empty_distribution()
    if dataframe.empty:
        return distribution

    counts = dataframe["sentiment_label"].value_counts()
    for label in distribution:
        distribution[label] = int(counts.get(label, 0))
    return distribution


def _compute_nss_from_distribution(distribution: dict[str, int]) -> float:
    """Calcule le NSS à partir d'une distribution déjà agrégée."""
    total = sum(distribution.values())
    if total == 0:
        return 0.0

    positives = distribution.get("très_positif", 0) + distribution.get("positif", 0)
    negatives = distribution.get("négatif", 0) + distribution.get("très_négatif", 0)
    return ((positives - negatives) / total) * 100.0


def _compute_nss(dataframe: pd.DataFrame) -> float:
    """Calcule le NSS pour un sous-ensemble de données."""
    return _compute_nss_from_distribution(_build_distribution(dataframe))


def _group_nss(dataframe: pd.DataFrame, column: str) -> dict[str, float]:
    """Calcule le NSS pour chaque valeur distincte d'une colonne catégorielle."""
    if dataframe.empty:
        return {}

    grouped_scores = {}
    for value, subset in dataframe.groupby(column, dropna=True):
        if pd.isna(value):
            continue
        grouped_scores[str(value)] = _compute_nss(subset)
    return grouped_scores


def _normalize_aspect_values(value: object) -> list[str]:
    """Normalise une valeur d'aspect scalaire ou multiple vers une liste exploitable."""
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None and not pd.isna(item)]
    if value is None or pd.isna(value):
        return []
    return [str(value)]


def _prepare_aspect_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Prépare une vue explosée des aspects pour le calcul NSS par aspect."""
    if dataframe.empty:
        return dataframe.copy()

    working = dataframe.copy()
    source_column = "aspects" if "aspects" in working.columns else "aspect"
    if source_column not in working.columns:
        return pd.DataFrame(columns=list(working.columns) + ["aspect"])

    working["aspect"] = working[source_column].apply(_normalize_aspect_values)
    working = working.explode("aspect")
    working = working.dropna(subset=["aspect"])
    working["aspect"] = working["aspect"].astype(str).str.strip()
    return working[working["aspect"] != ""]


def _build_trends(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Construit la tendance hebdomadaire du NSS."""
    if dataframe.empty:
        return pd.DataFrame(columns=["week_start", "nss", "volume_total"])

    working = dataframe.copy()
    working["timestamp"] = pd.to_datetime(working["timestamp"], errors="coerce")
    working = working.dropna(subset=["timestamp"])
    if working.empty:
        return pd.DataFrame(columns=["week_start", "nss", "volume_total"])

    working["week_start"] = working["timestamp"].dt.normalize() - pd.to_timedelta(
        working["timestamp"].dt.dayofweek, unit="D"
    )

    weekly = []
    for period_start, subset in working.groupby("week_start", sort=True):
        weekly.append(
            {
                "week_start": pd.Timestamp(period_start),
                "nss": _compute_nss(subset),
                "volume_total": int(len(subset)),
            }
        )

    return (
        pd.DataFrame(weekly, columns=["week_start", "nss", "volume_total"])
        .sort_values("week_start")
        .reset_index(drop=True)
    )


def calculate_nss(dataframe: pd.DataFrame) -> dict[str, object]:
    """Calcule le NSS global, par canal, par aspect et sa tendance temporelle.

    Args:
        dataframe: DataFrame ABSA avec les colonnes standard RamyPulse.

    Returns:
        Dict avec les clés : nss_global, nss_by_channel, nss_by_aspect,
        trends, volume_total, distribution.
    """
    if dataframe.empty:
        return {
            "nss_global": 0.0,
            "nss_by_channel": {},
            "nss_by_aspect": {},
            "trends": _build_trends(dataframe),
            "volume_total": 0,
            "distribution": _empty_distribution(),
        }

    distribution = _build_distribution(dataframe)
    aspect_dataframe = _prepare_aspect_dataframe(dataframe)
    return {
        "nss_global": _compute_nss_from_distribution(distribution),
        "nss_by_channel": _group_nss(dataframe, "channel"),
        "nss_by_aspect": _group_nss(aspect_dataframe, "aspect"),
        "trends": _build_trends(dataframe),
        "volume_total": int(len(dataframe)),
        "distribution": distribution,
    }


def calculate_nss_by_channel(dataframe: pd.DataFrame) -> dict[str, float]:
    """Retourne uniquement le NSS par canal (raccourci pour le simulateur What-If).

    Args:
        dataframe: DataFrame ABSA avec colonnes 'sentiment_label' et 'channel'.

    Returns:
        Dict {canal: nss_value}.
    """
    return _group_nss(dataframe, "channel")


def calculate_nss_by_aspect(dataframe: pd.DataFrame) -> dict[str, float]:
    """Retourne uniquement le NSS par aspect (raccourci pour le simulateur What-If).

    Args:
        dataframe: DataFrame ABSA avec colonnes 'sentiment_label' et 'aspect'.

    Returns:
        Dict {aspect: nss_value}.
    """
    return _group_nss(_prepare_aspect_dataframe(dataframe), "aspect")
