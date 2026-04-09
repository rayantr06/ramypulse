"""Collector for keyword-based public web search results."""

from __future__ import annotations

from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import config

try:
    from tavily import TavilyClient
except ImportError:  # pragma: no cover - exercised when dependency is unavailable
    TavilyClient = None

from core.watchlists.watchlist_manager import get_watchlist

_TRACKING_QUERY_PARAMS = {"fbclid", "gclid", "igshid", "mc_cid", "mc_eid"}


def _normalize_keywords(keywords: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_keyword in keywords or []:
        keyword = str(raw_keyword or "").strip().lower()
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        normalized.append(keyword)
    return normalized


def _resolve_keywords(
    *,
    client_id: str,
    watchlist_id: str | None,
    keywords: list[str] | None,
) -> list[str]:
    resolved_keywords = _normalize_keywords(keywords)
    if resolved_keywords or not watchlist_id:
        return resolved_keywords

    watchlist = get_watchlist(watchlist_id)
    if not watchlist:
        raise ValueError(f"watchlist not found: {watchlist_id}")
    if watchlist.get("client_id") != client_id:
        raise ValueError(f"watchlist tenant mismatch for {watchlist_id}")

    filters = watchlist.get("filters") or {}
    semantic_keywords = list(filters.get("keywords") or [])
    for field_name in ("brand_name", "product_name"):
        candidate = str(filters.get(field_name) or "").strip()
        if candidate:
            semantic_keywords.append(candidate)
    return _normalize_keywords(semantic_keywords)


def _canonicalize_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url)
    filtered_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_QUERY_PARAMS
    ]
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(filtered_pairs, doseq=True),
            "",
        )
    )


def collect_web_keyword_results(
    *,
    client_id: str,
    watchlist_id: str | None = None,
    keywords: list[str] | None = None,
    max_results: int = 5,
) -> list[dict[str, object]]:
    """Run a keyword search and map hits into watch raw documents."""
    resolved_keywords = _resolve_keywords(
        client_id=client_id,
        watchlist_id=watchlist_id,
        keywords=keywords,
    )
    if not resolved_keywords or not config.TAVILY_API_KEY or TavilyClient is None:
        return []

    query = " OR ".join(resolved_keywords)
    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
    )

    documents: list[dict[str, object]] = []
    for item in response.get("results", []):
        text = str(item.get("content") or "").strip()
        source_url = _canonicalize_url(str(item.get("url") or "").strip())
        if not text or not source_url:
            continue
        documents.append(
            {
                "external_document_id": source_url,
                "raw_text": text,
                "source_url": source_url,
                "raw_payload": {
                    **item,
                    "keywords": resolved_keywords,
                    "watchlist_id": watchlist_id,
                },
                "raw_metadata": {
                    "channel": "web_search",
                    "keywords": resolved_keywords,
                    "source_url": source_url,
                },
            }
        )
    return documents
