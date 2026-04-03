"""Connecteur Facebook Pages Wave 5.1.

Implémentation fondation: le contrat est présent, l'appel API officiel sera
branché dans un slice ultérieur.
"""

from __future__ import annotations

from core.connectors.base_connector import BaseConnector


class FacebookConnector(BaseConnector):
    """Connecteur stub pour Facebook Pages."""

    def fetch_documents(self, source: dict, *, credentials: dict | None = None, **kwargs) -> list[dict]:
        return []

