"""Tests unitaires pour l'extracteur d'aspects RamyPulse."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core.analysis.aspect_extractor as aspect_extractor
from core.analysis.aspect_extractor import extract_aspects


def test_detects_packaging_aspect_in_french_text() -> None:
    """Vérifie la détection d'un aspect emballage dans un texte simple."""
    text = "l'emballage ytl3 kol mra"

    results = extract_aspects(text)

    assert len(results) == 1
    assert results[0]["aspect"] == "emballage"
    assert results[0]["mention"] == "emballage"
    assert text[results[0]["start"] : results[0]["end"]] == "emballage"


def test_detects_multiple_aspects_in_same_sentence() -> None:
    """Vérifie qu'un texte peut contenir plusieurs aspects distincts."""
    results = extract_aspects("le goût est bon mais ghali bzaf")

    assert [item["aspect"] for item in results] == ["goût", "prix"]
    assert [item["mention"] for item in results] == ["goût", "ghali"]


def test_detects_availability_aspect() -> None:
    """Vérifie la détection de l'aspect disponibilité."""
    results = extract_aspects("ramy disponible partout")

    assert len(results) == 1
    assert results[0]["aspect"] == "disponibilité"
    assert results[0]["mention"] == "disponible"


def test_returns_empty_list_when_no_aspect_is_found() -> None:
    """Vérifie qu'aucun aspect n'est retourné si le texte n'en contient pas."""
    assert extract_aspects("ce commentaire ne parle de rien de précis") == []


def test_detects_multiple_mentions_for_same_and_different_aspects() -> None:
    """Vérifie la détection de plusieurs mentions triées par position."""
    text = "bared mais ghali et bouteille fragile avec date expiration proche"

    results = extract_aspects(text)

    assert [item["aspect"] for item in results] == [
        "fraîcheur",
        "prix",
        "emballage",
        "fraîcheur",
        "fraîcheur",
    ]
    assert [item["mention"] for item in results] == [
        "bared",
        "ghali",
        "bouteille",
        "date",
        "expiration",
    ]
    assert [item["start"] for item in results] == sorted(item["start"] for item in results)


def test_returns_exact_start_and_end_positions() -> None:
    """Vérifie que les positions start et end correspondent à la sous-chaîne."""
    text = "ramy disponible partout"

    results = extract_aspects(text)

    assert results == [
        {
            "aspect": "disponibilité",
            "mention": "disponible",
            "start": 5,
            "end": 15,
        }
    ]


def test_matches_keywords_case_insensitively() -> None:
    """Vérifie que les motifs sont insensibles à la casse."""
    results = extract_aspects("Le GOÛT est BON")

    assert len(results) == 1
    assert results[0]["aspect"] == "goût"
    assert results[0]["mention"] == "GOÛT"


def test_matches_arabic_keywords() -> None:
    """Vérifie la détection avec des mots-clés arabes."""
    results = extract_aspects("السعر مرتفع لكن متوفر")

    assert [item["aspect"] for item in results] == ["prix", "disponibilité"]
    assert [item["mention"] for item in results] == ["السعر", "متوفر"]


def test_supports_underscore_keywords_with_spaces() -> None:
    """Vérifie qu'un mot-clé avec underscore peut matcher une variante espacée."""
    results = extract_aspects("c'est pas cher pour ce jus")

    assert len(results) == 1
    assert results[0]["aspect"] == "prix"
    assert results[0]["mention"] == "pas cher"


def test_ignores_substring_inside_longer_word() -> None:
    """Vérifie qu'un mot-clé n'est pas détecté au milieu d'un mot plus long."""
    assert extract_aspects("disponiblement faux mot") == []


def test_dictionary_is_extensible_via_config_without_code_change(monkeypatch) -> None:
    """Le dictionnaire métier doit pouvoir être enrichi via la configuration."""
    monkeypatch.setattr(
        aspect_extractor.config,
        "ASPECT_KEYWORDS",
        {
            **aspect_extractor.DEFAULT_ASPECT_KEYWORDS,
            "prix": [*aspect_extractor.DEFAULT_ASPECT_KEYWORDS["prix"], "tarifpromo"],
        },
        raising=False,
    )

    results = extract_aspects("tarifpromo sur ramy aujourd'hui")

    assert len(results) == 1
    assert results[0]["aspect"] == "prix"
    assert results[0]["mention"] == "tarifpromo"
