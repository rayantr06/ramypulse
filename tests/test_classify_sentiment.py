"""Tests TDD pour scripts/03_classify_sentiment.py.

Teste: chargement clean.parquet, pipeline ABSA, sortie annotated.parquet,
logging du résumé.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.analysis import absa_engine
from core.business_catalog import CompetitorCatalog, ProductCatalog, WilayaCatalog
from core.database import DatabaseManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_clean_parquet(path: Path, n: int = 5) -> Path:
    """Crée un fichier clean.parquet minimal."""
    rows = [
        {
            "text": f"Le jus Ramy est bon numéro {i}",
            "text_original": f"Le jus Ramy est bon numéro {i}",
            "channel": "facebook",
            "source_url": f"http://fb/{i}",
            "timestamp": "2026-01-01",
            "script_detected": "latin",
            "language": "french",
        }
        for i in range(n)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _fake_classifier(text: str) -> dict:
    """Classifieur de sentiment déterministe pour les tests."""
    return {"label": "positif", "confidence": 0.85, "logits": [0.1, 0.6, 0.1, 0.1, 0.1]}


def _fake_extractor(text: str) -> list:
    """Extracteur d'aspects déterministe pour les tests."""
    if "bon" in text.lower():
        return [{"aspect": "goût", "mention": "bon", "start": text.lower().index("bon"), "end": text.lower().index("bon") + 3}]
    return []


def _make_catalog_db(path: Path) -> Path:
    """Cree un catalogue SQLite minimal pour les tests d'enrichissement."""
    database = DatabaseManager(path)
    database.create_tables()

    products = ProductCatalog(database)
    products.create(
        brand="Ramy",
        product_name="Jus Orange",
        product_line="Classic",
        sku="RAMY-JO-001",
        keywords_fr=["jus orange"],
        keywords_arabizi=["3assir bortokal"],
    )

    competitors = CompetitorCatalog(database)
    competitors.create(
        brand_name="Hamoud Boualem",
        category="soda",
        keywords_fr=["hamoud boualem"],
        keywords_arabizi=["hamoud"],
    )

    wilayas = WilayaCatalog(database)
    wilayas.create(
        wilaya_code="06",
        wilaya_name_fr="Béjaïa",
        wilaya_name_ar="بجاية",
        keywords_arabizi=["bejaia"],
        region="Est",
    )

    database.close()
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_classify_produit_annotated_parquet(monkeypatch, tmp_path: Path) -> None:
    """classify_sentiment doit produire un fichier annotated.parquet."""
    from scripts.classify_sentiment_03 import classify_sentiment

    clean = _make_clean_parquet(tmp_path / "clean.parquet")
    output = tmp_path / "annotated.parquet"

    monkeypatch.setattr(absa_engine, "classify_sentiment", _fake_classifier)
    monkeypatch.setattr(absa_engine, "extract_aspects", _fake_extractor)

    result = classify_sentiment(input_path=clean, output_path=output)

    assert output.exists()
    assert len(result) == 5


def test_output_contient_colonnes_absa(monkeypatch, tmp_path: Path) -> None:
    """La sortie doit contenir les colonnes ABSA: sentiment_label, confidence, aspects, aspect_sentiments."""
    from scripts.classify_sentiment_03 import classify_sentiment

    clean = _make_clean_parquet(tmp_path / "clean.parquet", 2)
    output = tmp_path / "annotated.parquet"

    monkeypatch.setattr(absa_engine, "classify_sentiment", _fake_classifier)
    monkeypatch.setattr(absa_engine, "extract_aspects", _fake_extractor)

    result = classify_sentiment(input_path=clean, output_path=output)

    required = {"text", "channel", "source_url", "timestamp", "sentiment_label", "confidence", "aspects", "aspect_sentiments"}
    assert required.issubset(set(result.columns))


def test_output_contient_colonnes_entites(monkeypatch, tmp_path: Path) -> None:
    """La sortie doit contenir les colonnes metier enrichies meme sans match."""
    from scripts.classify_sentiment_03 import classify_sentiment

    clean = _make_clean_parquet(tmp_path / "clean.parquet", 2)
    output = tmp_path / "annotated.parquet"

    monkeypatch.setattr(absa_engine, "classify_sentiment", _fake_classifier)
    monkeypatch.setattr(absa_engine, "extract_aspects", _fake_extractor)

    result = classify_sentiment(input_path=clean, output_path=output)

    required = {"brand", "product", "product_line", "sku", "wilaya", "competitor"}
    assert required.issubset(set(result.columns))


