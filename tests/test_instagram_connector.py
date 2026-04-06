"""Tests for InstagramConnector fetch_mode='api'."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from core.connectors.instagram_connector import InstagramConnector


def _make_source(fetch_mode: str = "api", credential_id: str | None = None) -> dict:
    """Create a minimal source dict for testing."""
    return {
        "source_id": "src-test-ig",
        "client_id": "test_client",
        "platform": "instagram",
        "source_type": "api",
        "owner_type": "brand",
        "credential_id": credential_id,
        "config_json": json.dumps({
            "fetch_mode": fetch_mode,
            "profile_id": "17841400123456789",
        }),
    }


def _make_media_item(media_id: str, caption: str = "Test caption") -> dict:
    return {
        "id": media_id,
        "caption": caption,
        "timestamp": "2026-03-15T10:30:00+0000",
        "media_type": "IMAGE",
        "media_url": f"https://scontent.cdninstagram.com/{media_id}.jpg",
        "permalink": f"https://www.instagram.com/p/{media_id}/",
        "like_count": 42,
        "comments_count": 5,
    }


class TestInstagramConnectorApiMode:
    def test_fetch_mode_api_calls_graph_api(self):
        connector = InstagramConnector()
        source = _make_source("api")
        credentials = {"access_token": "fake_token", "account_id": "17841400123456789"}
        media_items = [_make_media_item("111"), _make_media_item("222")]

        with patch("core.connectors.instagram_connector.meta_graph_paginate") as mock_paginate:
            mock_paginate.return_value = media_items
            documents = connector.fetch_documents(source, credentials=credentials)

        assert len(documents) == 2
        assert documents[0]["external_document_id"] == "111"
        assert documents[0]["raw_text"] == "Test caption"
        assert documents[0]["source_url"] == "https://www.instagram.com/p/111/"
        assert "raw_payload" in documents[0]
        assert "raw_metadata" in documents[0]
        assert documents[0]["raw_metadata"]["media_type"] == "IMAGE"

    def test_fetch_mode_api_no_credentials_raises(self):
        connector = InstagramConnector()
        source = _make_source("api")

        with pytest.raises(ValueError, match="access_token"):
            connector.fetch_documents(source, credentials={})

    def test_fetch_mode_api_no_account_id_raises(self):
        connector = InstagramConnector()
        source = _make_source("api")

        with pytest.raises(ValueError, match="account_id"):
            connector.fetch_documents(source, credentials={"access_token": "tok"})

    def test_fetch_mode_api_empty_results(self):
        connector = InstagramConnector()
        source = _make_source("api")
        credentials = {"access_token": "fake_token", "account_id": "17841400123456789"}

        with patch("core.connectors.instagram_connector.meta_graph_paginate") as mock_paginate:
            mock_paginate.return_value = []
            documents = connector.fetch_documents(source, credentials=credentials)

        assert documents == []


class TestInstagramConnectorSnapshotMode:
    """Verify that snapshot and collector modes still delegate to the parent."""

    def test_fetch_mode_snapshot_delegates_to_parent(self):
        connector = InstagramConnector()
        source = _make_source("snapshot")

        with patch.object(
            connector.__class__.__bases__[0],  # SnapshotPlatformConnector
            "fetch_documents",
            return_value=[{"external_document_id": "snap-1"}],
        ) as mock_parent:
            documents = connector.fetch_documents(source, credentials=None)

        mock_parent.assert_called_once()
        assert documents == [{"external_document_id": "snap-1"}]

    def test_fetch_mode_default_is_snapshot(self):
        connector = InstagramConnector()
        source = {
            "source_id": "src-test",
            "platform": "instagram",
            "config_json": "{}",
        }

        with patch.object(
            connector.__class__.__bases__[0],
            "fetch_documents",
            return_value=[],
        ) as mock_parent:
            connector.fetch_documents(source, credentials=None)

        mock_parent.assert_called_once()
