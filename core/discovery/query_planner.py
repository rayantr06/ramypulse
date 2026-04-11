"""Perplexity query generation for Discovery Brain V1."""

from __future__ import annotations

import logging

from core.discovery.brand_watchlist import BrandWatchlist

logger = logging.getLogger(__name__)


def _contains_arabic(text: str) -> bool:
    return any("\u0600" <= character <= "\u06ff" for character in text)


class QueryPlanner:
    """Generate prioritized search queries for a specific discovery mode."""

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
        self.watchlist = watchlist

    def generate_queries(self, mode: str, max_queries: int = 10) -> list[str]:
        queries: list[str] = []
        watchlist = self.watchlist

        for variant in watchlist.brand_variants[:3]:
            for product in watchlist.products[:2]:
                queries.append(f"{variant} {product}")

        for aspect in watchlist.aspects:
            queries.append(f"{watchlist.brand_name} {aspect} avis")
            if "ar" in watchlist.languages:
                arabic_variant = next(
                    (variant for variant in watchlist.brand_variants if _contains_arabic(variant)),
                    None,
                )
                if arabic_variant:
                    queries.append(f"{arabic_variant} {aspect}")

        if mode == "discovery":
            for competitor in watchlist.competitors[:3]:
                competitor_name = str(competitor.get("name") or "").strip()
                if not competitor_name:
                    continue
                queries.append(f"{competitor_name} vs {watchlist.brand_name}")
                queries.append(f"{competitor_name} avis consommateur")

        for signal in self.SIGNAL_KEYWORDS_FR[:3]:
            queries.append(f"{watchlist.brand_name} {signal}")

        limited_queries = queries[:max_queries]
        logger.info(
            "QueryPlanner: mode=%s generated %d queries for %s",
            mode,
            len(limited_queries),
            watchlist.brand_name,
        )
        return limited_queries

    def get_domains(self, mode: str) -> list[str] | None:
        if mode == "press":
            return self.watchlist.priority_domains
        if mode == "reddit":
            return ["reddit.com"]
        return None

    def get_recency(self, mode: str) -> str:
        return self.watchlist.recency.get(mode, "week")
