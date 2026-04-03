"""Classification de sentiment batch et extraction d'aspects pour RamyPulse.

Charge ``data/processed/clean.parquet``, applique le pipeline ABSA complet,
enrichit les mentions avec l'Entity Resolver, puis sauvegarde
``data/processed/annotated.parquet``.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import pandas as pd

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from core.analysis.absa_engine import run_absa_pipeline
from core.business_catalog import WilayaCatalog
from core.database import DatabaseManager
from core.entity_resolver import EntityResolver
from core.runtime.diagnostics import collect_runtime_diagnostics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_ENTITY_COLUMNS = ["brand", "product", "product_line", "sku", "wilaya", "competitor"]


def _log_summary(dataframe: pd.DataFrame) -> None:
    """Affiche un resume de la classification dans les logs."""
    logger.info("=== RESUME CLASSIFICATION ===")
    logger.info("Volume     : %d textes traites", len(dataframe))

    if "sentiment_label" in dataframe.columns and len(dataframe) > 0:
        distribution = dataframe["sentiment_label"].value_counts().to_dict()
        logger.info("Sentiments : %s", distribution)

    if "aspects" in dataframe.columns and len(dataframe) > 0:
        all_aspects: list[str] = []
        for aspects_list in dataframe["aspects"]:
            if isinstance(aspects_list, list):
                all_aspects.extend(aspects_list)
        unique_aspects = sorted(set(all_aspects))
        logger.info("Aspects    : %s (%d mentions)", unique_aspects, len(all_aspects))

    coverage = {
        column: int(dataframe[column].notna().sum())
        for column in _ENTITY_COLUMNS
        if column in dataframe.columns
    }
    if coverage:
        logger.info("Entites    : %s", coverage)

    logger.info("============================")


def _empty_annotated_frame() -> pd.DataFrame:
    """Construit un DataFrame de sortie vide avec schema enrichi."""
    return pd.DataFrame(
        columns=[
            "text",
            "channel",
            "source_url",
            "timestamp",
            "sentiment_label",
            "confidence",
            "aspects",
            "aspect_sentiments",
            *_ENTITY_COLUMNS,
        ]
    )


def _build_source_metadata_map(dataframe: pd.DataFrame) -> dict[int, dict]:
    """Construit les metadonnees source exploitables par ligne."""
    supported_fields = ("brand", "wilaya", "competitor")
    if not any(field in dataframe.columns for field in supported_fields):
        return {}

    metadata_map: dict[int, dict] = {}
    for index, row in dataframe.iterrows():
        metadata = {}
        for field in supported_fields:
            if field not in dataframe.columns:
                continue
            value = row.get(field)
            if pd.notna(value) and str(value).strip():
                metadata[field] = value
        if metadata:
            metadata_map[index] = metadata
    return metadata_map


def _prepare_entity_resolver(catalog_db_path: Path | str | None) -> tuple[DatabaseManager, EntityResolver]:
    """Initialise la base catalogue et le resolver d'entites."""
    database = DatabaseManager(catalog_db_path)
    database.create_tables()

    if database.connection.execute("SELECT COUNT(*) FROM wilayas").fetchone()[0] == 0:
        inserted = WilayaCatalog(database).seed_from_file()
        logger.info("Entity resolution : seed wilayas auto (%d inserees).", inserted)

    resolver = EntityResolver(database)
    return database, resolver


def _enrich_with_entities(
    annotated: pd.DataFrame,
    source_dataframe: pd.DataFrame,
    catalog_db_path: Path | str | None,
) -> pd.DataFrame:
    """Enrichit la sortie ABSA avec les dimensions metier Phase 1."""
    started_at = time.perf_counter()
    database, resolver = _prepare_entity_resolver(catalog_db_path)
    try:
        metadata_map = _build_source_metadata_map(source_dataframe)
        enriched = resolver.enrich_dataframe(annotated, source_metadata_map=metadata_map)
    finally:
        database.close()

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    coverage = {
        column: int(enriched[column].notna().sum())
        for column in _ENTITY_COLUMNS
    }
    logger.info(
        "Entity resolution : %d lignes enrichies en %.2f ms (%s)",
        len(enriched),
        elapsed_ms,
        coverage,
    )
    return enriched


def classify_sentiment(
    input_path: Path | None = None,
    output_path: Path | None = None,
    catalog_db_path: Path | str | None = None,
) -> pd.DataFrame:
    """Orchestre la classification de sentiment, l'ABSA et l'enrichissement metier.

    Args:
        input_path: Chemin vers le fichier clean.parquet.
        output_path: Chemin de sortie pour annotated.parquet.
        catalog_db_path: Base SQLite catalogue a utiliser pour l'entity resolution.

    Returns:
        DataFrame annote avec sentiment, aspects et dimensions metier.
    """
    input_path = Path(input_path) if input_path is not None else config.PROCESSED_DATA_DIR / "clean.parquet"
    output_path = Path(output_path) if output_path is not None else config.PROCESSED_DATA_DIR / "annotated.parquet"

    diagnostics = collect_runtime_diagnostics()
    logger.info(
        "Annotation backend actif: %s | mode=%s",
        diagnostics["annotation"]["backend_label"],
        diagnostics["mode"],
    )

    logger.info("Chargement de %s", input_path)
    dataframe = pd.read_parquet(input_path)

    if dataframe.empty:
        logger.warning("DataFrame vide, aucune classification a effectuer.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        empty = _empty_annotated_frame()
        empty.to_parquet(output_path, index=False)
        return empty

    logger.info("Lancement du pipeline ABSA sur %d textes...", len(dataframe))
    progress = None
    if tqdm is not None:
        progress = tqdm(total=len(dataframe), desc="Classification ABSA", unit="texte")

    absa_result = run_absa_pipeline(
        dataframe,
        output_path=output_path,
        persist_output=False,
    )

    if progress is not None:
        progress.update(len(dataframe))
        progress.close()

    enriched_result = _enrich_with_entities(absa_result, dataframe, catalog_db_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched_result.to_parquet(output_path, index=False)

    _log_summary(enriched_result)
    return enriched_result


if __name__ == "__main__":
    classify_sentiment()
