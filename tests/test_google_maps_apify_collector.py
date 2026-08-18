"""Tests du collecteur d'avis Google Maps via Apify.

L'API Places officielle plafonne a 5 avis par lieu. L'acteur
`compass/crawler-google-places` fait la decouverte des lieux ET l'extraction
des avis en un seul passage, sans ce plafond.
"""
from __future__ import annotations

import importlib


def _mod():
    return importlib.import_module("core.watch_runs.collectors.google_maps_apify")


class _FakeActor:
    def __init__(self, recorder):
        self.recorder = recorder

    def call(self, run_input=None, **kwargs):
        self.recorder.append(run_input)
        return {"defaultDatasetId": "ds-1"}


class _FakeDataset:
    def __init__(self, items):
        self._items = items

    def iterate_items(self):
        return iter(self._items)


def _client(items, recorder):
    class _C:
        def actor(self, actor_id):
            return _FakeActor(recorder)

        def dataset(self, dataset_id):
            return _FakeDataset(items)

    return _C()


def _place(reviews, **kw):
    base = {
        "placeId": "p1",
        "title": "Clinique du Val",
        "categoryName": "Clinique",
        "totalScore": 3.8,
        "reviewsCount": 210,
        "city": "Alger",
        "countryCode": "DZ",
        "url": "https://maps.google.com/p1",
        "reviews": reviews,
    }
    base.update(kw)
    return base


def test_skips_without_api_key(monkeypatch) -> None:
    c = _mod()
    monkeypatch.setattr(c.config, "APIFY_API_KEY", "", raising=False)
    result = c.collect_google_maps_reviews_apify(client_id="t1", search_terms=["restaurant"])
    assert result == {"status": "skipped", "documents": [], "reason": "missing_api_key"}


def test_accepts_apify_v3_typed_run(monkeypatch) -> None:
    """Apify Client v3 retourne un objet typé, pas un dictionnaire camelCase."""
    c = _mod()

    class _TypedRun:
        default_dataset_id = "ds-v3"

    class _Actor:
        def call(self, **_kwargs):
            return _TypedRun()

    class _Client:
        def actor(self, _actor_id):
            return _Actor()

        def dataset(self, dataset_id):
            assert dataset_id == "ds-v3"
            return _FakeDataset([])

    monkeypatch.setattr(c.config, "APIFY_API_KEY", "k", raising=False)
    monkeypatch.setattr(c, "ApifyClient", lambda token: _Client())

    assert c.collect_google_maps_reviews_apify(
        client_id="t1", search_terms=["restaurant"]
    ) == []


def test_derives_search_terms_from_watchlist(monkeypatch) -> None:
    c = _mod()
    recorder: list[dict[str, object]] = []
    monkeypatch.setattr(c.config, "APIFY_API_KEY", "k", raising=False)
    monkeypatch.setattr(c, "ApifyClient", lambda token: _client([], recorder))
    monkeypatch.setattr(
        c,
        "get_watchlist",
        lambda watchlist_id, client_id=None: {
            "watchlist_id": watchlist_id,
            "client_id": client_id,
            "filters": {
                "brand_name": "Algérie Télécom",
                "product_name": "Idoom Fibre",
                "keywords": ["connexion", "service client"],
                "competitors": ["Djezzy"],
            },
        },
    )

    result = c.collect_google_maps_reviews_apify(
        client_id="t1", watchlist_id="watch-1"
    )

    assert result == []
    assert recorder[0]["searchStringsArray"] == [
        "Algérie Télécom",
        "Idoom Fibre",
        "connexion",
        "service client",
        "Djezzy",
    ]


def test_skips_without_search_terms(monkeypatch) -> None:
    c = _mod()
    monkeypatch.setattr(c.config, "APIFY_API_KEY", "k", raising=False)
    monkeypatch.setattr(c, "ApifyClient", lambda token: _client([], []))
    result = c.collect_google_maps_reviews_apify(client_id="t1", search_terms=[])
    assert result == {"status": "skipped", "documents": [], "reason": "no_search_terms"}


def test_returns_review_documents_with_place_context(monkeypatch) -> None:
    """La note et la categorie du lieu doivent remonter : ce sont les deux
    signaux qui rendent cette source superieure aux pages de marque."""
    c = _mod()
    items = [_place([
        {
            "reviewId": "r1",
            "text": "Attente de 3 heures, personnel desagreable",
            "stars": 1,
            "publishedAtDate": "2026-06-01T10:00:00Z",
            "originalLanguage": "fr",
            "reviewUrl": "https://maps.google.com/r1",
        }
    ])]
    monkeypatch.setattr(c.config, "APIFY_API_KEY", "k", raising=False)
    monkeypatch.setattr(c, "ApifyClient", lambda token: _client(items, []))

    docs = c.collect_google_maps_reviews_apify(
        client_id="t1", search_terms=["clinique"], country_code="dz")

    assert len(docs) == 1
    doc = docs[0]
    assert doc["raw_text"] == "Attente de 3 heures, personnel desagreable"
    meta = doc["raw_metadata"]
    assert meta["channel"] == "google_maps"
    assert meta["rating"] == 1
    assert meta["place_name"] == "Clinique du Val"
    assert meta["place_category"] == "Clinique"
    assert meta["place_city"] == "Alger"
    assert meta["original_language"] == "fr"


