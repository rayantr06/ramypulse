"""Interface commune des connecteurs de sources."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.connectors.source_config import (
    parse_source_config,
    validate_source_config,
)


class BaseConnector(ABC):
    """Interface minimale des connecteurs plateforme."""

    def validate_source_config(self, source: dict) -> dict:
        """Valide et normalise la configuration de la source."""
        return validate_source_config(source)

    def resolve_runtime_inputs(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
        **kwargs,
    ) -> dict:
        """Construit les entrees runtime partagees pour un connecteur."""
        return {
            "config": parse_source_config(source),
            "credentials": credentials or {},
            **kwargs,
        }

    def health_hints(
        self,
        source: dict,
        *,
        last_run: dict | None = None,
    ) -> dict:
        """Retourne des indices de sante generiques pour l'administration."""
        return {
            "platform": source.get("platform"),
            "last_run_status": (last_run or {}).get("status"),
        }

    @abstractmethod
    def fetch_documents(
        self,
        source: dict,
        *,
        credentials: dict | None = None,
        **kwargs,
    ) -> list[dict]:
        """Retourne une liste de documents bruts prets a inserer."""
