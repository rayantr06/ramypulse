"""Point d'entree manuel pour le rapport hebdomadaire de recommandations."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

import config
from core.recommendation.weekly_report_job import run_weekly_recommendation_job

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Construit le parser CLI minimal du script."""
    parser = argparse.ArgumentParser(description="Genere le rapport hebdomadaire RamyPulse.")
    parser.add_argument(
        "--date",
        dest="run_date",
        help="Date ISO a utiliser pour simuler l'execution (YYYY-MM-DD).",
    )
    return parser


def _load_annotated_dataframe(path: Path) -> pd.DataFrame:
    """Charge annotated.parquet et normalise la colonne timestamp si presente."""
    dataframe = pd.read_parquet(path)
    if "timestamp" in dataframe.columns:
        dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], errors="coerce")
    return dataframe


def main(argv: list[str] | None = None) -> int:
    """Execute le job hebdomadaire en mode manuel."""
    args = _build_parser().parse_args(argv)
    annotated_path = Path(config.ANNOTATED_PARQUET_PATH)
    if not annotated_path.exists():
        logger.error("Fichier annotated.parquet introuvable: %s", annotated_path)
        return 1

    current_date = pd.Timestamp(args.run_date) if args.run_date else pd.Timestamp.now()
    dataframe = _load_annotated_dataframe(annotated_path)
    recommendation = run_weekly_recommendation_job(
        dataframe,
        current_date=current_date,
        client_id=config.DEFAULT_CLIENT_ID,
    )
    if recommendation is None:
        logger.info("Aucun rapport genere pour %s", current_date.date())
    else:
        logger.info("Rapport hebdomadaire genere: %s", recommendation.get("recommendation_id"))
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    raise SystemExit(main())
