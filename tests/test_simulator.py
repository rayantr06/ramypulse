"""Tests TDD pour core/whatif/simulator.py.

Vérification manuelle sur petit dataset (10 enregistrements) :
  - NSS actuel = (4 pos - 5 neg) / 10 × 100 = -10.0
  - Neutraliser emballage → NSS ≈ +28.57  (delta > 0)
  - Améliorer goût       → NSS = +20.0   (delta = +30.0)
  - Dégrader prix        → NSS = -30.0   (delta = -20.0)
"""
import sys
import os

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.whatif.simulator import simulate_whatif  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def df_sample() -> pd.DataFrame:
    """Petit dataset ABSA de 10 enregistrements pour les tests.

    Distribution :
      emballage : très_négatif×2, négatif×1  (3 enregistrements — tous négatifs)
      goût      : négatif×2, neutre×1        (3 enregistrements)
      prix      : positif×2, très_positif×1  (3 enregistrements — tous positifs)
      disponib. : positif×1                   (1 enregistrement)
    """
    return pd.DataFrame(
        {
            "text": [f"t{i}" for i in range(10)],
            "sentiment_label": [
                "très_négatif",  # 0 emballage
                "très_négatif",  # 1 emballage
                "négatif",       # 2 emballage
                "négatif",       # 3 goût
                "négatif",       # 4 goût
                "neutre",        # 5 goût
                "positif",       # 6 prix
                "positif",       # 7 prix
                "très_positif",  # 8 prix
                "positif",       # 9 disponibilité
            ],
            "channel": (
                ["facebook"] * 5 + ["google_maps"] * 5
            ),
            "aspect": [
                "emballage", "emballage", "emballage",
                "goût", "goût", "goût",
                "prix", "prix", "prix",
                "disponibilité",
            ],
            "source_url": ["http://x"] * 10,
            "timestamp": ["2024-01-01"] * 10,
            "confidence": [0.9] * 10,
        }
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_output_contient_toutes_les_cles(df_sample: pd.DataFrame) -> None:
    """Le dict retourné doit avoir exactement les 6 clés attendues."""
    result = simulate_whatif("goût", "améliorer", df_sample)
    expected = {
        "nss_actuel",
        "nss_simule",
        "delta",
        "interpretation",
        "affected_count",
        "nss_by_channel_simulated",
    }
    assert set(result.keys()) == expected


def test_neutraliser_emballage_augmente_nss(df_sample: pd.DataFrame) -> None:
    """Neutraliser l'emballage (tout négatif) doit faire monter le NSS."""
    result = simulate_whatif("emballage", "neutraliser", df_sample)

    assert result["affected_count"] == 3
    assert result["nss_actuel"] == pytest.approx(-10.0)
    assert result["nss_simule"] > result["nss_actuel"]
    assert result["delta"] > 0


def test_ameliorer_gout_augmente_nss(df_sample: pd.DataFrame) -> None:
    """Améliorer le goût (2 négatifs + 1 neutre) doit faire monter le NSS."""
    result = simulate_whatif("goût", "améliorer", df_sample)

    assert result["nss_simule"] > result["nss_actuel"]
    assert result["delta"] > 0
    # Vérification numérique : NSS passe de -10 à +20 (delta = +30)
    assert result["nss_simule"] == pytest.approx(20.0)
    assert result["delta"] == pytest.approx(30.0)


def test_degrader_prix_diminue_nss(df_sample: pd.DataFrame) -> None:
    """Dégrader le prix (tout positif) doit faire baisser le NSS."""
    result = simulate_whatif("prix", "dégrader", df_sample)

    assert result["nss_simule"] < result["nss_actuel"]
    assert result["delta"] < 0
    # Vérification numérique : NSS passe de -10 à -30 (delta = -20)
    assert result["nss_simule"] == pytest.approx(-30.0)
    assert result["delta"] == pytest.approx(-20.0)


def test_dataframe_original_non_modifie(df_sample: pd.DataFrame) -> None:
    """simulate_whatif ne doit JAMAIS modifier le DataFrame passé en argument."""
    labels_avant = df_sample["sentiment_label"].tolist()
    len_avant = len(df_sample)

    simulate_whatif("goût", "améliorer", df_sample)

    assert df_sample["sentiment_label"].tolist() == labels_avant
    assert len(df_sample) == len_avant


def test_dataframe_original_non_modifie_neutraliser(df_sample: pd.DataFrame) -> None:
    """Même vérification pour le scénario 'neutraliser' qui supprime des lignes."""
    labels_avant = df_sample["sentiment_label"].tolist()
    len_avant = len(df_sample)

    simulate_whatif("emballage", "neutraliser", df_sample)

    assert len(df_sample) == len_avant
    assert df_sample["sentiment_label"].tolist() == labels_avant


def test_aspect_inexistant_affected_count_zero_delta_zero(df_sample: pd.DataFrame) -> None:
    """Un aspect absent des données doit retourner affected_count=0 et delta=0."""
    result = simulate_whatif("fraîcheur", "améliorer", df_sample)

    assert result["affected_count"] == 0
    assert result["delta"] == pytest.approx(0.0)
    assert result["nss_simule"] == pytest.approx(result["nss_actuel"])


def test_interpretation_contient_nom_aspect(df_sample: pd.DataFrame) -> None:
    """L'interprétation doit mentionner l'aspect ciblé."""
    for aspect in ("goût", "prix", "emballage"):
        result = simulate_whatif(aspect, "améliorer", df_sample)
        assert aspect in result["interpretation"], (
            f"'{aspect}' absent de l'interprétation: {result['interpretation']}"
        )


def test_interpretation_coherente_delta_positif(df_sample: pd.DataFrame) -> None:
    """Pour un delta positif, l'interprétation doit signaler une augmentation."""
    result = simulate_whatif("emballage", "neutraliser", df_sample)

    assert result["delta"] > 0
    interp = result["interpretation"].lower()
    assert any(mot in interp for mot in ("augmenterait", "hausse", "améliore", "monte"))


def test_interpretation_coherente_delta_negatif(df_sample: pd.DataFrame) -> None:
    """Pour un delta négatif, l'interprétation doit signaler une diminution."""
    result = simulate_whatif("prix", "dégrader", df_sample)

    assert result["delta"] < 0
    interp = result["interpretation"].lower()
    assert any(mot in interp for mot in ("diminuerait", "baisse", "dégrade", "descend"))


def test_nss_by_channel_simulated_est_un_dict(df_sample: pd.DataFrame) -> None:
    """nss_by_channel_simulated doit être un dictionnaire."""
    result = simulate_whatif("goût", "améliorer", df_sample)
    assert isinstance(result["nss_by_channel_simulated"], dict)


def test_scenario_invalide_leve_valueerror(df_sample: pd.DataFrame) -> None:
    """Un scénario non reconnu doit lever une ValueError."""
    with pytest.raises(ValueError):
        simulate_whatif("goût", "magique", df_sample)
