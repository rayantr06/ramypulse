"""Tests unitaires pour le calculateur NSS RamyPulse."""

from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.analysis.nss_calculator import calculate_nss


def build_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Construit un DataFrame de test au format attendu par le calculateur."""
    return pd.DataFrame(rows, columns=["text", "sentiment_label", "channel", "aspect", "source_url", "timestamp"])


def test_returns_plus_100_for_all_positive_rows() -> None:
    """Vérifie qu'un dataset totalement positif donne un NSS de +100."""
    df = build_dataframe(
        [
            {
                "text": "a",
                "sentiment_label": "positif",
                "channel": "facebook",
                "aspect": "goût",
                "source_url": "https://x/1",
                "timestamp": "2026-01-01",
            },
            {
                "text": "b",
                "sentiment_label": "très_positif",
                "channel": "youtube",
                "aspect": "prix",
                "source_url": "https://x/2",
                "timestamp": "2026-01-02",
            },
        ]
    )

    result = calculate_nss(df)

    assert result["nss_global"] == pytest.approx(100.0)
    assert result["volume_total"] == 2


def test_returns_minus_100_for_all_negative_rows() -> None:
    """Vérifie qu'un dataset totalement négatif donne un NSS de -100."""
    df = build_dataframe(
        [
            {
                "text": "a",
                "sentiment_label": "négatif",
                "channel": "facebook",
                "aspect": "goût",
                "source_url": "https://x/1",
                "timestamp": "2026-01-01",
            },
            {
                "text": "b",
                "sentiment_label": "très_négatif",
                "channel": "youtube",
                "aspect": "prix",
                "source_url": "https://x/2",
                "timestamp": "2026-01-02",
            },
        ]
    )

    result = calculate_nss(df)

    assert result["nss_global"] == pytest.approx(-100.0)


def test_returns_zero_for_balanced_positive_and_negative_rows() -> None:
    """Vérifie qu'un jeu 50/50 produit un NSS nul."""
    df = build_dataframe(
        [
            {
                "text": "a",
                "sentiment_label": "positif",
                "channel": "facebook",
                "aspect": "goût",
                "source_url": "https://x/1",
                "timestamp": "2026-01-01",
            },
            {
                "text": "b",
                "sentiment_label": "négatif",
                "channel": "youtube",
                "aspect": "prix",
                "source_url": "https://x/2",
                "timestamp": "2026-01-02",
            },
        ]
    )

    result = calculate_nss(df)

    assert result["nss_global"] == pytest.approx(0.0)


def test_includes_neutral_rows_in_denominator() -> None:
    """Vérifie la formule exacte en présence de lignes neutres."""
    df = build_dataframe(
        [
            {
                "text": "a",
                "sentiment_label": "positif",
                "channel": "facebook",
                "aspect": "goût",
                "source_url": "https://x/1",
                "timestamp": "2026-01-01",
            },
            {
                "text": "b",
                "sentiment_label": "très_positif",
                "channel": "facebook",
                "aspect": "goût",
                "source_url": "https://x/2",
                "timestamp": "2026-01-02",
            },
            {
                "text": "c",
                "sentiment_label": "neutre",
                "channel": "youtube",
                "aspect": "prix",
                "source_url": "https://x/3",
                "timestamp": "2026-01-03",
            },
            {
                "text": "d",
                "sentiment_label": "négatif",
                "channel": "youtube",
                "aspect": "prix",
                "source_url": "https://x/4",
                "timestamp": "2026-01-04",
            },
        ]
    )

    result = calculate_nss(df)

    assert result["nss_global"] == pytest.approx(25.0)
    assert result["distribution"] == {
        "très_positif": 1,
        "positif": 1,
        "neutre": 1,
        "négatif": 1,
        "très_négatif": 0,
    }


def test_handles_empty_dataframe_without_crashing() -> None:
    """Vérifie qu'un DataFrame vide produit une structure de sortie valide."""
    df = build_dataframe([])

    result = calculate_nss(df)

    assert result["nss_global"] == 0.0
    assert result["volume_total"] == 0
    assert result["nss_by_channel"] == {}
    assert result["nss_by_aspect"] == {}
    assert result["distribution"] == {
        "très_positif": 0,
        "positif": 0,
        "neutre": 0,
        "négatif": 0,
        "très_négatif": 0,
    }
    assert result["trends"].empty


def test_calculates_nss_by_channel() -> None:
    """Vérifie le calcul du NSS indépendant pour chaque canal."""
    df = build_dataframe(
        [
            {
                "text": "a",
                "sentiment_label": "positif",
                "channel": "facebook",
                "aspect": "goût",
                "source_url": "https://x/1",
                "timestamp": "2026-01-01",
            },
            {
                "text": "b",
                "sentiment_label": "négatif",
                "channel": "youtube",
                "aspect": "goût",
                "source_url": "https://x/2",
                "timestamp": "2026-01-01",
            },
            {
                "text": "c",
                "sentiment_label": "très_positif",
                "channel": "facebook",
                "aspect": "prix",
                "source_url": "https://x/3",
                "timestamp": "2026-01-02",
            },
        ]
    )

    result = calculate_nss(df)

    assert result["nss_by_channel"] == {
        "facebook": pytest.approx(100.0),
        "youtube": pytest.approx(-100.0),
    }


def test_calculates_nss_by_aspect() -> None:
    """Vérifie le calcul du NSS indépendant pour chaque aspect."""
    df = build_dataframe(
        [
            {
                "text": "a",
                "sentiment_label": "positif",
                "channel": "facebook",
                "aspect": "goût",
                "source_url": "https://x/1",
                "timestamp": "2026-01-01",
            },
            {
                "text": "b",
                "sentiment_label": "très_négatif",
                "channel": "youtube",
                "aspect": "prix",
                "source_url": "https://x/2",
                "timestamp": "2026-01-02",
            },
            {
                "text": "c",
                "sentiment_label": "neutre",
                "channel": "facebook",
                "aspect": "prix",
                "source_url": "https://x/3",
                "timestamp": "2026-01-02",
            },
        ]
    )

    result = calculate_nss(df)

    assert result["nss_by_aspect"] == {
        "goût": pytest.approx(100.0),
        "prix": pytest.approx(-50.0),
    }


def test_groups_trends_by_week() -> None:
    """Vérifie le groupement temporel hebdomadaire du NSS."""
    df = build_dataframe(
        [
            {
                "text": "a",
                "sentiment_label": "positif",
                "channel": "facebook",
                "aspect": "goût",
                "source_url": "https://x/1",
                "timestamp": "2026-01-05",
            },
            {
                "text": "b",
                "sentiment_label": "négatif",
                "channel": "facebook",
                "aspect": "goût",
                "source_url": "https://x/2",
                "timestamp": "2026-01-06",
            },
            {
                "text": "c",
                "sentiment_label": "très_positif",
                "channel": "youtube",
                "aspect": "prix",
                "source_url": "https://x/3",
                "timestamp": "2026-01-13",
            },
        ]
    )

    result = calculate_nss(df)
    trends = result["trends"]

    assert list(trends["week_start"].dt.strftime("%Y-%m-%d")) == ["2026-01-05", "2026-01-12"]
    assert list(trends["nss"]) == pytest.approx([0.0, 100.0])
    assert list(trends["volume_total"]) == [2, 1]
