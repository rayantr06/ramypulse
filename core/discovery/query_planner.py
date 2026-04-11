"""Generation de requetes Perplexity pour Discovery Brain V1."""

from __future__ import annotations

import logging

from core.discovery.brand_watchlist import BrandWatchlist

logger = logging.getLogger(__name__)


def _contains_arabic(text: str) -> bool:
    return any("\u0600" <= character <= "\u06ff" for character in text)


class QueryPlanner:
    """Genere des requetes priorisees selon le mode de decouverte."""

    SIGNAL_KEYWORDS_FR = [
        "probleme",
        "augmentation",
        "rupture",
        "qualite",
        "scandale",
        "nouveau",
        "lancement",
        "rappel",
        "plainte",
        "boycott",
    ]
    SIGNAL_KEYWORDS_AR = [
        "مشكلة",
        "زيادة",
        "جودة",
        "شكوى",
        "جديد",
        "مقاطعة",
    ]

    def __init__(self, watchlist: BrandWatchlist):
        """Construit un planner a partir d'une watchlist declarative."""
        self.watchlist = watchlist

    def _arabic_variant(self) -> str | None:
        return next(
            (variant for variant in self.watchlist.brand_variants if _contains_arabic(variant)),
            None,
        )

    def _generate_press_queries(self) -> list[str]:
        queries: list[str] = []
        watchlist = self.watchlist

        for variant in watchlist.brand_variants[:3]:
            for product in watchlist.products[:2]:
                queries.append(f"{variant} {product}")

        for aspect in watchlist.aspects:
            queries.append(f"{watchlist.brand_name} {aspect} avis")
            if "ar" in watchlist.languages:
                arabic_variant = self._arabic_variant()
                if arabic_variant:
                    queries.append(f"{arabic_variant} {aspect}")

        for signal in self.SIGNAL_KEYWORDS_FR[:3]:
            queries.append(f"{watchlist.brand_name} {signal}")

        return queries

    def _generate_reddit_queries(self) -> list[str]:
        queries: list[str] = []
        watchlist = self.watchlist

        for variant in watchlist.brand_variants[:2]:
            queries.append(f"{variant} reddit")
            queries.append(f"{variant} forum")

        for aspect in watchlist.aspects[:3]:
            queries.append(f"{watchlist.brand_name} {aspect} reddit")
            queries.append(f"{watchlist.brand_name} {aspect} forum")

        for signal in self.SIGNAL_KEYWORDS_FR[:2]:
            queries.append(f"{watchlist.brand_name} {signal} reddit")
            queries.append(f"{watchlist.brand_name} {signal} forum")

        if "ar" in watchlist.languages:
            arabic_variant = self._arabic_variant()
            if arabic_variant:
                for signal in self.SIGNAL_KEYWORDS_AR[:2]:
                    queries.append(f"{arabic_variant} {signal} reddit")

        return queries

    def generate_queries(self, mode: str, max_queries: int = 10) -> list[str]:
        """Genere les requetes adaptees au mode `press`, `reddit` ou `discovery`."""
        watchlist = self.watchlist

        if mode == "reddit":
            queries = self._generate_reddit_queries()
        else:
            queries = self._generate_press_queries()

        if mode == "discovery":
            for competitor in watchlist.competitors[:3]:
                competitor_name = str(competitor.get("name") or "").strip()
                if not competitor_name:
                    continue
                queries.append(f"{competitor_name} vs {watchlist.brand_name}")
                queries.append(f"{competitor_name} avis consommateur")

        limited_queries = queries[:max_queries]
        logger.info(
            "QueryPlanner: mode=%s generated %d queries for %s",
            mode,
            len(limited_queries),
            watchlist.brand_name,
        )
        return limited_queries

    def get_domains(self, mode: str) -> list[str] | None:
        """Retourne les filtres de domaines a appliquer pour le mode."""
        if mode == "press":
            return self.watchlist.priority_domains
        if mode == "reddit":
            return ["reddit.com"]
        return None

    def get_recency(self, mode: str) -> str:
        """Retourne le filtre de recence pour le mode demande."""
        return self.watchlist.recency.get(mode, "week")
