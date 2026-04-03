"""Tests des helpers Phase 1 pour le Dashboard."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui_helpers.phase1_dashboard_helpers import (  # noqa: E402
    apply_dataframe_filters,
    build_available_filters,
    missing_filter_columns,
)


def _sample_dataframe() -> pd.DataFrame:
    """Construit un DataFrame minimal avec dimensions métier."""
    return pd.DataFrame(
        [
            {
                "text": "Ramy orange disponible à Béjaïa",
                "timestamp": "2026-03-20T10:00:00",
                "channel": "facebook",
                "aspect": "disponibilité",
                "sentiment_label": "positif",
                "product": "Jus orange",
                "wilaya": "Béjaïa",
            },
            {
                "text": "Le prix à Oran est critiqué",
                "timestamp": "2026-03-21T12:00:00",
                "channel": "instagram",
                "aspect": "prix",
                "sentiment_label": "négatif",
                "product": "Nectar pêche",
                "wilaya": "Oran",
            },
        ]
    )


def test_build_available_filters_inclut_dimensions_metier() -> None:
    """Les options de filtres doivent inclure produit, wilaya et canal quand présents."""
    df = _sample_dataframe()

    options = build_available_filters(df, ["product", "wilaya", "channel"])

    assert options["product"] == ["Jus orange", "Nectar pêche"]
    assert options["wilaya"] == ["Béjaïa", "Oran"]
    assert options["channel"] == ["facebook", "instagram"]


def test_apply_dataframe_filters_sur_dimensions_metier() -> None:
    """Les filtres combinés doivent restreindre le DataFrame correctement."""
    df = _sample_dataframe()

    filtered = apply_dataframe_filters(
        df,
        {
            "product": ["Jus orange"],
            "wilaya": ["Béjaïa"],
            "channel": ["facebook"],
            "date_range": (
                pd.Timestamp("2026-03-20").date(),
                pd.Timestamp("2026-03-20").date(),
            ),
        },
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["product"] == "Jus orange"


def test_missing_filter_columns_signale_dimensions_absentes() -> None:
    """Les colonnes métier absentes doivent être signalées explicitement."""
    df = _sample_dataframe().drop(columns=["product", "wilaya"])

    missing = missing_filter_columns(df, ["product", "wilaya", "channel"])

    assert missing == ["product", "wilaya"]


def test_apply_dataframe_filters_ignore_colonnes_absentes() -> None:
    """Un filtre sur colonne absente ne doit pas casser la page."""
    df = _sample_dataframe().drop(columns=["product"])

    filtered = apply_dataframe_filters(
        df,
        {
            "product": ["Jus orange"],
            "channel": ["facebook"],
        },
    )

    assert len(filtered) == 1
    assert filtered.iloc[0]["channel"] == "facebook"
