"""Interface commune des connecteurs de sources."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """Interface minimale des connecteurs plateforme."""

    @abstractmethod
    def fetch_documents(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
        **kwargs,
    ) -> list[dict]:
        """Retourne une liste de documents bruts prêts à insérer."""

