"""Connecteur YouTube Wave 5.1."""

from __future__ import annotations

from core.connectors.base_connector import BaseConnector


class YouTubeConnector(BaseConnector):
    """Connecteur stub pour YouTube."""

    def fetch_documents(self, source: dict, *, credentials: dict | None = None, **kwargs) -> list[dict]:
        return []
