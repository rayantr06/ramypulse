"""Connecteur plateforme basé sur snapshots locaux et collecteurs optionnels."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path

import pandas as pd

import config
from core.connectors.base_connector import BaseConnector
from core.connectors.batch_import_connector import BatchImportConnector
from core.connectors.source_config import parse_source_config
from core.ingestion.import_engine import ImportEngine

logger = logging.getLogger(__name__)


def _call_scraper_entrypoint(function, *, source: dict, credentials: dict | None):
    """Tente plusieurs signatures d'appel pour les collecteurs optionnels."""
    attempts = [
        lambda: function(source=source, credentials=credentials),
        lambda: function(source=source),
        lambda: function(credentials=credentials),
        lambda: function(),
    ]
    for attempt in attempts:
        try:
            result = attempt()
        except TypeError:
            continue
        if isinstance(result, pd.DataFrame):
            return result
    return None


class SnapshotPlatformConnector(BaseConnector):
    """Réutilise un snapshot local ou un collecteur optionnel pour une plateforme."""

    def __init__(
        self,
        *,
        platform: str,
        default_snapshot_names: tuple[str, ...],
        scraper_modules: tuple[str, ...] = (),
    ) -> None:
        self.platform = platform
        self.default_snapshot_names = default_snapshot_names
        self.scraper_modules = scraper_modules
        self._engine = ImportEngine()

    def _candidate_paths(self, source: dict, *, file_path: str | Path | None = None) -> list[Path]:
        source_config = parse_source_config(source)
        candidates: list[Path] = []
        for raw_path in (
            file_path,
            source_config.get("snapshot_path"),
            source_config.get("import_path"),
            source_config.get("file_path"),
        ):
            if raw_path:
                candidates.append(Path(str(raw_path)))
        for file_name in self.default_snapshot_names:
            candidates.append(config.RAW_DATA_DIR / file_name)
        return candidates

    def _load_dataframe_from_path(
        self,
        path: Path,
        *,
        column_mapping: dict[str, str] | None = None,
    ) -> pd.DataFrame:
        dataframe = self._engine.import_file(
            file_path=path,
            column_mapping=column_mapping,
            source_registry_id=None,
            deduplicate=True,
        )
        if "channel" in dataframe.columns:
            filtered = dataframe[dataframe["channel"].fillna("").astype(str) == self.platform]
            if not filtered.empty:
                return filtered.reset_index(drop=True)
        return dataframe.reset_index(drop=True)

    def _load_from_snapshots(
        self,
        source: dict,
        *,
        file_path: str | Path | None = None,
        column_mapping: dict[str, str] | None = None,
    ) -> list[dict]:
        for candidate in self._candidate_paths(source, file_path=file_path):
            if not candidate.exists():
                continue
            dataframe = self._load_dataframe_from_path(candidate, column_mapping=column_mapping)
            if dataframe.empty:
                continue
            return BatchImportConnector.dataframe_to_documents(
                dataframe,
                source=source,
                default_channel=self.platform,
            )
        return []

    def _load_from_scraper(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
    ) -> list[dict]:
        for module_name in self.scraper_modules:
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError:
                continue
            except Exception as exc:  # pragma: no cover
                logger.warning("Import impossible pour %s: %s", module_name, exc)
                continue

            for function_name in ("collect", "collect_data", "main"):
                function = getattr(module, function_name, None)
                if not callable(function):
                    continue
                dataframe = _call_scraper_entrypoint(
                    function,
                    source=source,
                    credentials=credentials,
                )
                if isinstance(dataframe, pd.DataFrame) and not dataframe.empty:
                    return BatchImportConnector.dataframe_to_documents(
                        dataframe,
                        source=source,
                        default_channel=self.platform,
                    )
        return []

    def fetch_documents(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
        file_path: str | Path | None = None,
        column_mapping: dict[str, str] | None = None,
        **kwargs,
    ) -> list[dict]:
        source_config = self.validate_source_config(source, require_platform_fields=False)
        fetch_mode = str(source_config.get("fetch_mode") or "snapshot").strip().lower() or "snapshot"
        resolved_mapping = column_mapping or source_config.get("column_mapping")
        mapping = resolved_mapping if isinstance(resolved_mapping, dict) else None

        if fetch_mode == "snapshot":
            documents = self._load_from_snapshots(
                source,
                file_path=file_path,
                column_mapping=mapping,
            )
            if documents:
                return documents
            return self._load_from_scraper(source, credentials=credentials)

        documents = self._load_from_scraper(source, credentials=credentials)
        if documents:
            return documents
        return self._load_from_snapshots(
            source,
            file_path=file_path,
            column_mapping=mapping,
        )
