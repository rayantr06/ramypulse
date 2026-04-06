# tests/test_facebook_connector.py
"""Tests pour FacebookConnector avec fetch_mode='api'."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.connectors.facebook_connector import FacebookConnector


def _source(fetch_mode: str = "api", page_id: str = "111222333") -> dict:
    return {
        "source_id": "src-fb-001",
        "platform": "facebook",
        "config_json": {"fetch_mode": fetch_mode, "page_id": page_id},
    }


def _creds(access_token: str = "tok123") -> dict:
    return {"access_token": access_token}


_SAMPLE_POST = {
    "id": "post_001",
    "message": "Nouveau jus citron disponible",
    "created_time": "2026-04-01T10:00:00+0000",
    "permalink_url": "https://facebook.com/ramy/posts/post_001",
    "reactions": {"summary": {"total_count": 42}},
    "comments": {
        "data": [
            {
                "id": "comment_001",
                "message": "Vraiment délicieux",
                "created_time": "2026-04-01T11:00:00+0000",
                "like_count": 3,
            },
            {
                "id": "comment_002",
                "message": "Trop sucré pour moi",
                "created_time": "2026-04-01T12:00:00+0000",
                "like_count": 0,
            },
        ],
        "summary": {"total_count": 2},
    },
}


class TestFacebookConnectorApiMode:
    def test_returns_post_and_comments_as_separate_documents(self):
        connector = FacebookConnector()
        with patch("core.connectors.facebook_connector.meta_graph_paginate") as mock_p:
            mock_p.return_value = [_SAMPLE_POST]
            docs = connector.fetch_documents(_source(), credentials=_creds())
        # 1 post + 2 comments = 3 documents
        assert len(docs) == 3

    def test_post_document_structure(self):
        connector = FacebookConnector()
        with patch("core.connectors.facebook_connector.meta_graph_paginate") as mock_p:
            mock_p.return_value = [_SAMPLE_POST]
            docs = connector.fetch_documents(_source(), credentials=_creds())
        post_docs = [d for d in docs if d["raw_metadata"].get("document_type") == "post"]
        assert len(post_docs) == 1
        doc = post_docs[0]
        assert doc["external_document_id"] == "post_001"
        assert doc["raw_text"] == "Nouveau jus citron disponible"
        assert doc["source_url"] == "https://facebook.com/ramy/posts/post_001"
        assert doc["raw_metadata"]["reactions_total"] == 42
        assert doc["raw_metadata"]["comments_total"] == 2
        assert "collected_at" in doc

    def test_comment_documents_structure(self):
        connector = FacebookConnector()
        with patch("core.connectors.facebook_connector.meta_graph_paginate") as mock_p:
            mock_p.return_value = [_SAMPLE_POST]
            docs = connector.fetch_documents(_source(), credentials=_creds())
        comment_docs = [d for d in docs if d["raw_metadata"].get("document_type") == "comment"]
        assert len(comment_docs) == 2
        c1 = next(d for d in comment_docs if d["external_document_id"] == "comment_001")
        assert c1["raw_text"] == "Vraiment délicieux"
        assert c1["raw_metadata"]["parent_post_id"] == "post_001"
        assert c1["raw_metadata"]["like_count"] == 3
        assert c1["source_url"] == "https://facebook.com/ramy/posts/post_001"

    def test_post_with_no_comments_returns_only_post_document(self):
        connector = FacebookConnector()
        post_no_comments = {
            "id": "post_002",
            "message": "Post sans commentaires",
            "created_time": "2026-04-01T10:00:00+0000",
            "permalink_url": "https://facebook.com/ramy/posts/post_002",
        }
        with patch("core.connectors.facebook_connector.meta_graph_paginate") as mock_p:
            mock_p.return_value = [post_no_comments]
            docs = connector.fetch_documents(_source(), credentials=_creds())
        assert len(docs) == 1
        assert docs[0]["raw_metadata"]["document_type"] == "post"

    def test_missing_access_token_raises_value_error(self):
        connector = FacebookConnector()
        with pytest.raises(ValueError, match="access_token"):
            connector.fetch_documents(_source(), credentials={})

    def test_missing_page_id_raises_value_error(self):
        connector = FacebookConnector()
        source_no_page = {
            "source_id": "src-fb-002",
            "platform": "facebook",
            "config_json": {"fetch_mode": "api"},
        }
        with pytest.raises(ValueError, match="page_id"):
            connector.fetch_documents(source_no_page, credentials=_creds())

    def test_snapshot_mode_delegates_to_parent(self):
        connector = FacebookConnector()
        with patch(
            "core.connectors.platform_snapshot_connector.SnapshotPlatformConnector.fetch_documents"
        ) as mock_parent:
            mock_parent.return_value = []
            result = connector.fetch_documents(_source(fetch_mode="snapshot"), credentials=_creds())
        mock_parent.assert_called_once()
        assert result == []

    def test_default_mode_is_snapshot(self):
        """Sans fetch_mode explicite, le connecteur délègue au parent (snapshot)."""
        connector = FacebookConnector()
        source_no_mode = {
            "source_id": "src-fb-003",
            "platform": "facebook",
            "config_json": {"page_id": "111222333"},
        }
        with patch(
            "core.connectors.platform_snapshot_connector.SnapshotPlatformConnector.fetch_documents"
        ) as mock_parent:
            mock_parent.return_value = []
            connector.fetch_documents(source_no_mode, credentials=_creds())
        mock_parent.assert_called_once()

    def test_api_error_propagates(self):
        """Une erreur HTTP (rate limit, token invalide) est remontée à l'orchestrateur."""
        connector = FacebookConnector()
        with patch("core.connectors.facebook_connector.meta_graph_paginate") as mock_p:
            mock_p.side_effect = Exception("HTTP 429 Too Many Requests")
            with pytest.raises(Exception, match="429"):
                connector.fetch_documents(_source(), credentials=_creds())
