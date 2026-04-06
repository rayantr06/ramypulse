"""Integration test: same Instagram post via API and import → single content_item."""

from __future__ import annotations

import json
import sqlite3

import config
from core.database import DatabaseManager
from core.ingestion.orchestrator import IngestionOrchestrator
from core.social_metrics.credential_manager import create_credential
from unittest.mock import patch

_db = DatabaseManager()
_db.create_tables()


class TestInstagramDedup:
    def test_api_then_import_same_post_single_content_item(self):
        """A post fetched via API and then via import should resolve to one content_item."""
        cred_id = create_credential(
            entity_type="brand",
            entity_name="dedup_test",
            platform="instagram",
            account_id="17841400123456789",
            access_token="dedup_token",
        )

        orchestrator = IngestionOrchestrator()

        # Source 1: API (priority 1)
        api_source = orchestrator.create_source({
            "source_name": "IG API Dedup",
            "platform": "instagram",
            "source_type": "api",
            "owner_type": "brand",
            "credential_id": cred_id,
            "config_json": json.dumps({"fetch_mode": "api", "profile_id": "17841400123456789"}),
            "source_priority": 1,
            "coverage_key": "instagram:dedup_test",
        })

        # Source 2: Import (priority 2)
        import_source = orchestrator.create_source({
            "source_name": "IG Import Dedup",
            "platform": "instagram",
            "source_type": "batch_import",
            "owner_type": "brand",
            "config_json": json.dumps({"fetch_mode": "snapshot"}),
            "source_priority": 2,
            "coverage_key": "instagram:dedup_test",
        })

        permalink = "https://www.instagram.com/p/ABC123/"

        # Sync via API — returns one post
        api_media = [{
            "id": "media_ABC123",
            "caption": "Test dedup post",
            "timestamp": "2026-03-15T10:30:00+0000",
            "media_type": "IMAGE",
            "permalink": permalink,
            "like_count": 10,
            "comments_count": 2,
        }]

        with patch("core.connectors.instagram_connector.meta_graph_paginate", return_value=api_media):
            api_result = orchestrator.run_source_sync(api_source["source_id"])

        assert api_result["records_inserted"] == 1

        # Sync via import — returns same post (same permalink)
        import_docs = [{
            "external_document_id": "media_ABC123",
            "raw_text": "Test dedup post",
            "raw_payload": {"id": "media_ABC123", "permalink": permalink},
            "raw_metadata": {"media_type": "IMAGE"},
            "source_url": permalink,
            "collected_at": "2026-03-16T00:00:00Z",
        }]

        with patch.object(orchestrator._connectors["import"], "fetch_documents", return_value=import_docs):
            import_result = orchestrator.run_source_sync(import_source["source_id"])

        assert import_result["records_inserted"] == 1

        # Both raw_documents should point to the same content_item
        conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT DISTINCT content_item_id
            FROM raw_documents
            WHERE source_id IN (?, ?)
            AND content_item_id IS NOT NULL
            """,
            [api_source["source_id"], import_source["source_id"]],
        ).fetchall()
        conn.close()

        content_item_ids = [row["content_item_id"] for row in rows]
        # Should be exactly 1 unique content_item_id (dedup worked)
        assert len(content_item_ids) == 1
