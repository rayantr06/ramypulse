"""Nettoyage et normalisation des données brutes pour RamyPulse.

Charge tous les fichiers Parquet de ``data/raw/``, applique le normalizer
sur chaque texte, unifie le schéma, filtre et déduplique.
Sauvegarde le résultat dans ``data/processed/clean.parquet``.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from core.ingestion.normalizer import normalize

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_MIN_WORDS = 3
_MAX_WORDS = 500

_OUTPUT_COLUMNS = [
    "text",
    "text_original",
    "channel",
    "source_url",
    "timestamp",
    "script_detected",
    "language",
]


def _load_all_raw(raw_dir: Path) -> pd.DataFrame:
    """Charge et concatène tous les fichiers Parquet de raw_dir."""
    parquet_files = sorted(raw_dir.glob("*.parquet"))
    if not parquet_files:
        logger.warning("Aucun fichier Parquet trouvé dans %s.", raw_dir)
        return pd.DataFrame(columns=["text", "channel", "source_url", "timestamp"])

    frames = []
    for path in parquet_files:
        logger.info("Chargement de %s", path.name)
        frames.append(pd.read_parquet(path))

    combined = pd.concat(frames, ignore_index=True)
    logger.info("Total brut chargé: %d lignes depuis %d fichier(s).", len(combined), len(parquet_files))
    return combined


def _normalize_texts(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Applique normalizer.normalize() sur chaque texte."""
    originals = []
    normalized_texts = []
    scripts = []
    languages = []

    for text in dataframe["text"]:
        raw = str(text) if text is not None else ""
        originals.append(raw)
        result = normalize(raw)
        normalized_texts.append(result["normalized"])
        scripts.append(result["script_detected"])
        languages.append(result["language"])

    dataframe = dataframe.copy()
    dataframe["text_original"] = originals
    dataframe["text"] = normalized_texts
    dataframe["script_detected"] = scripts
    dataframe["language"] = languages
    return dataframe


def _filter_by_length(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Supprime les textes trop courts (<3 mots) ou trop longs (>500 mots)."""
    word_counts = dataframe["text"].str.split().str.len().fillna(0)
    mask = (word_counts >= _MIN_WORDS) & (word_counts <= _MAX_WORDS)
    removed = len(dataframe) - mask.sum()
    if removed > 0:
        logger.info("Filtrage longueur: %d textes supprimés (< %d ou > %d mots).", removed, _MIN_WORDS, _MAX_WORDS)
    return dataframe[mask].reset_index(drop=True)


def _filter_empty(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Supprime les lignes où le texte est vide ou None."""
    mask = dataframe["text"].notna() & (dataframe["text"].str.strip() != "")
    return dataframe[mask].reset_index(drop=True)


def _deduplicate(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Déduplique par texte normalisé."""
    before = len(dataframe)
    deduped = dataframe.drop_duplicates(subset=["text"], keep="first").reset_index(drop=True)
    removed = before - len(deduped)
    if removed > 0:
        logger.info("Déduplication: %d doublons supprimés.", removed)
    return deduped


def _ensure_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Garantit la présence de toutes les colonnes de sortie."""
    for col in _OUTPUT_COLUMNS:
        if col not in dataframe.columns:
            dataframe[col] = None
    return dataframe[_OUTPUT_COLUMNS]


def process_data(
    raw_dir: Path | None = None,
    output_path: Path | None = None,
) -> pd.DataFrame:
    """Orchestre le nettoyage et la normalisation des données brutes.

    Args:
        raw_dir: Répertoire contenant les fichiers Parquet bruts.
        output_path: Chemin de sortie pour le fichier clean.parquet.

    Returns:
        DataFrame nettoyé et normalisé.
    """
    raw_dir = Path(raw_dir) if raw_dir is not None else config.RAW_DATA_DIR
    output_path = Path(output_path) if output_path is not None else config.PROCESSED_DATA_DIR / "clean.parquet"

    raw = _load_all_raw(raw_dir)
    if raw.empty:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        empty = pd.DataFrame(columns=_OUTPUT_COLUMNS)
        empty.to_parquet(output_path, index=False)
        return empty

    normalized = _normalize_texts(raw)
    filtered = _filter_empty(normalized)
    filtered = _filter_by_length(filtered)
    deduped = _deduplicate(filtered)
    result = _ensure_columns(deduped)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False)

    logger.info("=== RÉSUMÉ NETTOYAGE ===")
    logger.info("Entrée     : %d lignes", len(raw))
    logger.info("Sortie     : %d lignes", len(result))
    logger.info("Canaux     : %s", list(result["channel"].unique()))
    logger.info("Sauvegardé : %s", output_path)
    logger.info("========================")

    return result


if __name__ == "__main__":
    process_data()
