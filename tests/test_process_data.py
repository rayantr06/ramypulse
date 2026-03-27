"""Tests TDD pour scripts/02_process_data.py.

Teste: chargement raw, normalisation, filtrage, déduplication, schéma de sortie.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw_parquet(path: Path, rows: list[dict]) -> Path:
    """Crée un fichier Parquet brut dans le répertoire donné."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _sample_rows(n: int = 5, channel: str = "facebook", prefix: str = "fb") -> list[dict]:
    """Génère n lignes brutes avec un texte valide (>3 mots)."""
    return [
        {
            "text": f"Le jus Ramy est bon {prefix} numéro {i}",
            "channel": channel,
            "source_url": f"http://{prefix}/{i}",
            "timestamp": "2026-01-01",
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests schéma de sortie
# ---------------------------------------------------------------------------

def test_output_contient_colonnes_attendues(tmp_path: Path) -> None:
    """Le fichier clean.parquet doit avoir le schéma PRD attendu."""
    from scripts.process_data_02 import process_data

    raw_dir = tmp_path / "raw"
    _make_raw_parquet(raw_dir / "facebook_raw.parquet", _sample_rows(5))

    result = process_data(raw_dir=raw_dir, output_path=tmp_path / "clean.parquet")

    expected_cols = {"text", "text_original", "channel", "source_url", "timestamp", "script_detected", "language"}
    assert expected_cols.issubset(set(result.columns))


def test_output_sauvegarde_fichier_parquet(tmp_path: Path) -> None:
    """Le fichier clean.parquet doit être créé sur disque."""
    from scripts.process_data_02 import process_data

    raw_dir = tmp_path / "raw"
    _make_raw_parquet(raw_dir / "test.parquet", _sample_rows(3))
    output = tmp_path / "clean.parquet"

    process_data(raw_dir=raw_dir, output_path=output)

    assert output.exists()
    reloaded = pd.read_parquet(output)
    assert len(reloaded) > 0


# ---------------------------------------------------------------------------
# Tests normalisation
# ---------------------------------------------------------------------------

def test_normalisation_appliquee_sur_chaque_texte(tmp_path: Path) -> None:
    """Chaque texte doit être normalisé via normalizer.normalize()."""
    from scripts.process_data_02 import process_data

    raw_dir = tmp_path / "raw"
    _make_raw_parquet(raw_dir / "test.parquet", [
        {"text": "  LE JUS RAMY EST BON  ", "channel": "facebook",
         "source_url": "http://fb/1", "timestamp": "2026-01-01"}
    ])

    result = process_data(raw_dir=raw_dir, output_path=tmp_path / "clean.parquet")

    assert result.iloc[0]["text_original"] == "  LE JUS RAMY EST BON  "
    assert result.iloc[0]["text"] != ""
    assert "script_detected" in result.columns


# ---------------------------------------------------------------------------
# Tests filtrage
# ---------------------------------------------------------------------------

def test_filtre_textes_trop_courts(tmp_path: Path) -> None:
    """Les textes de moins de 3 mots doivent être supprimés."""
    from scripts.process_data_02 import process_data

    raw_dir = tmp_path / "raw"
    rows = [
        {"text": "ok", "channel": "facebook", "source_url": "http://fb/1", "timestamp": "2026-01-01"},
        {"text": "ab", "channel": "facebook", "source_url": "http://fb/2", "timestamp": "2026-01-01"},
        {"text": "Le jus Ramy est excellent vraiment", "channel": "facebook",
         "source_url": "http://fb/3", "timestamp": "2026-01-01"},
    ]
    _make_raw_parquet(raw_dir / "test.parquet", rows)

    result = process_data(raw_dir=raw_dir, output_path=tmp_path / "clean.parquet")

    assert len(result) == 1
    assert "excellent" in result.iloc[0]["text"].lower() or "excellent" in result.iloc[0]["text_original"].lower()


def test_filtre_textes_trop_longs(tmp_path: Path) -> None:
    """Les textes de plus de 500 mots doivent être supprimés."""
    from scripts.process_data_02 import process_data

    raw_dir = tmp_path / "raw"
    long_text = " ".join(["mot"] * 501)
    rows = [
        {"text": long_text, "channel": "facebook", "source_url": "http://fb/1", "timestamp": "2026-01-01"},
        {"text": "Le jus Ramy est bon vraiment", "channel": "facebook",
         "source_url": "http://fb/2", "timestamp": "2026-01-01"},
    ]
    _make_raw_parquet(raw_dir / "test.parquet", rows)

    result = process_data(raw_dir=raw_dir, output_path=tmp_path / "clean.parquet")

    assert len(result) == 1


# ---------------------------------------------------------------------------
# Tests déduplication
# ---------------------------------------------------------------------------

def test_deduplication_supprime_doublons(tmp_path: Path) -> None:
    """Les textes identiques doivent être dédupliqués."""
    from scripts.process_data_02 import process_data

    raw_dir = tmp_path / "raw"
    rows = [
        {"text": "Le jus Ramy est bon", "channel": "facebook",
         "source_url": "http://fb/1", "timestamp": "2026-01-01"},
        {"text": "Le jus Ramy est bon", "channel": "facebook",
         "source_url": "http://fb/2", "timestamp": "2026-01-01"},
        {"text": "Le prix est trop cher vraiment", "channel": "youtube",
         "source_url": "http://yt/1", "timestamp": "2026-01-02"},
    ]
    _make_raw_parquet(raw_dir / "test.parquet", rows)

    result = process_data(raw_dir=raw_dir, output_path=tmp_path / "clean.parquet")

    assert len(result) == 2


# ---------------------------------------------------------------------------
# Tests multi-sources
# ---------------------------------------------------------------------------

def test_charge_plusieurs_fichiers_raw(tmp_path: Path) -> None:
    """process_data doit charger et combiner tous les *.parquet de raw_dir."""
    from scripts.process_data_02 import process_data

    raw_dir = tmp_path / "raw"
    _make_raw_parquet(raw_dir / "facebook_raw.parquet", _sample_rows(3, "facebook", "fb"))
    _make_raw_parquet(raw_dir / "google_raw.parquet", _sample_rows(2, "google_maps", "gm"))

    result = process_data(raw_dir=raw_dir, output_path=tmp_path / "clean.parquet")

    assert len(result) == 5
    assert set(result["channel"].unique()) == {"facebook", "google_maps"}


# ---------------------------------------------------------------------------
# Tests robustesse
# ---------------------------------------------------------------------------

def test_aucun_texte_vide_ou_none_dans_sortie(tmp_path: Path) -> None:
    """Aucun texte vide ou None ne doit rester dans la sortie."""
    from scripts.process_data_02 import process_data

    raw_dir = tmp_path / "raw"
    rows = [
        {"text": "", "channel": "facebook", "source_url": "http://fb/1", "timestamp": "2026-01-01"},
        {"text": None, "channel": "facebook", "source_url": "http://fb/2", "timestamp": "2026-01-01"},
        {"text": "Le jus Ramy est vraiment bon", "channel": "facebook",
         "source_url": "http://fb/3", "timestamp": "2026-01-01"},
    ]
    _make_raw_parquet(raw_dir / "test.parquet", rows)

    result = process_data(raw_dir=raw_dir, output_path=tmp_path / "clean.parquet")

    assert all(result["text"].notna())
    assert all(result["text"].str.strip() != "")


def test_raw_dir_vide_retourne_dataframe_vide(tmp_path: Path) -> None:
    """Si aucun fichier Parquet dans raw_dir, retourner un DataFrame vide."""
    from scripts.process_data_02 import process_data

    raw_dir = tmp_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    result = process_data(raw_dir=raw_dir, output_path=tmp_path / "clean.parquet")

    assert len(result) == 0
