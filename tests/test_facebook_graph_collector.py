"""Tests pour facebook_graph_collector."""
from __future__ import annotations

import sqlite3
from unittest import mock

import pytest

from core.social_metrics import facebook_graph_collector


def _make_db() -> sqlite3.Connection:
    """Base de données en mémoire avec la table post_engagement_metrics."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE post_engagement_metrics (
            metric_id        TEXT PRIMARY KEY,
            post_id          TEXT NOT NULL,
            collected_at     TEXT NOT NULL,
            likes            INTEGER DEFAULT 0,
            comments         INTEGER DEFAULT 0,
            shares           INTEGER DEFAULT 0,
            views            INTEGER DEFAULT 0,
            reach            INTEGER DEFAULT 0,
            impressions      INTEGER DEFAULT 0,
            saves            INTEGER DEFAULT 0,
            collection_mode  TEXT DEFAULT 'api',
            raw_response     TEXT DEFAULT '{}'
        )
    """)
    conn.commit()
    return conn


class TestCollectPostMetrics:
    def test_returns_metrics_from_api(self):
        api_response = {
            "id": "fb_post_001",
            "reactions": {"summary": {"total_count": 42}},
            "comments": {"summary": {"total_count": 5}},
            "shares": {"count": 3},
        }
        with mock.patch(
            "core.social_metrics.facebook_graph_collector.meta_graph_get"
        ) as mock_get:
            mock_get.return_value = api_response
            metrics = facebook_graph_collector.collect_post_metrics(
                "fb_post_001", access_token="tok123"
            )
        mock_get.assert_called_once_with(
            "fb_post_001",
            access_token="tok123",
            fields="id,reactions.summary(true),comments.summary(true),shares",
        )
        assert metrics["likes"] == 42
        assert metrics["comments"] == 5
        assert metrics["shares"] == 3

    def test_returns_empty_dict_on_api_error(self):
        with mock.patch(
            "core.social_metrics.facebook_graph_collector.meta_graph_get"
        ) as mock_get:
            mock_get.side_effect = Exception("Network error")
            metrics = facebook_graph_collector.collect_post_metrics(
                "fb_post_001", access_token="tok123"
            )
        assert metrics == {}

    def test_missing_fields_return_empty_dict(self):
        """Une réponse API sans reactions/comments/shares ne lève pas d'erreur."""
        api_response = {"id": "fb_post_002"}
        with mock.patch(
            "core.social_metrics.facebook_graph_collector.meta_graph_get"
        ) as mock_get:
            mock_get.return_value = api_response
            metrics = facebook_graph_collector.collect_post_metrics(
                "fb_post_002", access_token="tok123"
            )
        assert metrics == {}


class TestSaveMetrics:
    def test_writes_to_post_engagement_metrics(self):
        conn = _make_db()
        metrics = {"likes": 10, "comments": 3, "shares": 1}
        with mock.patch(
            "core.social_metrics.facebook_graph_collector._get_conn",
            return_value=conn,
        ):
            metric_id = facebook_graph_collector.save_metrics("post_001", metrics)

        row = conn.execute(
            "SELECT * FROM post_engagement_metrics WHERE metric_id = ?", [metric_id]
        ).fetchone()
        assert row is not None
        assert row["likes"] == 10
        assert row["comments"] == 3
        assert row["shares"] == 1
        assert row["post_id"] == "post_001"
        assert row["collection_mode"] == "api"

    def test_returns_metric_id_with_correct_prefix(self):
        conn = _make_db()
        with mock.patch(
            "core.social_metrics.facebook_graph_collector._get_conn",
            return_value=conn,
        ):
            metric_id = facebook_graph_collector.save_metrics("post_001", {"likes": 5})
        assert metric_id.startswith("met-")


class TestCollectAndSave:
    def test_raises_value_error_on_empty_metrics(self):
        """collect_and_save lève ValueError si aucune métrique collectée."""
        with mock.patch(
            "core.social_metrics.facebook_graph_collector.meta_graph_get"
        ) as mock_get:
            mock_get.return_value = {"id": "fb_post_003"}
            with pytest.raises(ValueError, match="Aucune métrique"):
                facebook_graph_collector.collect_and_save(
                    "fb_post_003", access_token="tok123"
                )

    def test_returns_metric_id_and_metrics_on_success(self):
        """collect_and_save retourne metric_id + métriques après persistance."""
        api_response = {
            "id": "fb_post_004",
            "reactions": {"summary": {"total_count": 7}},
            "comments": {"summary": {"total_count": 2}},
            "shares": {"count": 1},
        }
        conn = _make_db()
        with mock.patch(
            "core.social_metrics.facebook_graph_collector.meta_graph_get"
        ) as mock_get, mock.patch(
            "core.social_metrics.facebook_graph_collector._get_conn",
            return_value=conn,
        ):
            mock_get.return_value = api_response
            result = facebook_graph_collector.collect_and_save(
                "fb_post_004", access_token="tok123"
            )
        assert result["metric_id"].startswith("met-")
        assert result["likes"] == 7
        assert result["comments"] == 2
        assert result["shares"] == 1
