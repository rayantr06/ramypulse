from __future__ import annotations

import importlib


def _import_module(module_name: str):
    return importlib.import_module(module_name)


def test_collect_google_maps_reviews_returns_skipped_without_api_key(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.google_maps_reviews")

    monkeypatch.setattr(collector.config, "GOOGLE_MAPS_API_KEY", "", raising=False)

    result = collector.collect_google_maps_reviews(
        client_id="tenant-alpha",
        place_query="Ramy Alger",
    )

    assert result["status"] == "skipped"
    assert result["documents"] == []


def test_collect_google_maps_reviews_extracts_reviews(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.google_maps_reviews")

    class _FakeClient:
        def places(self, query):
            assert query == "Ramy Alger"
            return {"results": [{"place_id": "place-1"}]}

        def place(self, place_id, fields):
            assert place_id == "place-1"
            return {
                "result": {
                    "reviews": [
                        {
                            "author_name": "Sara",
                            "text": "Produit tres aime",
                            "time": 1712345678,
                        }
                    ]
                }
            }

    monkeypatch.setattr(collector.config, "GOOGLE_MAPS_API_KEY", "maps-key", raising=False)
    monkeypatch.setattr(collector.googlemaps, "Client", lambda key: _FakeClient())

    result = collector.collect_google_maps_reviews(
        client_id="tenant-alpha",
        place_query="Ramy Alger",
    )

    assert result["status"] == "success"
    assert result["documents"][0]["raw_metadata"]["channel"] == "google_maps"
    assert "aime" in result["documents"][0]["raw_text"].lower()


def test_collect_google_maps_reviews_builds_place_query_from_watchlist(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.google_maps_reviews")

    class _FakeClient:
        def places(self, query):
            assert query == "Ramy Citron"
            return {"results": []}

    monkeypatch.setattr(collector.config, "GOOGLE_MAPS_API_KEY", "maps-key", raising=False)
    monkeypatch.setattr(collector.googlemaps, "Client", lambda key: _FakeClient())
    monkeypatch.setattr(
        collector,
        "get_watchlist",
        lambda watchlist_id: {
            "watchlist_id": watchlist_id,
            "client_id": "tenant-alpha",
            "filters": {
                "brand_name": "Ramy",
                "product_name": "Citron",
            },
        },
    )

    result = collector.collect_google_maps_reviews(
        client_id="tenant-alpha",
        watchlist_id="watch-maps",
    )

    assert result == {"status": "success", "documents": []}
