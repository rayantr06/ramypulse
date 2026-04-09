from __future__ import annotations

import importlib


def _import_module(module_name: str):
    return importlib.import_module(module_name)


def test_collect_youtube_search_results_reads_comments(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.youtube_search")

    class _FakeExecute:
        def __init__(self, payload):
            self.payload = payload

        def execute(self):
            return self.payload

    class _FakeService:
        def search(self):
            return self

        def commentThreads(self):
            return self

        def list(self, **kwargs):
            if kwargs.get("type") == "video":
                return _FakeExecute(
                    {
                        "items": [
                            {"id": {"videoId": "vid-1"}, "snippet": {"title": "Elio review"}}
                        ]
                    }
                )
            return _FakeExecute(
                {
                    "items": [
                        {
                            "snippet": {
                                "topLevelComment": {
                                    "snippet": {"textDisplay": "Le prix est trop eleve"}
                                }
                            }
                        }
                    ]
                }
            )

    monkeypatch.setattr(collector.config, "YOUTUBE_API_KEY", "yt-key", raising=False)
    monkeypatch.setattr(collector, "build", lambda *args, **kwargs: _FakeService())

    documents = collector.collect_youtube_search_results(
        client_id="tenant-alpha",
        keywords=["elio"],
        max_videos=3,
        max_comments=5,
    )

    assert documents[0]["raw_metadata"]["channel"] == "youtube"
    assert "prix" in documents[0]["raw_text"].lower()
    assert documents[0]["source_url"] == "https://www.youtube.com/watch?v=vid-1"


def test_collect_youtube_search_results_loads_keywords_from_watchlist(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.youtube_search")

    class _FakeExecute:
        def __init__(self, payload):
            self.payload = payload

        def execute(self):
            return self.payload

    class _FakeService:
        def search(self):
            return self

        def commentThreads(self):
            return self

        def list(self, **kwargs):
            if kwargs.get("type") == "video":
                assert kwargs["q"] == "cevital OR elio"
                return _FakeExecute({"items": []})
            return _FakeExecute({"items": []})

    monkeypatch.setattr(collector.config, "YOUTUBE_API_KEY", "yt-key", raising=False)
    monkeypatch.setattr(collector, "build", lambda *args, **kwargs: _FakeService())
    monkeypatch.setattr(
        collector,
        "get_watchlist",
        lambda watchlist_id: {
            "watchlist_id": watchlist_id,
            "client_id": "tenant-alpha",
            "filters": {"keywords": ["cevital", "elio"]},
        },
    )

    documents = collector.collect_youtube_search_results(
        client_id="tenant-alpha",
        watchlist_id="watch-yt",
    )

    assert documents == []
