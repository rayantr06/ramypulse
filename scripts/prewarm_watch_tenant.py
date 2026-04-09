"""Prewarm the safe expo tenant with a watch-first run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from api.data_loader import load_annotated_from_sqlite
from core.tenancy.tenant_paths import get_tenant_paths
from core.tenancy.client_manager import get_or_create_client, set_active_client
from core.watch_runs.run_service import start_watch_run
from core.watchlists.watchlist_manager import (
    create_watchlist,
    list_watchlists,
    update_watchlist,
)

DEFAULT_CHANNELS = ["public_url_seed", "web_search", "youtube", "google_maps"]
DEFAULT_KEYWORDS = ["ramy", "ramy juice", "ramy algerie", "ramy dz", "رامي"]


def _normalize_list(values: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        candidate = str(value or "").strip()
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(candidate)
    return normalized


def build_watch_seed_filters(
    *,
    brand_name: str,
    product_name: str | None = None,
    keywords: Iterable[str] | None = None,
    seed_urls: Iterable[str] | None = None,
    channels: Iterable[str] | None = None,
) -> dict[str, object]:
    normalized_keywords = _normalize_list(keywords) or DEFAULT_KEYWORDS.copy()
    brand_keyword = brand_name.strip()
    if brand_keyword and brand_keyword.lower() not in {value.lower() for value in normalized_keywords}:
        normalized_keywords.insert(0, brand_keyword)

    filters = {
        "brand_name": brand_name.strip(),
        "product_name": (product_name or "").strip() or None,
        "keywords": normalized_keywords,
        "seed_urls": _normalize_list(seed_urls),
        "competitors": [],
        "channels": [value.lower() for value in _normalize_list(channels) or DEFAULT_CHANNELS.copy()],
        "languages": ["fr", "ar"],
        "hashtags": [],
        "period_days": 7,
        "min_volume": 10,
    }
    return filters


def ensure_watchlist(
    *,
    client_id: str,
    watchlist_name: str,
    description: str,
    filters: dict[str, object],
) -> str:
    for watchlist in list_watchlists(is_active=False):
        if watchlist.get("client_id") != client_id:
            continue
        if watchlist.get("watchlist_name") != watchlist_name:
            continue
        update_watchlist(
            str(watchlist["watchlist_id"]),
            {
                "description": description,
                "scope_type": "watch_seed",
                "filters": filters,
                "is_active": 1,
            },
        )
        return str(watchlist["watchlist_id"])

    return create_watchlist(
        name=watchlist_name,
        description=description,
        scope_type="watch_seed",
        filters=filters,
        client_id=client_id,
    )


def prewarm_watch_tenant(
    *,
    client_id: str = config.SAFE_EXPO_CLIENT_ID,
    client_name: str = "Ramy Demo",
    brand_name: str = "Ramy",
    product_name: str = "Ramy",
    keywords: Iterable[str] | None = None,
    seed_urls: Iterable[str] | None = None,
    channels: Iterable[str] | None = None,
    min_docs: int = 50,
) -> dict[str, object]:
    client = get_or_create_client(client_id=client_id, client_name=client_name)
    resolved_client_id = str(client["client_id"])
    set_active_client(resolved_client_id)

    effective_filters = build_watch_seed_filters(
        brand_name=brand_name,
        product_name=product_name,
        keywords=keywords,
        seed_urls=seed_urls,
        channels=channels,
    )
    watchlist_id = ensure_watchlist(
        client_id=resolved_client_id,
        watchlist_name=f"{brand_name.strip()} Expo Watch",
        description=f"{brand_name.strip()} prewarmed watchlist for the expo-safe demo tenant.",
        filters=effective_filters,
    )

    run = start_watch_run(
        client_id=resolved_client_id,
        watchlist_id=watchlist_id,
        requested_channels=list(effective_filters["channels"]),
        run_async=False,
    ) or {}

    dataframe = load_annotated_from_sqlite(client_id=resolved_client_id)
    tenant_paths = get_tenant_paths(resolved_client_id)
    documents = int(len(dataframe))
    if documents < min_docs:
        raise RuntimeError(
            f"Prewarm failed for {resolved_client_id}: expected at least {min_docs} documents, got {documents}"
        )

    return {
        "client_id": resolved_client_id,
        "watchlist_id": watchlist_id,
        "run_id": run.get("run_id"),
        "run_status": run.get("status"),
        "documents": documents,
        "channels": list(effective_filters["channels"]),
        "annotated_path": str(tenant_paths.annotated_path),
        "index_path": str(tenant_paths.faiss_index_prefix),
    }


def _parse_multi_value(values: list[str] | None) -> list[str]:
    if not values:
        return []
    parsed: list[str] = []
    for value in values:
        parsed.extend(part.strip() for part in str(value).split(","))
    return _normalize_list(parsed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", default=config.SAFE_EXPO_CLIENT_ID)
    parser.add_argument("--client-name", default="Ramy Demo")
    parser.add_argument("--brand-name", default="Ramy")
    parser.add_argument("--product-name", default="Ramy")
    parser.add_argument("--keyword", dest="keywords", action="append")
    parser.add_argument("--seed-url", dest="seed_urls", action="append")
    parser.add_argument("--channel", dest="channels", action="append")
    parser.add_argument("--min-docs", type=int, default=50)
    args = parser.parse_args()

    try:
        summary = prewarm_watch_tenant(
            client_id=args.client_id,
            client_name=args.client_name,
            brand_name=args.brand_name,
            product_name=args.product_name,
            keywords=_parse_multi_value(args.keywords),
            seed_urls=_parse_multi_value(args.seed_urls),
            channels=_parse_multi_value(args.channels),
            min_docs=args.min_docs,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
