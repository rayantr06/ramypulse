"""Tests for Meta Graph API HTTP client."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch, MagicMock

import pytest


def _mock_urlopen_response(data: dict) -> MagicMock:
    """Create a mock urllib response that returns JSON data."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(data).encode("utf-8")
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


class TestMetaGraphGet:
    def test_single_page_returns_data(self):
        from core.connectors.meta_graph_client import meta_graph_get

        api_response = {
            "data": [
                {"id": "111", "caption": "Hello"},
                {"id": "222", "caption": "World"},
            ]
        }

        with patch("core.connectors.meta_graph_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = _mock_urlopen_response(api_response)
            result = meta_graph_get("12345/media", access_token="fake_token", fields="id,caption")

        assert result == api_response
        call_url = mock_urlopen.call_args[0][0].full_url
        assert "12345/media" in call_url
        assert "access_token=fake_token" in call_url
        assert "fields=id%2Ccaption" in call_url or "fields=id,caption" in call_url


class TestMetaGraphPaginate:
    def test_follows_cursor_pagination(self):
        from core.connectors.meta_graph_client import meta_graph_paginate

        page1 = {
            "data": [{"id": "111"}],
            "paging": {"cursors": {"after": "cursor_abc"}, "next": "https://graph.facebook.com/v21.0/next"},
        }
        page2 = {
            "data": [{"id": "222"}],
            "paging": {"cursors": {"after": "cursor_def"}},
        }

        with patch("core.connectors.meta_graph_client.meta_graph_get") as mock_get:
            mock_get.side_effect = [page1, page2]
            items = meta_graph_paginate("12345/media", access_token="fake", fields="id")

        assert len(items) == 2
        assert items[0]["id"] == "111"
        assert items[1]["id"] == "222"
        assert mock_get.call_count == 2
        second_call_params = mock_get.call_args_list[1][1].get("params", {})
        assert second_call_params.get("after") == "cursor_abc"

    def test_respects_max_pages(self):
        from core.connectors.meta_graph_client import meta_graph_paginate

        page = {
            "data": [{"id": "111"}],
            "paging": {"cursors": {"after": "cursor"}, "next": "https://graph.facebook.com/v21.0/next"},
        }

        with patch("core.connectors.meta_graph_client.meta_graph_get") as mock_get:
            mock_get.return_value = page
            items = meta_graph_paginate("12345/media", access_token="fake", fields="id", max_pages=2)

        assert len(items) == 2
        assert mock_get.call_count == 2

    def test_empty_response(self):
        from core.connectors.meta_graph_client import meta_graph_paginate

        with patch("core.connectors.meta_graph_client.meta_graph_get") as mock_get:
            mock_get.return_value = {"data": []}
            items = meta_graph_paginate("12345/media", access_token="fake", fields="id")

        assert items == []


class TestMetaGraphErrors:
    def test_http_error_propagates(self):
        from core.connectors.meta_graph_client import meta_graph_get

        with patch("core.connectors.meta_graph_client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="https://graph.facebook.com/v21.0/test",
                code=401,
                msg="Invalid OAuth access token",
                hdrs=None,
                fp=None,
            )
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                meta_graph_get("test", access_token="bad_token")
            assert exc_info.value.code == 401

    def test_paginate_stops_on_error(self):
        from core.connectors.meta_graph_client import meta_graph_paginate

        page1 = {
            "data": [{"id": "111"}],
            "paging": {"cursors": {"after": "cursor"}, "next": "https://..."},
        }

        with patch("core.connectors.meta_graph_client.meta_graph_get") as mock_get:
            mock_get.side_effect = [
                page1,
                urllib.error.HTTPError("url", 429, "Rate limited", None, None),
            ]
            with pytest.raises(urllib.error.HTTPError):
                meta_graph_paginate("12345/media", access_token="fake", fields="id")
