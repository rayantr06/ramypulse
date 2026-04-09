from __future__ import annotations

import importlib

import pytest


def _import_module(module_name: str):
    return importlib.import_module(module_name)


def test_collect_public_url_seed_extracts_article_text(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.public_url_seed")

    class _FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        collector.requests,
        "get",
        lambda url, timeout, headers: _FakeResponse(
            """
            <html>
              <head><title>Brand story</title></head>
              <body>
                <article><p>Le produit Elio est critique pour son prix.</p></article>
              </body>
            </html>
            """
        ),
    )

    documents = collector.collect_public_url_seed(
        client_id="tenant-alpha",
        brand_name="Cevital Elio",
        seed_urls=["https://example.com/brand"],
    )

    assert len(documents) == 1
    assert "prix" in documents[0]["raw_text"].lower()
    assert documents[0]["source_url"] == "https://example.com/brand"
    assert documents[0]["raw_metadata"]["channel"] == "public_url_seed"


def test_collect_public_url_seed_loads_brand_and_urls_from_watchlist(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.public_url_seed")

    monkeypatch.setattr(
        collector,
        "get_watchlist",
        lambda watchlist_id: {
            "watchlist_id": watchlist_id,
            "client_id": "tenant-alpha",
            "filters": {
                "brand_name": "Cevital Elio",
                "seed_urls": ["https://example.com/seed"],
            },
        },
    )
    monkeypatch.setattr(
        collector,
        "_fetch_html",
        lambda url: "<html><body><article>Prix trop eleve pour Elio.</article></body></html>",
    )

    documents = collector.collect_public_url_seed(
        client_id="tenant-alpha",
        watchlist_id="watch-001",
    )

    assert len(documents) == 1
    assert documents[0]["raw_payload"]["brand_name"] == "Cevital Elio"
    assert documents[0]["source_url"] == "https://example.com/seed"


def test_collect_public_url_seed_rejects_cross_tenant_watchlist(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.public_url_seed")

    monkeypatch.setattr(
        collector,
        "get_watchlist",
        lambda watchlist_id: {
            "watchlist_id": watchlist_id,
            "client_id": "tenant-other",
            "filters": {
                "brand_name": "Cevital Elio",
                "seed_urls": ["https://example.com/seed"],
            },
        },
    )

    with pytest.raises(ValueError, match="tenant"):
        collector.collect_public_url_seed(
            client_id="tenant-alpha",
            watchlist_id="watch-001",
        )
