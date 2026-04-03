"""Tests TDD pour pages/04_whatif.py.

Teste la logique métier extraite en helpers (pas le rendu Streamlit) :
  - build_comparison_chart_data : DataFrame pour le bar chart avant/après par canal
  - nss_label : classification du NSS en texte lisible (excellent/bon/neutre/problématique)
  - delta_color : couleur associée au signe du delta
  - delta_arrow : flèche directionnelle ↑ / ↓ / →
  - build_mock_df : génération du DataFrame mock quand aucune donnée n'est disponible
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui_helpers.whatif_helpers import (  # noqa: E402
    build_comparison_chart_data,
    build_mock_df,
    delta_arrow,
    delta_color,
    nss_label,
)


# ---------------------------------------------------------------------------
# nss_label
# ---------------------------------------------------------------------------

def test_nss_label_excellent() -> None:
    """NSS > 50 → 'Excellent'."""
    assert nss_label(55.0) == "Excellent"


def test_nss_label_bon() -> None:
    """20 < NSS ≤ 50 → 'Bon'."""
    assert nss_label(35.0) == "Bon"
    assert nss_label(20.01) == "Bon"


def test_nss_label_neutre() -> None:
    """0 < NSS ≤ 20 → 'Neutre'."""
    assert nss_label(10.0) == "Neutre"
    assert nss_label(0.01) == "Neutre"


def test_nss_label_problematique() -> None:
    """NSS ≤ 0 → 'Problématique'."""
    assert nss_label(0.0) == "Problématique"
    assert nss_label(-30.0) == "Problématique"


# ---------------------------------------------------------------------------
# delta_color
# ---------------------------------------------------------------------------

def test_delta_color_vert_pour_positif() -> None:
    """Delta > 0 → vert (amélioration)."""
    assert delta_color(5.0) == "#2ecc71"


def test_delta_color_rouge_pour_negatif() -> None:
    """Delta < 0 → rouge (dégradation)."""
    assert delta_color(-3.0) == "#e74c3c"


def test_delta_color_gris_pour_zero() -> None:
    """Delta == 0 → gris (neutralisation)."""
    assert delta_color(0.0) == "#95a5a6"


# ---------------------------------------------------------------------------
# delta_arrow
# ---------------------------------------------------------------------------

def test_delta_arrow_up() -> None:
    """Delta > 0 → '↑'."""
    assert delta_arrow(10.0) == "↑"


def test_delta_arrow_down() -> None:
    """Delta < 0 → '↓'."""
    assert delta_arrow(-2.5) == "↓"


def test_delta_arrow_neutral() -> None:
    """Delta == 0 → '→'."""
    assert delta_arrow(0.0) == "→"


# ---------------------------------------------------------------------------
# build_comparison_chart_data
# ---------------------------------------------------------------------------

def test_chart_data_has_expected_columns() -> None:
    """Le DataFrame pour le chart doit avoir Canal, NSS, Période."""
    nss_avant = {"facebook": 20.0, "google_maps": -10.0}
    nss_apres = {"facebook": 35.0, "google_maps": 5.0}
    df = build_comparison_chart_data(nss_avant, nss_apres)
    assert set(df.columns) == {"Canal", "NSS", "Période"}


def test_chart_data_double_entries_per_channel() -> None:
    """Chaque canal apparaît 2 fois : une 'Actuel', une 'Simulé'."""
    nss_avant = {"facebook": 10.0}
    nss_apres = {"facebook": 30.0}
    df = build_comparison_chart_data(nss_avant, nss_apres)
    assert len(df) == 2
    assert set(df["Période"]) == {"Actuel", "Simulé"}


def test_chart_data_all_channels_present() -> None:
    """Tous les canaux de nss_avant et nss_apres sont représentés."""
    nss_avant = {"facebook": 10.0, "google_maps": 20.0, "audio": 5.0}
    nss_apres = {"facebook": 15.0, "google_maps": 25.0, "audio": 10.0}
    df = build_comparison_chart_data(nss_avant, nss_apres)
    assert set(df[df["Période"] == "Actuel"]["Canal"]) == {"facebook", "google_maps", "audio"}


# ---------------------------------------------------------------------------
# build_mock_df
# ---------------------------------------------------------------------------

def test_mock_df_a_les_colonnes_standard() -> None:
    """Le mock DataFrame doit avoir les 7 colonnes standard RamyPulse."""
    df = build_mock_df()
    colonnes_requises = {"text", "sentiment_label", "channel", "aspect", "source_url", "timestamp", "confidence"}
    assert colonnes_requises.issubset(set(df.columns))


def test_mock_df_non_vide() -> None:
    """Le mock DataFrame ne doit pas être vide."""
    df = build_mock_df()
    assert len(df) > 0


def test_mock_df_contient_les_5_aspects() -> None:
    """Le mock DataFrame doit couvrir les 5 aspects Ramy."""
    df = build_mock_df()
    aspects = set(df["aspect"].unique())
    assert aspects == {"goût", "emballage", "prix", "disponibilité", "fraîcheur"}


def test_mock_df_contient_les_5_sentiments() -> None:
    """Le mock DataFrame doit utiliser les 5 classes de sentiment."""
    df = build_mock_df()
    sentiments = set(df["sentiment_label"].unique())
    assert sentiments == {"très_positif", "positif", "neutre", "négatif", "très_négatif"}
