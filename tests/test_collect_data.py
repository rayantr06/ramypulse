"""Tests PRD pour scripts/01_collect_data.py."""

import importlib.util
import io
import logging
import os
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "01_collect_data.py"
STANDARD_COLUMNS = [
    "text",
    "sentiment_label",
    "channel",
    "aspect",
    "source_url",
    "timestamp",
    "confidence",
]


def _load_module() -> types.ModuleType:
    """Charge dynamiquement le script de collecte."""
    spec = importlib.util.spec_from_file_location("collect_data_01", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _demo_dataframe() -> pd.DataFrame:
    """Construit un petit dataset fallback local pour les tests."""
    return pd.DataFrame(
        {
            "text": ["Avis demo", "Avis demo 2"],
            "sentiment_label": ["positif", "négatif"],
            "channel": ["youtube", "youtube"],
            "aspect": ["goût", "prix"],
            "source_url": ["http://demo/1", "http://demo/2"],
            "timestamp": ["2026-01-01", "2026-01-02"],
            "confidence": [0.9, 0.8],
        }
    )


def test_script_produit_un_parquet_agrégé_depuis_un_fallback_local(tmp_path: pytest.TempPathFactory) -> None:
    """Le script doit produire ``collected_raw.parquet`` à partir d'un fallback local."""
    raw_dir = tmp_path / "raw"
    demo_dir = tmp_path / "demo"
    raw_dir.mkdir()
    demo_dir.mkdir()
    _demo_dataframe().to_parquet(demo_dir / "algerian_45k.parquet", index=False)

    module = _load_module()
    output_path = module.main(raw_dir=raw_dir, demo_dir=demo_dir)

    assert output_path == raw_dir / "collected_raw.parquet"
    assert output_path.exists()


def test_parquet_agrégé_respecte_le_schema_standard(tmp_path: pytest.TempPathFactory) -> None:
    """Le Parquet agrégé doit respecter le schéma standard RamyPulse."""
    raw_dir = tmp_path / "raw"
    demo_dir = tmp_path / "demo"
    raw_dir.mkdir()
    demo_dir.mkdir()
    _demo_dataframe().to_parquet(demo_dir / "algerian_45k.parquet", index=False)

    module = _load_module()
    output_path = module.main(raw_dir=raw_dir, demo_dir=demo_dir)
    dataframe = pd.read_parquet(output_path)

    assert list(dataframe.columns) == STANDARD_COLUMNS
    assert len(dataframe) == 2


def test_sources_existantes_sont_reutilisees_sans_fallback(tmp_path: pytest.TempPathFactory) -> None:
    """Le script doit réutiliser les sources déjà présentes dans data/raw/."""
    raw_dir = tmp_path / "raw"
    demo_dir = tmp_path / "demo"
    raw_dir.mkdir()
    demo_dir.mkdir()

    dataframe = pd.DataFrame(
        {
            "text": ["post facebook"],
            "sentiment_label": ["neutre"],
            "channel": ["facebook"],
            "aspect": ["prix"],
            "source_url": ["http://fb/1"],
            "timestamp": ["2024-06-01"],
            "confidence": [0.8],
        }
    )
    dataframe.to_parquet(raw_dir / "facebook_raw.parquet", index=False)

    module = _load_module()
    output_path = module.main(raw_dir=raw_dir, demo_dir=demo_dir)
    result = pd.read_parquet(output_path)

    assert result["text"].tolist() == ["post facebook"]


def test_resume_de_collecte_est_logge(tmp_path: pytest.TempPathFactory) -> None:
    """Le script doit logger un résumé clair de la collecte."""
    raw_dir = tmp_path / "raw"
    demo_dir = tmp_path / "demo"
    raw_dir.mkdir()
    demo_dir.mkdir()
    _demo_dataframe().to_parquet(demo_dir / "algerian_45k.parquet", index=False)

    module = _load_module()
    capture = io.StringIO()
    handler = logging.StreamHandler(capture)
    module.logger.addHandler(handler)
    module.logger.setLevel(logging.INFO)
    module.logger.propagate = False

    try:
        module.main(raw_dir=raw_dir, demo_dir=demo_dir)
    finally:
        module.logger.removeHandler(handler)

    logs = capture.getvalue()
    assert "RÉSUMÉ COLLECTE" in logs
    assert "Volume" in logs
    assert "Sources" in logs


def test_absence_de_fallback_local_leve_une_erreur_claire(tmp_path: pytest.TempPathFactory) -> None:
    """Sans fallback local disponible, le script doit échouer explicitement."""
    raw_dir = tmp_path / "raw"
    demo_dir = tmp_path / "demo"
    raw_dir.mkdir()
    demo_dir.mkdir()

    module = _load_module()

    with pytest.raises(FileNotFoundError):
        module.main(raw_dir=raw_dir, demo_dir=demo_dir)
