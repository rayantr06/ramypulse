"""Connecteur Google Maps / Business Profile Wave 5.1."""

from __future__ import annotations

from core.connectors.base_connector import BaseConnector


class GoogleMapsConnector(BaseConnector):
    """Connecteur stub pour Google Maps."""

    def fetch_documents(self, source: dict, *, credentials: dict | None = None, **kwargs) -> list[dict]:
        return []

