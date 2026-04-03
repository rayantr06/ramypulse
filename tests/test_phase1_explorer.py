"""Tests des helpers Phase 1 pour l'Explorer."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui_helpers.phase1_dashboard_helpers import (  # noqa: E402
    apply_dataframe_filters,
    build_explorer_display_columns,
)


def _sample_dataframe() -> pd.DataFrame:
    """Construit un DataFrame annoté avec colonnes métier."""
    return pd.DataFrame(
        [
            {
                "text": "Ramy orange",
                "timestamp": "2026-03-20T10:00:00",
                "channel": "facebook",
                "aspect": "goût",
                "sentiment_label": "positif",
                "product": "Jus orange",
                "wilaya": "Béjaïa",
                "source_url": "https://example.com/1",
                "confidence": 0.91,
            },
            {
                "text": "Produit indisponible",
                "timestamp": "2026-03-21T11:00:00",
                "channel": "instagram",
                "aspect": "disponibilité",
                "sentiment_label": "négatif",
                "product": "Nectar pêche",
                "wilaya": "Oran",
                "source_url": "https://example.com/2",
                "confidence": 0.73,
            },
        ]
    )


def test_build_explorer_display_columns_ajoute_dimensions_metier() -> None:
    """L'explorer doit afficher produit et wilaya si les colonnes existent."""
    df = _sample_dataframe()

    columns = build_explorer_display_columns(df)

    assert "product" in columns
    assert "wilaya" in columns
    assert columns[:4] == ["text", "sentiment_label", "aspect", "channel"]


def test_build_explorer_display_columns_omet_dimensions_absentes() -> None:
    """L'explorer doit rester stable si produit et wilaya n'existent pas."""
    df = _sample_dataframe().drop(columns=["product", "wilaya"])

    columns = build_explorer_display_columns(df)

    assert "product" not in columns
    assert "wilaya" not in columns
    assert "timestamp" in columns


def test_apply_dataframe_filters_explorer_garde_sentiment_et_aspect() -> None:
    """L'explorer doit pouvoir combiner filtres métier et filtres existants."""
    df = _sample_dataframe()

    filtered = apply_dataframe_filters(
        df,
        {
            "product": ["Nectar pêche"],
            "wilaya": ["Oran"],
            "channel": ["instagram"],
            "aspect": ["disponibilité"],
            "sentiment_label": ["négatif"],
        },
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["text"] == "Produit indisponible"
