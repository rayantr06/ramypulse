"""Perplexity-based Discovery Brain collectors for watch-first runs."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

import requests

import config
from core.discovery.brand_watchlist import BrandWatchlist
from core.discovery.budget_controller import BudgetController
from core.discovery.query_planner import QueryPlanner
from core.watchlists.watchlist_manager import get_watchlist

logger = logging.getLogger(__name__)

PERPLEXITY_SEARCH_URL = "https://api.perplexity.ai/search"
PERPLEXITY_RATE_QPS = 50.0
_MIN_INTERVAL = 1.0 / PERPLEXITY_RATE_QPS


def _build_watchlist_from_db(client_id: str, watchlist_id: str | None) -> BrandWatchlist:
    """Build a V1 brand watchlist from DB filters, with default fallback."""
    if not watchlist_id:
        return BrandWatchlist()

    watchlist = get_watchlist(watchlist_id)
    if not watchlist or watchlist.get("client_id") != client_id:
        logger.warning(
            "Watchlist %s missing or tenant mismatch; using Discovery Brain defaults",
            watchlist_id,
        )
        return BrandWatchlist()

    filters = watchlist.get("filters") or {}
    overrides: dict[str, Any] = {}

    brand_name = str(filters.get("brand_name") or "").strip()
    if brand_name:
        overrides["brand_name"] = brand_name

    keywords = list(filters.get("keywords") or [])
    if keywords:
        overrides["brand_variants"] = keywords

    return BrandWatchlist(**overrides) if overrides else BrandWatchlist()


def _search_perplexity(
    query: str,
    *,
    api_key: str,
    domains: list[str] | None = None,
    languages: list[str] | None = None,
    recency: str | None = None,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Execute a single Search API request using a singular `query` string."""
    body: dict[str, Any] = {
        "query": query,
        "max_results": max_results,
        "country": "DZ",
    }
    if domains:
        body["search_domain_filter"] = domains[:20]
    if languages:
        body["search_language_filter"] = languages[:20]
    if recency:
        body["search_recency_filter"] = recency

    response = requests.post(
        PERPLEXITY_SEARCH_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json() or {}
    return list(payload.get("results") or [])


def _result_to_document(
    result: dict[str, Any],
    *,
    mode: str,
    query: str,
    priority_domains: list[str],
) -> dict[str, object] | None:
    """Map one Perplexity search result into the watch raw-document contract."""
    url = str(result.get("url") or "").strip()
    snippet = str(result.get("snippet") or "").strip()
    title = str(result.get("title") or "").strip()
    if not url or not snippet:
        return None

    url_lower = url.lower()
    if any(domain in url_lower for domain in priority_domains):
        channel = "press"
    elif "reddit.com" in url_lower:
        channel = "reddit"
    else:
        channel = "web_search"

    document_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
    return {
        "external_document_id": document_id,
        "raw_text": snippet,
        "source_url": url,
        "raw_payload": {
            "title": title,
            "url": url,
            "date": result.get("date"),
            "last_updated": result.get("last_updated"),
            "query": query,
            "channel_mode": mode,
            "discovery_brain": True,
        },
        "raw_metadata": {
            "channel": channel,
            "source_url": url,
        },
    }


def _collect_mode(
    mode: str,
    *,
    client_id: str,
    watchlist_id: str | None = None,
    max_results_per_query: int = 10,
) -> list[dict[str, object]] | dict[str, object]:
    """Collect documents for a specific Discovery Brain mode."""
    api_key = config.PERPLEXITY_API_KEY
    if not api_key:
        return {"status": "skipped", "documents": [], "reason": "missing_api_key"}

    watchlist = _build_watchlist_from_db(client_id, watchlist_id)
    planner = QueryPlanner(watchlist)
    budget = BudgetController(
        monthly_budget_usd=watchlist.monthly_budget_usd,
        budget_split=watchlist.budget_split,
    )

    if not budget.can_spend(mode, n_search=1):
        return {"status": "skipped", "documents": [], "reason": "budget_exhausted"}

    max_queries = min(budget.max_queries_for_mode(mode), 10)
    if max_queries <= 0:
        return {"status": "skipped", "documents": [], "reason": "budget_exhausted"}

    queries = planner.generate_queries(mode, max_queries=max_queries)
    if not queries:
        return {"status": "skipped", "documents": [], "reason": "no_queries_generated"}

    domains = planner.get_domains(mode)
    recency = planner.get_recency(mode)
    documents: list[dict[str, object]] = []
    seen_urls: set[str] = set()
    last_call_time = 0.0
    executed_queries = 0

    for query in queries:
        if not budget.can_spend(mode, n_search=1):
            logger.info("Discovery Brain [%s]: budget exhausted mid-run", mode)
            break

        elapsed = time.monotonic() - last_call_time
        if last_call_time and elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)

        try:
            results = _search_perplexity(
                query,
                api_key=api_key,
                domains=domains,
                languages=watchlist.languages,
                recency=recency,
                max_results=max_results_per_query,
            )
            budget.record_spend(mode, n_search=1)
            executed_queries += 1
            last_call_time = time.monotonic()
        except requests.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            logger.error("Perplexity Search API error for %s: %s", query, status_code)
            if status_code == 429:
                break
            continue
        except Exception as exc:  # pragma: no cover - defensive path
            logger.error("Perplexity query failed for %s: %s", query, exc)
            continue

        for result in results:
            document = _result_to_document(
                result,
                mode=mode,
                query=query,
                priority_domains=watchlist.priority_domains,
            )
            if document is None:
                continue
            source_url = str(document["source_url"])
            if source_url in seen_urls:
                continue
            seen_urls.add(source_url)
            documents.append(document)

    logger.info(
        "Discovery Brain [%s]: %d docs after %d queries, remaining budget %.3f",
        mode,
        len(documents),
        executed_queries,
        budget.get_remaining(mode),
    )
    return documents


def collect_perplexity_discovery(
    *,
    client_id: str,
    watchlist_id: str | None = None,
    **kwargs,
) -> list[dict[str, object]] | dict[str, object]:
    """Replacement for the watch-first Tavily web_search collector."""
    return _collect_mode("discovery", client_id=client_id, watchlist_id=watchlist_id)


def collect_perplexity_press(
    *,
    client_id: str,
    watchlist_id: str | None = None,
    **kwargs,
) -> list[dict[str, object]] | dict[str, object]:
    """Discovery Brain press collector using domain-filtered Search API."""
    return _collect_mode("press", client_id=client_id, watchlist_id=watchlist_id)


def collect_perplexity_reddit(
    *,
    client_id: str,
    watchlist_id: str | None = None,
    **kwargs,
) -> list[dict[str, object]] | dict[str, object]:
    """Discovery Brain reddit collector using domain-filtered Search API."""
    return _collect_mode("reddit", client_id=client_id, watchlist_id=watchlist_id)
