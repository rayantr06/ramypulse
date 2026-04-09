"""Collector for public seed URLs used in watch-first demo flows."""

from __future__ import annotations

from typing import Iterable

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed

try:
    import trafilatura
except ImportError:  # pragma: no cover - exercised through BeautifulSoup fallback
    trafilatura = None

from core.watchlists.watchlist_manager import get_watchlist


def _dedupe_seed_urls(seed_urls: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_url in seed_urls or []:
        url = str(raw_url or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        normalized.append(url)
    return normalized


def _extract_text(html: str) -> str:
    if trafilatura is not None:
        extracted = trafilatura.extract(html, include_links=False, favor_precision=True) or ""
        if extracted.strip():
            return extracted.strip()

    soup = BeautifulSoup(html, "html.parser")
    main_node = soup.find("article") or soup.find("main") or soup.body or soup
    return main_node.get_text(" ", strip=True)


@retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
def _fetch_html(url: str) -> str:
    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "RamyPulse/1.0 (+watch-first-expo)"},
    )
    response.raise_for_status()
    return response.text


def _resolve_watch_seed_context(
    *,
    client_id: str,
    watchlist_id: str | None,
    brand_name: str | None,
    seed_urls: list[str] | None,
) -> tuple[str | None, list[str]]:
    resolved_brand_name = str(brand_name or "").strip() or None
    resolved_seed_urls = _dedupe_seed_urls(seed_urls)

    if resolved_brand_name and resolved_seed_urls:
        return resolved_brand_name, resolved_seed_urls

    if not watchlist_id:
        return resolved_brand_name, resolved_seed_urls

    watchlist = get_watchlist(watchlist_id)
    if not watchlist:
        raise ValueError(f"watchlist not found: {watchlist_id}")
    if watchlist.get("client_id") != client_id:
        raise ValueError(f"watchlist tenant mismatch for {watchlist_id}")

    filters = watchlist.get("filters") or {}
    if resolved_brand_name is None:
        resolved_brand_name = str(filters.get("brand_name") or "").strip() or None
    if not resolved_seed_urls:
        resolved_seed_urls = _dedupe_seed_urls(filters.get("seed_urls"))

    return resolved_brand_name, resolved_seed_urls


def collect_public_url_seed(
    *,
    client_id: str,
    watchlist_id: str | None = None,
    brand_name: str | None = None,
    seed_urls: list[str] | None = None,
) -> list[dict[str, object]]:
    """Fetch public seed URLs and turn them into raw document payloads."""
    resolved_brand_name, resolved_seed_urls = _resolve_watch_seed_context(
        client_id=client_id,
        watchlist_id=watchlist_id,
        brand_name=brand_name,
        seed_urls=seed_urls,
    )

    documents: list[dict[str, object]] = []
    for seed_url in resolved_seed_urls:
        html = _fetch_html(seed_url)
        text = _extract_text(html)
        if not text.strip():
            continue
        documents.append(
            {
                "external_document_id": seed_url,
                "raw_text": text,
                "source_url": seed_url,
                "raw_payload": {
                    "brand_name": resolved_brand_name,
                    "seed_url": seed_url,
                    "watchlist_id": watchlist_id,
                },
                "raw_metadata": {
                    "channel": "public_url_seed",
                    "brand": resolved_brand_name,
                    "source_url": seed_url,
                },
            }
        )
    return documents
