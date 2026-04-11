"""Collector for Google Maps public reviews."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Iterable

import config

try:
    import googlemaps
except ImportError:  # pragma: no cover - exercised when dependency is unavailable
    googlemaps = SimpleNamespace(Client=None)

from core.watchlists.watchlist_manager import get_watchlist


def _normalize_place_query(place_query: str | None) -> str:
    return " ".join(str(place_query or "").strip().split())


def _resolve_place_query(
    *,
    client_id: str,
    watchlist_id: str | None,
    place_query: str | None,
) -> str:
    resolved_place_query = _normalize_place_query(place_query)
    if resolved_place_query or not watchlist_id:
        return resolved_place_query

    watchlist = get_watchlist(watchlist_id)
    if not watchlist:
        raise ValueError(f"watchlist not found: {watchlist_id}")
    if watchlist.get("client_id") != client_id:
        raise ValueError(f"watchlist tenant mismatch for {watchlist_id}")

    filters = watchlist.get("filters") or {}
    parts = [
        str(filters.get("brand_name") or "").strip(),
        str(filters.get("product_name") or "").strip(),
    ]
    return _normalize_place_query(" ".join(part for part in parts if part))


def collect_google_maps_reviews(
    *,
    client_id: str,
    watchlist_id: str | None = None,
    place_query: str | None = None,
) -> dict[str, object]:
    """Collect public reviews from Google Maps, or skip cleanly when unavailable."""
    if not config.GOOGLE_MAPS_API_KEY or getattr(googlemaps, "Client", None) is None:
        return {"status": "skipped", "documents": [], "reason": "missing_api_key"}

    resolved_place_query = _resolve_place_query(
        client_id=client_id,
        watchlist_id=watchlist_id,
        place_query=place_query,
    )
    if not resolved_place_query:
        return {"status": "success", "documents": []}

    client = googlemaps.Client(key=config.GOOGLE_MAPS_API_KEY)
    search = client.places(query=resolved_place_query)
    results = list(search.get("results") or [])
    if not results:
        return {"status": "success", "documents": []}

    place_id = str(results[0].get("place_id") or "").strip()
    if not place_id:
        return {"status": "success", "documents": []}

    details = client.place(place_id=place_id, fields=["name", "rating", "reviews"])
    reviews = list(details.get("result", {}).get("reviews") or [])
    documents: list[dict[str, object]] = []
    for index, review in enumerate(reviews):
        text = str(review.get("text") or "").strip()
        if not text:
            continue
        source_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
        documents.append(
            {
                "external_document_id": f"{place_id}:{index}",
                "raw_text": text,
                "source_url": source_url,
                "raw_payload": {
                    **review,
                    "place_id": place_id,
                    "watchlist_id": watchlist_id,
                },
                "raw_metadata": {
                    "channel": "google_maps",
                    "place_id": place_id,
                    "place_query": resolved_place_query,
                    "source_url": source_url,
                },
            }
        )
    return {"status": "success", "documents": documents}
