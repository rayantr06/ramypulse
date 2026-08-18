"""SerpApi-powered discovery helpers for smart onboarding."""

from __future__ import annotations

import logging
from typing import Any

import config

try:
    from serpapi import GoogleSearch
except ImportError:  # pragma: no cover - optional dependency in local env
    GoogleSearch = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)

_BASE_PARAMS = {
    "engine": "google",
    "hl": "fr",
    "num": 10,
}


def _safe_dict_list(value: object) -> list[dict[str, Any]]:
    return [item for item in (value or []) if isinstance(item, dict)]


def _sanitize_organic(items: object) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for item in _safe_dict_list(items):
        title = str(item.get("title") or "").strip()
        link = str(item.get("link") or item.get("url") or "").strip()
        if not title or not link:
            continue
        results.append(
            {
                "title": title,
                "link": link,
                "snippet": str(item.get("snippet") or "").strip(),
                "source": str(item.get("source") or "").strip(),
            }
        )
    return results


def _sanitize_local(items: object) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for item in _safe_dict_list(items):
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        results.append(
            {
                "title": title,
                "address": str(item.get("address") or "").strip(),
                "place_id": str(item.get("place_id") or "").strip(),
                "website": str(item.get("website") or "").strip(),
            }
        )
    return results


def _run_search(query: str, country: str) -> dict[str, Any]:
    search = GoogleSearch(
        {
            **_BASE_PARAMS,
            "q": query,
            "gl": country.lower(),
            "api_key": config.SERPAPI_API_KEY,
        }
    )
    payload = search.get_dict()
    return payload if isinstance(payload, dict) else {}


def discover_brand_signals(
    *,
    brand_name: str,
    country: str = "dz",
    product_name: str | None = None,
) -> dict[str, Any]:
    """Query SerpApi for public brand signals.

    Returns a stable structure even when discovery is unavailable locally.
    """
    normalized_brand = brand_name.strip()
    if not normalized_brand:
        raise ValueError("brand_name is required")

    if not config.SERPAPI_API_KEY or GoogleSearch is None:
        return {
            "brand_name": normalized_brand,
            "country": country.lower(),
            "queries": [],
            "organic": [],
            "local": [],
            "skipped": True,
        }

    product_suffix = f" {product_name.strip()}" if isinstance(product_name, str) and product_name.strip() else ""
    queries = [
        f'"{normalized_brand}"{product_suffix} site officiel algerie',
        f'"{normalized_brand}" facebook instagram youtube google maps algerie',
    ]
    organic_results: list[dict[str, str]] = []
    local_results: list[dict[str, str]] = []

    for query in queries:
        try:
            response = _run_search(query, country)
        except Exception as exc:  # pragma: no cover - network/provider failures
            logger.warning("SerpApi onboarding discovery failed for %s: %s", query, exc)
            continue
        organic_results.extend(_sanitize_organic(response.get("organic_results")))
        local_results.extend(_sanitize_local(response.get("local_results")))

    return {
        "brand_name": normalized_brand,
        "country": country.lower(),
        "queries": queries,
        "organic": organic_results,
        "local": local_results,
        "skipped": False,
    }
