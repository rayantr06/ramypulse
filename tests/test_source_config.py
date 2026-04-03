"""Tests TDD pour la configuration source partagee."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.connectors.source_config import parse_source_config, validate_source_config  # noqa: E402


def test_parse_source_config_retourne_un_dict_normalise() -> None:
    """Le parseur doit convertir config_json texte en dictionnaire exploitable."""
    source = {
        "platform": "import",
        "config_json": "{\"snapshot_path\": \"data/raw/import.csv\", \"fetch_mode\": \"snapshot\"}",
    }

    config = parse_source_config(source)

    assert config["snapshot_path"] == "data/raw/import.csv"
    assert config["fetch_mode"] == "snapshot"


def test_parse_source_config_rejette_une_config_invalide() -> None:
    """Une config JSON invalide doit etre normalisee en dictionnaire vide."""
    source = {
        "platform": "import",
        "config_json": "{",
    }

    assert parse_source_config(source) == {}


def test_validate_source_config_refuse_facebook_sans_page() -> None:
    """Facebook doit exiger un identifiant ou une URL de page."""
    source = {
        "platform": "facebook",
        "config_json": {"fetch_mode": "snapshot"},
    }

    try:
        validate_source_config(source)
    except ValueError as exc:
        assert "page_id" in str(exc) or "page_url" in str(exc)
    else:
        raise AssertionError("validate_source_config aurait dû lever ValueError")


def test_validate_source_config_ajoute_fetch_mode_snapshot_par_defaut() -> None:
    """Le mode de collecte doit etre normalise et recevoir sa valeur par defaut."""
    source = {
        "platform": "import",
        "config_json": {"snapshot_path": "data/raw/import.csv"},
    }

    config = validate_source_config(source)

    assert config["snapshot_path"] == "data/raw/import.csv"
    assert config["fetch_mode"] == "snapshot"


def test_validate_source_config_rejette_fetch_mode_invalide() -> None:
    """Un fetch_mode inconnu doit etre refuse explicitement."""
    source = {
        "platform": "youtube",
        "config_json": {"channel_id": "channel-001", "fetch_mode": "stream"},
    }

    with pytest.raises(ValueError, match="fetch_mode"):
        validate_source_config(source)
