from __future__ import annotations

import importlib


def _import_module(module_name: str):
    return importlib.import_module(module_name)


def test_collect_facebook_comments_apify_skips_without_api_key(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.facebook_apify")

    monkeypatch.setattr(collector.config, "APIFY_API_KEY", "", raising=False)

    result = collector.collect_facebook_comments_apify(
        client_id="tenant-alpha",
        seed_urls=["https://www.facebook.com/ramy"],
    )

    assert result == {"status": "skipped", "documents": [], "reason": "missing_api_key"}


def test_collect_facebook_comments_apify_loads_seed_urls_from_watchlist(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.facebook_apify")

    class _FakeActor:
        def __init__(self, dataset_id: str):
            self.dataset_id = dataset_id

        def call(self, **kwargs):
            return {"defaultDatasetId": self.dataset_id}

    class _FakeDataset:
        def __init__(self, items):
            self._items = items

        def iterate_items(self):
            return iter(self._items)

    class _FakeClient:
        def actor(self, actor_id: str):
            if "posts" in actor_id:
                return _FakeActor("fb-posts")
            return _FakeActor("fb-comments")

        def dataset(self, dataset_id: str):
            if dataset_id == "fb-posts":
                return _FakeDataset([])
            return _FakeDataset([])

    monkeypatch.setattr(collector.config, "APIFY_API_KEY", "apify-key", raising=False)
    monkeypatch.setattr(collector, "ApifyClient", lambda token: _FakeClient())
    monkeypatch.setattr(
        collector,
        "get_watchlist",
        lambda watchlist_id: {
            "watchlist_id": watchlist_id,
            "client_id": "tenant-alpha",
            "filters": {"seed_urls": ["https://www.facebook.com/ramy"]},
        },
    )

    result = collector.collect_facebook_comments_apify(
        client_id="tenant-alpha",
        watchlist_id="watch-fb",
        max_posts=1,
    )

    assert result == []


def test_collect_facebook_comments_apify_returns_documents(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.facebook_apify")

    class _FakeActor:
        def __init__(self, dataset_id: str):
            self.dataset_id = dataset_id

        def call(self, **kwargs):
            return {"defaultDatasetId": self.dataset_id}

    class _FakeDataset:
        def __init__(self, items):
            self._items = items

        def iterate_items(self):
            return iter(self._items)

    class _FakeClient:
        def actor(self, actor_id: str):
            if "posts" in actor_id:
                return _FakeActor("fb-posts")
            return _FakeActor("fb-comments")

        def dataset(self, dataset_id: str):
            if dataset_id == "fb-posts":
                return _FakeDataset([{"postUrl": "https://www.facebook.com/post-1"}])
            return _FakeDataset(
                [
                    {
                        "text": "Bon jus Ramy",
                        "profileName": "Ahmed",
                        "date": "2026-01-15T10:00:00Z",
                        "likesCount": 5,
                        "commentUrl": "https://www.facebook.com/comment-1",
                        "comments": [],
                    }
                ]
            )

    monkeypatch.setattr(collector.config, "APIFY_API_KEY", "apify-key", raising=False)
    monkeypatch.setattr(collector, "ApifyClient", lambda token: _FakeClient())

    documents = collector.collect_facebook_comments_apify(
        client_id="tenant-alpha",
        seed_urls=["https://www.facebook.com/ramy"],
        max_posts=1,
        max_comments_per_post=10,
    )

    assert len(documents) == 1
    assert documents[0]["raw_text"] == "Bon jus Ramy"
    assert documents[0]["raw_metadata"]["channel"] == "facebook"
    assert documents[0]["source_url"] == "https://www.facebook.com/comment-1"
    assert documents[0]["raw_metadata"]["date"] == "2026-01-15T10:00:00Z"
    assert documents[0]["raw_metadata"]["comment_url"] == "https://www.facebook.com/comment-1"


def test_collect_facebook_comments_apify_deduplicates(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.facebook_apify")

    class _FakeActor:
        def __init__(self, dataset_id: str):
            self.dataset_id = dataset_id

        def call(self, **kwargs):
            return {"defaultDatasetId": self.dataset_id}

    class _FakeDataset:
        def __init__(self, items):
            self._items = items

        def iterate_items(self):
            return iter(self._items)

    duplicate = {
        "text": "Dupe",
        "profileName": "Bob",
        "date": "2026-01-15T10:00:00Z",
        "likesCount": 0,
        "commentUrl": "",
        "comments": [],
    }

    class _FakeClient:
        def actor(self, actor_id: str):
            if "posts" in actor_id:
                return _FakeActor("fb-posts")
            return _FakeActor("fb-comments")

        def dataset(self, dataset_id: str):
            if dataset_id == "fb-posts":
                return _FakeDataset([{"postUrl": "https://www.facebook.com/post-1"}])
            return _FakeDataset([duplicate, duplicate])

    monkeypatch.setattr(collector.config, "APIFY_API_KEY", "apify-key", raising=False)
    monkeypatch.setattr(collector, "ApifyClient", lambda token: _FakeClient())

    documents = collector.collect_facebook_comments_apify(
        client_id="tenant-alpha",
        seed_urls=["https://www.facebook.com/ramy"],
    )

    assert len(documents) == 1


def test_collect_facebook_comments_apify_deduplicates_by_text_and_author_across_posts(
    monkeypatch,
) -> None:
    collector = _import_module("core.watch_runs.collectors.facebook_apify")

    class _FakeActor:
        def __init__(self, dataset_id: str):
            self.dataset_id = dataset_id

        def call(self, **kwargs):
            return {"defaultDatasetId": self.dataset_id}

    class _FakeDataset:
        def __init__(self, items):
            self._items = items

        def iterate_items(self):
            return iter(self._items)

    duplicate_a = {
        "text": "Même texte",
        "profileName": "Bob",
        "date": "2026-01-15T10:00:00Z",
        "likesCount": 0,
        "commentUrl": "",
        "comments": [],
    }
    duplicate_b = {
        "text": "Même texte",
        "profileName": "Bob",
        "date": "2026-01-15T10:30:00Z",
        "likesCount": 2,
        "commentUrl": "",
        "comments": [],
    }

    class _FakeClient:
        def actor(self, actor_id: str):
            if "posts" in actor_id:
                return _FakeActor("fb-posts")
            return _FakeActor("fb-comments")

        def dataset(self, dataset_id: str):
            if dataset_id == "fb-posts":
                return _FakeDataset(
                    [
                        {"postUrl": "https://www.facebook.com/post-1"},
                        {"postUrl": "https://www.facebook.com/post-2"},
                    ]
                )
            if not hasattr(self, "_comment_call_count"):
                self._comment_call_count = 0
            self._comment_call_count += 1
            return _FakeDataset([duplicate_a] if self._comment_call_count == 1 else [duplicate_b])

    monkeypatch.setattr(collector.config, "APIFY_API_KEY", "apify-key", raising=False)
    monkeypatch.setattr(collector, "ApifyClient", lambda token: _FakeClient())

    documents = collector.collect_facebook_comments_apify(
        client_id="tenant-alpha",
        seed_urls=["https://www.facebook.com/ramy"],
        max_posts=2,
    )

    assert len(documents) == 1


def test_collect_facebook_comments_apify_includes_nested_replies(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.facebook_apify")

    class _FakeActor:
        def __init__(self, dataset_id: str):
            self.dataset_id = dataset_id

        def call(self, **kwargs):
            return {"defaultDatasetId": self.dataset_id}

    class _FakeDataset:
        def __init__(self, items):
            self._items = items

        def iterate_items(self):
            return iter(self._items)

    class _FakeClient:
        def actor(self, actor_id: str):
            if "posts" in actor_id:
                return _FakeActor("fb-posts")
            return _FakeActor("fb-comments")

        def dataset(self, dataset_id: str):
            if dataset_id == "fb-posts":
                return _FakeDataset([{"postUrl": "https://www.facebook.com/post-1"}])
            return _FakeDataset(
                [
                    {
                        "text": "Comment parent",
                        "profileName": "Ahmed",
                        "date": "2026-01-15T10:00:00Z",
                        "likesCount": 5,
                        "commentsCount": 1,
                        "commentUrl": "https://www.facebook.com/comment-1",
                        "comments": [
                            {
                                "text": "Réponse imbriquée",
                                "profileName": "Sara",
                                "date": "2026-01-15T10:05:00Z",
                                "likesCount": 1,
                                "commentUrl": "https://www.facebook.com/comment-2",
                            }
                        ],
                    }
                ]
            )

    monkeypatch.setattr(collector.config, "APIFY_API_KEY", "apify-key", raising=False)
    monkeypatch.setattr(collector, "ApifyClient", lambda token: _FakeClient())

    documents = collector.collect_facebook_comments_apify(
        client_id="tenant-alpha",
        seed_urls=["https://www.facebook.com/ramy"],
        max_posts=1,
    )

    assert len(documents) == 2
    reply_document = documents[1]
    assert reply_document["raw_text"] == "Réponse imbriquée"
    assert reply_document["raw_metadata"]["is_reply"] is True
    assert reply_document["raw_metadata"]["comment_url"] == "https://www.facebook.com/comment-2"


def test_collect_facebook_comments_apify_skips_when_only_apify_token_set(monkeypatch) -> None:
    """APIFY_API_TOKEN env var doit être ignoré — seul APIFY_API_KEY (config) est utilisé."""
    collector = _import_module("core.watch_runs.collectors.facebook_apify")

    monkeypatch.setattr(collector.config, "APIFY_API_KEY", "", raising=False)
    monkeypatch.setenv("APIFY_API_TOKEN", "legacy-token")

    result = collector.collect_facebook_comments_apify(
        client_id="tenant-alpha",
        seed_urls=["https://www.facebook.com/ramy"],
    )

    assert result == {"status": "skipped", "documents": [], "reason": "missing_api_key"}


def test_collect_instagram_comments_apify_skips_without_api_key(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.instagram_apify")

    monkeypatch.setattr(collector.config, "APIFY_API_KEY", "", raising=False)

    result = collector.collect_instagram_comments_apify(
        client_id="tenant-alpha",
        seed_urls=["https://www.instagram.com/ramy/"],
    )

    assert result == {"status": "skipped", "documents": [], "reason": "missing_api_key"}


def test_collect_instagram_comments_apify_returns_documents(monkeypatch) -> None:
    collector = _import_module("core.watch_runs.collectors.instagram_apify")

    class _FakeActor:
        def __init__(self, dataset_id: str):
            self.dataset_id = dataset_id

        def call(self, **kwargs):
            return {"defaultDatasetId": self.dataset_id}

    class _FakeDataset:
        def __init__(self, items):
            self._items = items

        def iterate_items(self):
            return iter(self._items)

    class _FakeClient:
        def actor(self, actor_id: str):
            if "post-scraper" in actor_id:
                return _FakeActor("ig-posts")
            return _FakeActor("ig-comments")

        def dataset(self, dataset_id: str):
            if dataset_id == "ig-posts":
                return _FakeDataset([{"url": "https://www.instagram.com/p/abc123/"}])
            return _FakeDataset(
                [
                    {
                        "text": "Super produit !",
                        "ownerUsername": "Fatima",
                        "timestamp": "2026-01-20T12:00:00Z",
                        "likesCount": 3,
                        "replyToId": None,
                    }
                ]
            )

    monkeypatch.setattr(collector.config, "APIFY_API_KEY", "apify-key", raising=False)
    monkeypatch.setattr(collector, "ApifyClient", lambda token: _FakeClient())

    documents = collector.collect_instagram_comments_apify(
        client_id="tenant-alpha",
        seed_urls=["https://www.instagram.com/ramy/"],
    )

    assert len(documents) == 1
    assert documents[0]["raw_text"] == "Super produit !"
    assert documents[0]["raw_metadata"]["channel"] == "instagram"
    assert documents[0]["raw_metadata"]["date"] == "2026-01-20T12:00:00Z"
    assert documents[0]["raw_metadata"]["replies_count"] == 0


def test_facebook_and_instagram_registered_as_channels() -> None:
    from core.watch_runs.run_service import DEFAULT_COLLECTORS

    assert "facebook" in DEFAULT_COLLECTORS
    assert "instagram" in DEFAULT_COLLECTORS
