"""Contrat fournisseur pour les collecteurs publics V3."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Mapping


@dataclass(frozen=True)
class DiscoveryTarget:
    external_id: str
    canonical_url: str
    label: str


@dataclass(frozen=True)
class CollectedDocument:
    external_id: str
    canonical_url: str
    content: str
    published_at: str
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class CollectionCheckpoint:
    cursor: str | None
    collected_count: int
    estimated_cost_dzd: float


@dataclass(frozen=True)
class CollectionCost:
    provider: str
    documents: int
    requests: int
    cost_dzd: float
    currency_basis: str


class PublicSourceConnector(ABC):
    provider: str
    platform: str

    @abstractmethod
    async def discover(self, query: str, *, limit: int) -> list[DiscoveryTarget]:
        """Resout une cible metier en ressources collectables."""

    @abstractmethod
    async def collect(
        self, target: DiscoveryTarget, *, checkpoint: CollectionCheckpoint | None
    ) -> AsyncIterator[CollectedDocument]:
        """Collecte de maniere reprenable."""

    @abstractmethod
    def normalize(self, document: CollectedDocument) -> dict[str, object]:
        """Retourne le format mention canonique sans logique analytique."""

    @abstractmethod
    def checkpoint(self) -> CollectionCheckpoint:
        """Expose le dernier curseur durable."""

    @abstractmethod
    def report_cost(self) -> CollectionCost:
        """Expose le cout reel ou estime du run."""


class BudgetExceeded(RuntimeError):
    """Arret controle lorsqu'une limite de surveillance est atteinte."""


def enforce_collection_limits(
    *,
    collected: int,
    cost_dzd: float,
    max_documents: int,
    max_cost_dzd: float,
) -> None:
    if collected >= max_documents:
        raise BudgetExceeded("volume maximal de la surveillance atteint")
    if max_cost_dzd > 0 and cost_dzd >= max_cost_dzd:
        raise BudgetExceeded("budget maximal de la surveillance atteint")