def test_classify_enrichit_avec_entity_resolver(monkeypatch, tmp_path: Path) -> None:
    """Le pipeline doit enrichir l'annotated.parquet avec le catalogue SQLite."""
    from scripts.classify_sentiment_03 import classify_sentiment

    clean = tmp_path / "clean.parquet"
    rows = [
        {
            "text": "Le jus orange Ramy est bon a Béjaïa",
            "text_original": "Le jus orange Ramy est bon a Béjaïa",
            "channel": "facebook",
            "source_url": "http://fb/1",
            "timestamp": "2026-01-01",
            "script_detected": "latin",
            "language": "french",
        },
        {
            "text": "hamoud boualem trop sucre",
            "text_original": "hamoud boualem trop sucre",
            "channel": "facebook",
            "source_url": "http://fb/2",
            "timestamp": "2026-01-02",
            "script_detected": "latin",
            "language": "french",
        },
    ]
    pd.DataFrame(rows).to_parquet(clean, index=False)
    catalog_db = _make_catalog_db(tmp_path / "catalog.db")

    monkeypatch.setattr(absa_engine, "classify_sentiment", _fake_classifier)
    monkeypatch.setattr(absa_engine, "extract_aspects", _fake_extractor)

    result = classify_sentiment(
        input_path=clean,
        output_path=tmp_path / "annotated.parquet",
        catalog_db_path=catalog_db,
    )

    assert result.loc[0, "brand"] == "Ramy"
    assert result.loc[0, "product"] == "Jus Orange"
    assert result.loc[0, "wilaya"] == "06"
    assert result.loc[1, "competitor"] == "Hamoud Boualem"


def test_chaque_ligne_a_un_sentiment_label(monkeypatch, tmp_path: Path) -> None:
    """Chaque ligne doit avoir un sentiment_label non nul."""
    from scripts.classify_sentiment_03 import classify_sentiment
    from config import SENTIMENT_LABELS

    clean = _make_clean_parquet(tmp_path / "clean.parquet", 3)

    monkeypatch.setattr(absa_engine, "classify_sentiment", _fake_classifier)
    monkeypatch.setattr(absa_engine, "extract_aspects", _fake_extractor)

    result = classify_sentiment(input_path=clean, output_path=tmp_path / "out.parquet")

    assert all(result["sentiment_label"].isin(SENTIMENT_LABELS))


def test_log_resume_volume(monkeypatch, tmp_path: Path, caplog) -> None:
    """Le script doit logger le résumé: volume traité."""
    from scripts.classify_sentiment_03 import classify_sentiment
    import logging

    clean = _make_clean_parquet(tmp_path / "clean.parquet", 4)

    monkeypatch.setattr(absa_engine, "classify_sentiment", _fake_classifier)
    monkeypatch.setattr(absa_engine, "extract_aspects", _fake_extractor)

    with caplog.at_level(logging.INFO):
        classify_sentiment(input_path=clean, output_path=tmp_path / "out.parquet")

    log_text = caplog.text.lower()
    assert "4" in log_text or "volume" in log_text


def test_fichier_vide_ne_crashe_pas(monkeypatch, tmp_path: Path) -> None:
    """Un clean.parquet vide ne doit pas lever d'exception."""
    from scripts.classify_sentiment_03 import classify_sentiment

    clean = tmp_path / "clean.parquet"
    pd.DataFrame(columns=["text", "channel", "source_url", "timestamp"]).to_parquet(clean, index=False)

    monkeypatch.setattr(absa_engine, "classify_sentiment", _fake_classifier)
    monkeypatch.setattr(absa_engine, "extract_aspects", _fake_extractor)

    result = classify_sentiment(input_path=clean, output_path=tmp_path / "out.parquet")

    assert len(result) == 0
    assert {"brand", "product", "product_line", "sku", "wilaya", "competitor"}.issubset(
        set(result.columns)
    )
