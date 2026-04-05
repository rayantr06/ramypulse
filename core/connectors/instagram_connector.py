"""Connecteur Instagram Wave 5.2 — snapshot + API Graph."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.connectors.meta_graph_client import meta_graph_paginate
from core.connectors.platform_snapshot_connector import SnapshotPlatformConnector
from core.connectors.source_config import parse_source_config

logger = logging.getLogger(__name__)

_MEDIA_FIELDS = (
    "id,caption,timestamp,media_type,media_url,"
    "permalink,like_count,comments_count"
)


class InstagramConnector(SnapshotPlatformConnector):
    """Connecteur Instagram via snapshot local, scraper, ou API Graph officielle."""

    def __init__(self) -> None:
        super().__init__(
            platform="instagram",
            default_snapshot_names=("instagram_raw.parquet",),
            scraper_modules=("core.ingestion.scraper_instagram",),
        )

    def fetch_documents(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
        file_path=None,
        column_mapping=None,
        **kwargs,
    ) -> list[dict]:
        source_config = parse_source_config(source)
        fetch_mode = str(source_config.get("fetch_mode") or "snapshot").strip().lower()

        if fetch_mode == "api":
            return self._fetch_from_graph_api(source, credentials or {})

        # Existing behavior: snapshot + scraper fallback
        return super().fetch_documents(
            source,
            credentials=credentials,
            file_path=file_path,
            column_mapping=column_mapping,
            **kwargs,
        )

    def _fetch_from_graph_api(
        self,
        source: dict,
        credentials: dict,
    ) -> list[dict]:
        """Discover and fetch media via Meta Graph API."""
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError(
                "Instagram API mode requires 'access_token' in credentials. "
                "Ensure the source has a valid credential_id linked to platform_credentials."
            )

        account_id = credentials.get("account_id")
        if not account_id:
            raise ValueError(
                "Instagram API mode requires 'account_id' (IG Business User ID) in credentials. "
                "Set account_id in the platform_credentials record."
            )

        source_config = parse_source_config(source)
        max_pages = int(source_config.get("max_pages", 20))

        media_items = meta_graph_paginate(
            f"{account_id}/media",
            access_token=access_token,
            fields=_MEDIA_FIELDS,
            max_pages=max_pages,
        )

        now = datetime.now(timezone.utc).isoformat()
        documents: list[dict] = []
        for media in media_items:
            documents.append({
                "external_document_id": media["id"],
                "raw_text": media.get("caption") or "",
                "raw_payload": media,
                "raw_metadata": {
                    "media_type": media.get("media_type"),
                    "permalink": media.get("permalink"),
                    "timestamp": media.get("timestamp"),
                    "like_count": media.get("like_count"),
                    "comments_count": media.get("comments_count"),
                },
                "source_url": media.get("permalink"),
                "collected_at": now,
            })

        logger.info(
            "Instagram API: fetched %d media for account %s",
            len(documents),
            account_id,
        )
        return documents