def test_personal_data_disabled_by_default(monkeypatch) -> None:
    """Ne pas demander les donnees personnelles des auteurs.

    L'acteur les inclut par defaut. Les collecter puis les retirer ensuite
    serait une precaution plus faible que ne jamais les demander.
    """
    c = _mod()
    rec: list = []
    monkeypatch.setattr(c.config, "APIFY_API_KEY", "k", raising=False)
    monkeypatch.setattr(c, "ApifyClient", lambda token: _client([], rec))
    c.collect_google_maps_reviews_apify(client_id="t1", search_terms=["restaurant"])
    assert rec, "l'acteur n'a pas ete appele"
    assert rec[0]["scrapeReviewsPersonalData"] is False


def test_passes_geography_and_freshness(monkeypatch) -> None:
    c = _mod()
    rec: list = []
    monkeypatch.setattr(c.config, "APIFY_API_KEY", "k", raising=False)
    monkeypatch.setattr(c, "ApifyClient", lambda token: _client([], rec))
    c.collect_google_maps_reviews_apify(
        client_id="t1", search_terms=["hotel"], country_code="dz",
        city="Oran", reviews_since="2024-01-01", max_reviews_per_place=50)
    run_input = rec[0]
    assert run_input["countryCode"] == "dz"
    assert run_input["city"] == "Oran"
    assert run_input["reviewsStartDate"] == "2024-01-01"
    assert run_input["maxReviews"] == 50


def test_drops_translated_duplicates(monkeypatch) -> None:
    """Demander une langue renvoie aussi des avis traduits vers elle.

    Sans filtre, une partie du corpus serait des traductions machine
    presentees comme des avis authentiques.
    """
    c = _mod()
    items = [_place([
        {"reviewId": "r1", "text": "Service excellent", "originalLanguage": "fr", "stars": 5},
        {"reviewId": "r2", "text": "Service excellent", "originalLanguage": "ar", "stars": 5},
    ])]
    monkeypatch.setattr(c.config, "APIFY_API_KEY", "k", raising=False)
    monkeypatch.setattr(c, "ApifyClient", lambda token: _client(items, []))

    docs = c.collect_google_maps_reviews_apify(
        client_id="t1", search_terms=["restaurant"], language="fr")

    assert len(docs) == 1
    assert docs[0]["raw_metadata"]["original_language"] == "fr"


def test_keeps_all_languages_when_not_filtered(monkeypatch) -> None:
    c = _mod()
    items = [_place([
        {"reviewId": "r1", "text": "Service excellent", "originalLanguage": "fr", "stars": 5},
        {"reviewId": "r2", "text": "خدمة ممتازة", "originalLanguage": "ar", "stars": 5},
    ])]
    monkeypatch.setattr(c.config, "APIFY_API_KEY", "k", raising=False)
    monkeypatch.setattr(c, "ApifyClient", lambda token: _client(items, []))

    docs = c.collect_google_maps_reviews_apify(
        client_id="t1", search_terms=["restaurant"], language=None)
    assert len(docs) == 2


def test_deduplicates_same_review_id(monkeypatch) -> None:
    c = _mod()
    items = [_place([
        {"reviewId": "r1", "text": "Tres bien", "originalLanguage": "fr", "stars": 5},
        {"reviewId": "r1", "text": "Tres bien", "originalLanguage": "fr", "stars": 5},
    ])]
    monkeypatch.setattr(c.config, "APIFY_API_KEY", "k", raising=False)
    monkeypatch.setattr(c, "ApifyClient", lambda token: _client(items, []))

    docs = c.collect_google_maps_reviews_apify(client_id="t1", search_terms=["x"])
    assert len(docs) == 1


def test_ignores_empty_reviews(monkeypatch) -> None:
    c = _mod()
    items = [_place([
        {"reviewId": "r1", "text": "", "originalLanguage": "fr", "stars": 5},
        {"reviewId": "r2", "text": None, "originalLanguage": "fr", "stars": 4},
    ])]
    monkeypatch.setattr(c.config, "APIFY_API_KEY", "k", raising=False)
    monkeypatch.setattr(c, "ApifyClient", lambda token: _client(items, []))

    docs = c.collect_google_maps_reviews_apify(client_id="t1", search_terms=["x"])
    assert docs == []
