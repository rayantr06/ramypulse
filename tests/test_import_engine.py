"""Tests TDD pour core/ingestion/import_engine.py et core/ingestion/validators.py.

Teste : import CSV/Parquet/Excel, validation schéma, déduplication,
normalisation texte, mapping colonnes, cas limites.
"""

from pathlib import Path

import logging
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ingestion.import_engine import ImportEngine  # noqa: E402
from core.ingestion.validators import validate_dataframe  # noqa: E402


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Crée un CSV valide minimal."""
    path = tmp_path / "sample.csv"
    df = pd.DataFrame({
        "text": [
            "Ramy c'est bon",
            "Le goût est mauvais",
            "Prix raisonnable",
        ],
        "channel": ["facebook", "google_maps", "facebook"],
        "timestamp": ["2026-01-01", "2026-01-02", "2026-01-03"],
    })
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def sample_parquet(tmp_path: Path) -> Path:
    """Crée un Parquet valide."""
    path = tmp_path / "sample.parquet"
    df = pd.DataFrame({
        "text": ["Bnin bzaf", "Ghali bzaf", "Mliha"],
        "channel": ["facebook", "facebook", "google_maps"],
        "sentiment_label": ["positif", "négatif", "positif"],
    })
    df.to_parquet(path, index=False)
    return path


@pytest.fixture
def sample_excel(tmp_path: Path) -> Path:
    """Crée un Excel valide."""
    path = tmp_path / "sample.xlsx"
    df = pd.DataFrame({
        "text": ["Produit super", "Pas frais"],
        "channel": ["facebook", "google_maps"],
    })
    df.to_excel(path, index=False)
    return path


@pytest.fixture
def csv_with_dups(tmp_path: Path) -> Path:
    """CSV avec doublons textuels."""
    path = tmp_path / "dups.csv"
    df = pd.DataFrame({
        "text": [
            "Ramy c'est bon",
            "Ramy c'est bon",
            "Le goût est mauvais",
            "RAMY C'EST BON",
        ],
        "channel": ["facebook", "facebook", "google_maps", "facebook"],
    })
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def csv_custom_columns(tmp_path: Path) -> Path:
    """CSV avec des noms de colonnes non-standards nécessitant un mapping."""
    path = tmp_path / "custom.csv"
    df = pd.DataFrame({
        "commentaire": ["Ramy c'est bon", "Mauvais goût"],
        "source": ["facebook", "youtube"],
        "date_collecte": ["2026-01-01", "2026-01-02"],
    })
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def csv_empty(tmp_path: Path) -> Path:
    """CSV vide (headers seulement)."""
    path = tmp_path / "empty.csv"
    df = pd.DataFrame({"text": [], "channel": []})
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def csv_no_text(tmp_path: Path) -> Path:
    """CSV sans colonne text."""
    path = tmp_path / "no_text.csv"
    df = pd.DataFrame({
        "channel": ["facebook"],
        "sentiment_label": ["positif"],
    })
    df.to_csv(path, index=False)
    return path


def test_import_csv(sample_csv: Path) -> None:
    """Import CSV retourne un DataFrame valide."""
    engine = ImportEngine()
    result = engine.import_file(sample_csv)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert "text" in result.columns


def test_import_parquet(sample_parquet: Path) -> None:
    """Import Parquet retourne un DataFrame valide."""
    engine = ImportEngine()
    result = engine.import_file(sample_parquet)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3


def test_import_excel(sample_excel: Path) -> None:
    """Import Excel retourne un DataFrame valide."""
    engine = ImportEngine()
    result = engine.import_file(sample_excel)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2


def test_auto_detect_format(sample_csv: Path, sample_parquet: Path) -> None:
    """Le format est détecté automatiquement par extension."""
    engine = ImportEngine()
    df_csv = engine.import_file(sample_csv)
    df_pq = engine.import_file(sample_parquet)
    assert len(df_csv) == 3
    assert len(df_pq) == 3


def test_validates_text_column(csv_no_text: Path) -> None:
    """Import sans colonne 'text' lève une erreur."""
    engine = ImportEngine()
    with pytest.raises(ValueError, match="[Tt]ext"):
        engine.import_file(csv_no_text)


def test_empty_file_raises(csv_empty: Path) -> None:
    """Import fichier vide lève une erreur."""
    engine = ImportEngine()
    with pytest.raises(ValueError, match="[Vv]ide|[Ee]mpty|aucun|0"):
        engine.import_file(csv_empty)


def test_file_not_found() -> None:
    """Import fichier inexistant lève une erreur."""
    engine = ImportEngine()
    with pytest.raises(FileNotFoundError):
        engine.import_file(Path("fichier_inexistant.csv"))


def test_unsupported_format(tmp_path: Path) -> None:
    """Import format non supporté lève une erreur."""
    path = tmp_path / "data.json"
    path.write_text('{"text": "hello"}')
    engine = ImportEngine()
    with pytest.raises(ValueError, match="[Ff]ormat|[Ee]xtension"):
        engine.import_file(path)


def test_dedup_removes_exact_duplicates(csv_with_dups: Path) -> None:
    """Les doublons exacts sont supprimés."""
    engine = ImportEngine()
    result = engine.import_file(csv_with_dups)
    assert len(result) < 4


def test_dedup_logs_stats(csv_with_dups: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Les statistiques de dédup sont loggées."""
    engine = ImportEngine()
    with caplog.at_level(logging.INFO):
        engine.import_file(csv_with_dups)
    log_text = " ".join(r.message for r in caplog.records)
    assert any(char.isdigit() for char in log_text)


