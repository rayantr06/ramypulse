"""Connecteur Facebook Pages Wave 5.3 — snapshot + API Graph."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.connectors.meta_graph_client import meta_graph_paginate
from core.connectors.platform_snapshot_connector import SnapshotPlatformConnector
from core.connectors.source_config import parse_source_config

logger = logging.getLogger(__name__)

_POSTS_FIELDS = (
    "id,message,story,created_time,permalink_url,"
    "reactions.summary(true),"
    "comments.limit(100){id,message,created_time,like_count}"
)


class FacebookConnector(SnapshotPlatformConnector):
    """Connecteur Facebook Pages via snapshot local, scraper, ou API Graph officielle."""

    def __init__(self) -> None:
        super().__init__(
            platform="facebook",
            default_snapshot_names=("facebook_raw.parquet",),
            scraper_modules=("core.ingestion.scraper_facebook",),
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
        """Récupère les documents Facebook selon le mode de collecte configuré."""
        source_config = parse_source_config(source)
        fetch_mode = str(source_config.get("fetch_mode") or "snapshot").strip().lower()

        if fetch_mode == "api":
            return self._fetch_from_graph_api(source, credentials or {})

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
        """Collecte les posts et commentaires d'une Page Facebook via Meta Graph API."""
        access_token = credentials.get("access_token")
        if not access_token:
            raise ValueError(
                "Facebook API mode requires 'access_token' in credentials. "
                "Ensure the source has a valid credential_id linked to platform_credentials."
            )

        source_config = parse_source_config(source)
        page_id = str(source_config.get("page_id") or "").strip()
        if not page_id:
            raise ValueError(
                "Facebook API mode requires 'page_id' in config_json. "
                "Set page_id in the source configuration."
            )

        max_pages = int(source_config.get("max_pages", 10))

        posts = meta_graph_paginate(
            f"{page_id}/posts",
            access_token=access_token,
            fields=_POSTS_FIELDS,
            max_pages=max_pages,
        )

        now = datetime.now(timezone.utc).isoformat()
        documents: list[dict] = []

        for post in posts:
            permalink = post.get("permalink_url")
            documents.append({
                "external_document_id": post["id"],
                "raw_text": post.get("message") or post.get("story") or "",
                "raw_payload": post,
                "raw_metadata": {
                    "document_type": "post",
                    "permalink": permalink,
                    "timestamp": post.get("created_time"),
                    "reactions_total": (
                        post.get("reactions", {}).get("summary", {}).get("total_count", 0)
                    ),
                    "comments_total": (
                        post.get("comments", {}).get("summary", {}).get("total_count", 0)
                    ),
                },
                "source_url": permalink,
                "collected_at": now,
            })

            for comment in post.get("comments", {}).get("data", []):
                documents.append({
                    "external_document_id": comment["id"],
                    "raw_text": comment.get("message") or "",
                    "raw_payload": comment,
                    "raw_metadata": {
                        "document_type": "comment",
                        "parent_post_id": post["id"],
                        "timestamp": comment.get("created_time"),
                        "like_count": comment.get("like_count", 0),
                    },
                    "source_url": permalink,
                    "collected_at": now,
                })

        logger.info(
            "Facebook API: fetched %d documents (posts + comments) for page %s",
            len(documents),
            page_id,
        )
        return documents
