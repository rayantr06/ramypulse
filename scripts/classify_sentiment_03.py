"""Classification de sentiment batch et extraction d'aspects pour RamyPulse.

Charge ``data/processed/clean.parquet``, applique le pipeline ABSA complet,
et sauvegarde ``data/processed/annotated.parquet``.
"""

from __future__ import annotations

import logging
import sys
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _log_summary(dataframe: pd.DataFrame) -> None:
    """Affiche un résumé de la classification dans les logs."""
    logger.info("=== RÉSUMÉ CLASSIFICATION ===")
    logger.info("Volume     : %d textes traités", len(dataframe))

    if "sentiment_label" in dataframe.columns and len(dataframe) > 0:
        distribution = dataframe["sentiment_label"].value_counts().to_dict()
        logger.info("Sentiments : %s", distribution)

    if "aspects" in dataframe.columns and len(dataframe) > 0:
        all_aspects = []
        for aspects_list in dataframe["aspects"]:
            if isinstance(aspects_list, list):
                all_aspects.extend(aspects_list)
        unique_aspects = sorted(set(all_aspects))
        logger.info("Aspects    : %s (%d mentions)", unique_aspects, len(all_aspects))

    logger.info("=============================")


def classify_sentiment(
    input_path: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Orchestre la classification de sentiment et l'extraction d'aspects.

    Args:
        input_path: Chemin vers le fichier clean.parquet.
        output_path: Chemin de sortie pour annotated.parquet.

    Returns:
        DataFrame annoté avec sentiment et aspects.
    """
    input_path = Path(input_path) if input_path is not None else config.PROCESSED_DATA_DIR / "clean.parquet"
    output_path = Path(output_path) if output_path is not None else config.PROCESSED_DATA_DIR / "annotated.parquet"

    logger.info("Chargement de %s", input_path)
    dataframe = pd.read_parquet(input_path)

    if dataframe.empty:
        logger.warning("DataFrame vide, aucune classification à effectuer.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        empty = pd.DataFrame(columns=[
            "text", "channel", "source_url", "timestamp",
            "sentiment_label", "confidence", "aspects", "aspect_sentiments",
        ])
        empty.to_parquet(output_path, index=False)
        return empty

    logger.info("Lancement du pipeline ABSA sur %d textes...", len(dataframe))
    if tqdm is not None:
        progress = tqdm(total=len(dataframe), desc="Classification ABSA", unit="texte")
    result = run_absa_pipeline(dataframe, output_path=output_path)
    if tqdm is not None:
        progress.update(len(dataframe))
        progress.close()

    _log_summary(result)
    return result


if __name__ == "__main__":
    classify_sentiment()
