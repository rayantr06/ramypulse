"""Routage résilient Google Maps : Apify complet, Places en repli."""

from __future__ import annotations

from core.watch_runs import run_service


def test_google_maps_prefers_apify_when_configured(monkeypatch) -> None:
    expected = [{"raw_text": "Avis complet"}]
    monkeypatch.setattr(run_service.config, "APIFY_API_KEY", "token")
    monkeypatch.setattr(
        run_service,
        "collect_google_maps_reviews_apify",
        lambda **_kwargs: expected,
    )
    monkeypatch.setattr(
        run_service,
        "collect_google_maps_reviews",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected fallback")),
    )

    assert run_service.collect_google_maps_adaptive(
        client_id="tenant-1", watchlist_id="watch-1"
    ) == expected


def test_google_maps_falls_back_when_apify_fails(monkeypatch) -> None:
    fallback = {"status": "success", "documents": [{"raw_text": "Avis Places"}]}
    monkeypatch.setattr(run_service.config, "APIFY_API_KEY", "token")
    monkeypatch.setattr(
        run_service,
        "collect_google_maps_reviews_apify",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("actor unavailable")),
    )
    monkeypatch.setattr(
        run_service,
        "collect_google_maps_reviews",
        lambda **_kwargs: fallback,
    )

    assert run_service.collect_google_maps_adaptive(
        client_id="tenant-1", watchlist_id="watch-1"
    ) == fallback
