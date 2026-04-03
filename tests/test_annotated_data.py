"""Tests des helpers de normalisation du dataset annote pour l'UI."""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui_helpers.annotated_data import normalize_annotated_dataframe  # noqa: E402


def test_normalize_annotated_dataframe_derive_aspect_depuis_aspects() -> None:
    """La colonne aspect doit etre derivee depuis aspects quand elle manque."""
    dataframe = pd.DataFrame(
        [
            {
                "text": "signal test",
                "timestamp": "2026-04-01T10:00:00",
                "sentiment_label": "positif",
                "channel": "facebook",
                "aspects": ["prix", "gout"],
            }
        ]
    )

    normalized = normalize_annotated_dataframe(dataframe)

    assert "aspect" in normalized.columns
    assert normalized.iloc[0]["aspect"] == "prix"


def test_normalize_annotated_dataframe_derive_aspect_depuis_aspect_sentiments() -> None:
    """La colonne aspect doit etre reconstruite depuis aspect_sentiments si besoin."""
    dataframe = pd.DataFrame(
        [
            {
                "text": "signal test",
                "timestamp": "2026-04-01T10:00:00",
                "sentiment_label": "positif",
                "channel": "facebook",
                "aspect_sentiments": [{"aspect": "emballage", "sentiment": "negatif"}],
            }
        ]
    )

    normalized = normalize_annotated_dataframe(dataframe)

    assert normalized.iloc[0]["aspect"] == "emballage"


def test_normalize_annotated_dataframe_normalise_timestamp_et_wilaya() -> None:
    """La normalisation UI doit parser timestamp et nettoyer wilaya."""
    dataframe = pd.DataFrame(
        [
            {
                "text": "signal test",
                "timestamp": "2026-04-01T10:00:00",
                "sentiment_label": "positif",
                "channel": "facebook",
                "aspect": None,
                "wilaya": "  Oran ",
            }
        ]
    )

    normalized = normalize_annotated_dataframe(dataframe)

    assert str(normalized["timestamp"].dtype).startswith("datetime64")
    assert normalized.iloc[0]["wilaya"] == "oran"
    assert normalized.iloc[0]["aspect"] == ""
