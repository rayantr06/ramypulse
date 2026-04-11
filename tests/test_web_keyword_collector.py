from __future__ import annotations

import importlib


def _import_module(module_name: str):
    return importlib.import_module(module_name)


def test_collect_web_keyword_results_converts_search_hits_to_raw_documents(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.web_keyword")

    class _FakeClient:
        def search(self, **kwargs):
            return {
                "results": [
                    {
                        "url": "https://news.example.com/elio?utm_source=meta",
                        "title": "Elio fait debat",
                        "content": "Les consommateurs se plaignent du prix de Elio.",
                    }
                ]
            }

    monkeypatch.setattr(collector.config, "TAVILY_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(collector, "TavilyClient", lambda api_key: _FakeClient())

    documents = collector.collect_web_keyword_results(
        client_id="tenant-alpha",
        keywords=["cevital", "elio"],
        max_results=5,
    )

    assert len(documents) == 1
    assert documents[0]["raw_metadata"]["channel"] == "web_search"
    assert documents[0]["source_url"] == "https://news.example.com/elio"
    assert "prix" in documents[0]["raw_text"].lower()


def test_collect_web_keyword_results_loads_keywords_from_watchlist(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.web_keyword")

    class _FakeClient:
        def search(self, **kwargs):
            assert kwargs["query"] == "cevital OR elio"
            return {
                "results": [
                    {
                        "url": "https://news.example.com/elio",
                        "title": "Elio fait debat",
                        "content": "Retour clients sur Elio.",
                    }
                ]
            }

    monkeypatch.setattr(collector.config, "TAVILY_API_KEY", "test-key", raising=False)
    monkeypatch.setattr(collector, "TavilyClient", lambda api_key: _FakeClient())
    monkeypatch.setattr(
        collector,
        "get_watchlist",
        lambda watchlist_id: {
            "watchlist_id": watchlist_id,
            "client_id": "tenant-alpha",
            "filters": {"keywords": ["cevital", "elio"]},
        },
    )

    documents = collector.collect_web_keyword_results(
        client_id="tenant-alpha",
        watchlist_id="watch-001",
    )

    assert len(documents) == 1
    assert documents[0]["raw_payload"]["keywords"] == ["cevital", "elio"]


def test_collect_web_keyword_results_skips_without_api_key(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.web_keyword")

    monkeypatch.setattr(collector.config, "TAVILY_API_KEY", "", raising=False)

    documents = collector.collect_web_keyword_results(
        client_id="tenant-alpha",
        keywords=["cevital", "elio"],
    )

    assert documents == {"status": "skipped", "documents": [], "reason": "missing_api_key"}