def test_normalizer_applied_to_text(sample_csv: Path) -> None:
    """Le normalizer est appliqué sur la colonne text."""
    engine = ImportEngine()
    result = engine.import_file(sample_csv)
    assert "text" in result.columns
    assert all(len(str(t)) > 0 for t in result["text"])


def test_column_mapping(csv_custom_columns: Path) -> None:
    """Import avec mapping de colonnes personnalisé."""
    engine = ImportEngine()
    mapping = {
        "commentaire": "text",
        "source": "channel",
        "date_collecte": "timestamp",
    }
    result = engine.import_file(csv_custom_columns, column_mapping=mapping)
    assert "text" in result.columns
    assert "channel" in result.columns
    assert len(result) == 2


def test_batch_id_added(sample_csv: Path) -> None:
    """L'import ajoute un ingestion_batch_id."""
    engine = ImportEngine()
    result = engine.import_file(sample_csv)
    assert "ingestion_batch_id" in result.columns
    assert result["ingestion_batch_id"].nunique() == 1


def test_source_registry_id_propagated(sample_csv: Path) -> None:
    """Le source_registry_id est ajouté si fourni."""
    engine = ImportEngine()
    result = engine.import_file(sample_csv, source_registry_id="src-123")
    assert "source_registry_id" in result.columns
    assert all(result["source_registry_id"] == "src-123")


def test_validate_dataframe_valid() -> None:
    """DataFrame valide passe la validation."""
    df = pd.DataFrame({
        "text": ["bon produit"],
        "channel": ["facebook"],
        "sentiment_label": ["positif"],
    })
    errors = validate_dataframe(df)
    assert len(errors) == 0


def test_validate_dataframe_invalid_sentiment() -> None:
    """Sentiment label invalide détecté."""
    df = pd.DataFrame({
        "text": ["bon produit"],
        "sentiment_label": ["excellent"],
    })
    errors = validate_dataframe(df)
    assert len(errors) > 0
    assert any("sentiment" in e.lower() for e in errors)


def test_validate_dataframe_invalid_channel() -> None:
    """Channel invalide détecté."""
    df = pd.DataFrame({
        "text": ["bon produit"],
        "channel": ["tiktok"],
    })
    errors = validate_dataframe(df)
    assert len(errors) > 0
    assert any("channel" in e.lower() or "canal" in e.lower() for e in errors)
