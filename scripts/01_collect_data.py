"""Script orchestrateur de collecte batch avec fallback local.

Le script suit le PRD:
1. Réutiliser les sources déjà collectées dans ``data/raw/`` si elles existent.
2. Tenter les collecteurs Facebook et Google Maps si les modules sont présents.
3. Tenter l'audio pipeline si des fichiers audio existent et si le module est présent.
4. Si aucune donnée n'est disponible, charger un dataset fallback local depuis ``data/demo/``.
5. Sauvegarder un fichier agrégé ``data/raw/collected_raw.parquet``.
"""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

RAW_DIR = config.RAW_DATA_DIR
DEMO_DIR = config.DEMO_DATA_DIR

STANDARD_COLUMNS = [
    "text",
    "sentiment_label",
    "channel",
    "aspect",
    "source_url",
    "timestamp",
    "confidence",
]


def _load_parquet_if_exists(path: Path) -> pd.DataFrame | None:
    """Charge un fichier Parquet s'il existe."""
    if not path.exists():
        return None
    logger.info("Source existante détectée: %s", path)
    return pd.read_parquet(path)


def _coerce_standard_schema(dataframe: pd.DataFrame, channel_hint: str | None = None) -> pd.DataFrame:
    """Aligne un DataFrame sur le schéma standard RamyPulse."""
    working = dataframe.copy()
    rename_map = {
        "url": "source_url",
        "date": "timestamp",
    }
    working = working.rename(columns={key: value for key, value in rename_map.items() if key in working.columns})

    if channel_hint and "channel" not in working.columns:
        working["channel"] = channel_hint

    for column in STANDARD_COLUMNS:
        if column not in working.columns:
            working[column] = None

    return working[STANDARD_COLUMNS]


def _call_first_available(module: object, function_names: list[str]) -> pd.DataFrame | None:
    """Appelle la première fonction disponible d'un module optionnel."""
    for function_name in function_names:
        function = getattr(module, function_name, None)
        if callable(function):
            result = function()
            if isinstance(result, pd.DataFrame):
                return result
    return None


def _try_optional_scraper(module_name: str, channel: str) -> pd.DataFrame | None:
    """Tente d'exécuter un scraper optionnel, sinon journalise un fallback gracieux."""
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        logger.info("Module optionnel absent: %s", module_name)
        return None
    except Exception as error:  # pragma: no cover - protection runtime
        logger.warning("Import du module %s impossible: %s", module_name, error)
        return None

    try:
        result = _call_first_available(module, ["collect", "collect_data", "main"])
    except Exception as error:  # pragma: no cover - protection runtime
        logger.warning("Collecte %s échouée: %s", channel, error)
        return None

    if result is None:
        logger.info("Aucune DataFrame retournée par %s.", module_name)
        return None

    logger.info("Collecte %s exécutée via %s.", channel, module_name)
    return _coerce_standard_schema(result, channel_hint=channel)


def _try_optional_audio_pipeline(raw_dir: Path) -> pd.DataFrame | None:
    """Tente une préparation audio si des fichiers audio et le pipeline existent."""
    audio_dir = raw_dir / "audio"
    if not audio_dir.exists():
        return None

    audio_files = [
        path for path in audio_dir.iterdir() if path.suffix.lower() in {".wav", ".mp3", ".m4a"}
    ]
    if not audio_files:
        return None

    try:
        module = importlib.import_module("core.ingestion.audio_pipeline")
    except ModuleNotFoundError:
        logger.info("audio_pipeline absent, aucun traitement audio lancé.")
        return None
    except Exception as error:  # pragma: no cover - protection runtime
        logger.warning("Import audio_pipeline impossible: %s", error)
        return None

    runner = getattr(module, "process_audio_batch", None) or getattr(module, "main", None)
    if not callable(runner):
        logger.info("audio_pipeline présent mais sans point d'entrée batch exploitable.")
        return None

    try:
        result = runner(audio_dir)
    except Exception as error:  # pragma: no cover - protection runtime
        logger.warning("Traitement audio échoué: %s", error)
        return None

    if not isinstance(result, pd.DataFrame):
        return None

    logger.info("Traitement audio exécuté pour %d fichier(s).", len(audio_files))
    return _coerce_standard_schema(result, channel_hint="audio")


def _load_local_fallback(demo_dir: Path) -> pd.DataFrame:
    """Charge le dataset fallback local depuis ``data/demo/``."""
    demo_files = sorted(demo_dir.glob("*.parquet"), key=lambda path: path.stat().st_size, reverse=True)
    if not demo_files:
        raise FileNotFoundError(
            "Aucun dataset fallback local trouvé dans data/demo/. "
            "Le PRD exige un fallback 45K disponible localement."
        )

    fallback_path = demo_files[0]
    logger.info("Fallback local chargé: %s", fallback_path)
    return _coerce_standard_schema(pd.read_parquet(fallback_path))


def _save_raw_snapshot(dataframe: pd.DataFrame, output_path: Path) -> None:
    """Sauvegarde le snapshot brut agrégé au format Parquet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_parquet(output_path, index=False)


def main(raw_dir: Path | None = None, demo_dir: Path | None = None) -> Path:
    """Orchestre la collecte batch et sauvegarde le résultat agrégé.

    Args:
        raw_dir: Répertoire ``data/raw`` à utiliser.
        demo_dir: Répertoire ``data/demo`` contenant le fallback local.

    Returns:
        Chemin du fichier Parquet agrégé généré.
    """
    raw_dir = Path(raw_dir) if raw_dir is not None else RAW_DIR
    demo_dir = Path(demo_dir) if demo_dir is not None else DEMO_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    demo_dir.mkdir(parents=True, exist_ok=True)

    sources: list[tuple[str, pd.DataFrame]] = []

    existing_sources = {
        "facebook": raw_dir / "facebook_raw.parquet",
        "google_maps": raw_dir / "google_raw.parquet",
    }
    for channel, path in existing_sources.items():
        dataframe = _load_parquet_if_exists(path)
        if dataframe is not None:
            sources.append((channel, _coerce_standard_schema(dataframe, channel_hint=channel)))

    if not any(channel == "facebook" for channel, _ in sources):
        dataframe = _try_optional_scraper("core.ingestion.scraper_facebook", "facebook")
        if dataframe is not None:
            sources.append(("facebook", dataframe))

    if not any(channel == "google_maps" for channel, _ in sources):
        dataframe = _try_optional_scraper("core.ingestion.scraper_google", "google_maps")
        if dataframe is not None:
            sources.append(("google_maps", dataframe))

    audio_dataframe = _try_optional_audio_pipeline(raw_dir)
    if audio_dataframe is not None:
        sources.append(("audio", audio_dataframe))

    if not sources:
        sources.append(("fallback_demo", _load_local_fallback(demo_dir)))

    collected = pd.concat([frame for _, frame in sources], ignore_index=True)
    output_path = raw_dir / "collected_raw.parquet"
    _save_raw_snapshot(collected, output_path)

    logger.info("=== RÉSUMÉ COLLECTE ===")
    logger.info("Sources    : %s", ", ".join(channel for channel, _ in sources))
    logger.info("Volume     : %d enregistrements", len(collected))
    logger.info("Colonnes   : %s", list(collected.columns))
    logger.info("Sauvegardé : %s", output_path)
    logger.info("=======================")

    return output_path


if __name__ == "__main__":
    main()
