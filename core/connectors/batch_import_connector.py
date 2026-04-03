"""Connecteur d'import batch fondé sur l'ImportEngine existant."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from core.connectors.base_connector import BaseConnector
from core.ingestion.import_engine import ImportEngine


class BatchImportConnector(BaseConnector):
    """Transforme un fichier client en documents bruts traçables."""

    def __init__(self) -> None:
        self._engine = ImportEngine()

    def fetch_documents(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
        file_path: str | Path | None = None,
        column_mapping: dict[str, str] | None = None,
        **kwargs,
    ) -> list[dict]:
        if not file_path:
            raise ValueError("file_path est requis pour un import batch")

        dataframe = self._engine.import_file(
            file_path=file_path,
            column_mapping=column_mapping,
            source_registry_id=str(source.get("source_id") or ""),
            deduplicate=True,
        )

        documents: list[dict] = []
        for index, row in enumerate(dataframe.to_dict(orient="records"), start=1):
            raw_text = str(row.get("text") or "")
            payload = dict(row)
            documents.append(
                {
                    "external_document_id": str(row.get("source_url") or f"batch-{index}"),
                    "raw_text": raw_text,
                    "raw_payload": payload,
                    "raw_metadata": {
                        "channel": row.get("channel"),
                        "source_url": row.get("source_url"),
                        "timestamp": row.get("timestamp"),
                        "language": row.get("language"),
                        "script_detected": row.get("script_detected"),
                    },
                    "collected_at": str(row.get("timestamp") or ""),
                    "checksum_sha256": sha256(raw_text.encode("utf-8")).hexdigest(),
                }
            )
        return documents

