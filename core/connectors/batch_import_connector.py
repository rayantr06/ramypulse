"""Connecteur d'import batch fondé sur l'ImportEngine existant."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pandas as pd

from core.connectors.base_connector import BaseConnector
from core.ingestion.import_engine import ImportEngine


class BatchImportConnector(BaseConnector):
    """Transforme un fichier client en documents bruts traçables."""

    def __init__(self) -> None:
        self._engine = ImportEngine()

    @staticmethod
    def dataframe_to_documents(
        dataframe: pd.DataFrame,
        *,
        source: dict,
        default_channel: str | None = None,
    ) -> list[dict]:
        """Convertit un DataFrame déjà nettoyé en documents bruts traçables."""
        working = dataframe.copy()
        if default_channel and "channel" not in working.columns:
            working["channel"] = default_channel
        if "source_url" not in working.columns:
            working["source_url"] = None
        if "timestamp" not in working.columns:
            working["timestamp"] = None

        source_trace = {
            "source_id": source.get("source_id"),
            "source_name": source.get("source_name") or source.get("display_name"),
            "platform": source.get("platform"),
            "source_type": source.get("source_type"),
            "owner_type": source.get("owner_type"),
            "client_id": source.get("client_id"),
        }

        documents: list[dict] = []
        for index, row in enumerate(working.to_dict(orient="records"), start=1):
            raw_text = str(row.get("text") or "")
            payload = dict(row)
            metadata = {
                "channel": row.get("channel") or default_channel,
                "source_url": row.get("source_url"),
                "timestamp": row.get("timestamp"),
                "language": row.get("language"),
                "script_detected": row.get("script_detected"),
                **source_trace,
            }
            documents.append(
                {
                    "external_document_id": str(
                        row.get("source_url")
                        or row.get("external_document_id")
                        or f"{source_trace.get('source_id') or 'batch'}-{index}"
                    ),
                    "raw_text": raw_text,
                    "raw_payload": payload,
                    "raw_metadata": metadata,
                    "collected_at": str(row.get("timestamp") or row.get("collected_at") or ""),
                    "checksum_sha256": sha256(raw_text.encode("utf-8")).hexdigest(),
                }
            )
        return documents

    def fetch_documents(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
        file_path: str | Path | None = None,
        column_mapping: dict[str, str] | None = None,
        **kwargs,
    ) -> list[dict]:
        runtime_inputs = self.resolve_runtime_inputs(
            source,
            credentials=credentials,
            file_path=file_path,
            column_mapping=column_mapping,
            **kwargs,
        )
        source_config = runtime_inputs.get("config") if isinstance(runtime_inputs.get("config"), dict) else {}
        resolved_file_path = (
            runtime_inputs.get("file_path")
            or source_config.get("snapshot_path")
            or source_config.get("file_path")
            or source_config.get("import_path")
        )
        resolved_column_mapping = runtime_inputs.get("column_mapping")
        if not isinstance(resolved_column_mapping, dict):
            resolved_column_mapping = source_config.get("column_mapping")

        if not resolved_file_path:
            raise ValueError("file_path est requis pour un import batch")

        dataframe = self._engine.import_file(
            file_path=resolved_file_path,
            column_mapping=resolved_column_mapping if isinstance(resolved_column_mapping, dict) else None,
            source_registry_id=str(source.get("source_id") or ""),
            deduplicate=True,
        )
        default_channel = str(source.get("platform") or "") or None
        return self.dataframe_to_documents(dataframe, source=source, default_channel=default_channel)
