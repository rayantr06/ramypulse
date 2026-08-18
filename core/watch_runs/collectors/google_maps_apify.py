"""Collecte d'avis Google Maps via Apify.

Pourquoi ce collecteur en plus de `google_maps_reviews.py`. L'API Places
officielle plafonne a **5 avis par lieu**, ce qui suffit a mesurer la diversite
des lieux mais pas a constituer un corpus. L'acteur `compass/crawler-google-places`
fait la decouverte des lieux et l'extraction des avis en un seul passage, sans
ce plafond.

Deux choix de conception importants :

- `scrapeReviewsPersonalData` est force a `False`. L'acteur inclut les donnees
  des auteurs par defaut ; ne jamais les demander est plus sur que les collecter
  puis les retirer.
- Quand une langue est demandee, Google renvoie aussi des avis **traduits** vers
  cette langue. Ils sont ecartes en comparant `originalLanguage` a la langue
  demandee, sans quoi une partie du corpus serait des traductions machine
  presentees comme des avis authentiques.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Iterable

import config
from core.watch_runs.collectors.apify_utils import default_dataset_id
from core.watchlists.watchlist_manager import get_watchlist

try:
    from apify_client import ApifyClient
except ImportError:  # pragma: no cover - exercised when dependency is unavailable
    ApifyClient = None

logger = logging.getLogger(__name__)

APIFY_MAPS_ACTOR = "compass/crawler-google-places"
_DEFAULT_MAX_PLACES = 50
_DEFAULT_MAX_REVIEWS = 30


def _resolve_apify_token() -> str | None:
    return str(getattr(config, "APIFY_API_KEY", "") or "").strip() or None


def _resolve_search_terms(
    *,
    client_id: str,
    watchlist_id: str | None,
    search_terms: Iterable[str] | None,
) -> list[str]:
    terms = [str(term).strip() for term in (search_terms or []) if str(term).strip()]
    if terms or not watchlist_id:
        return list(dict.fromkeys(terms))

    watchlist = get_watchlist(watchlist_id, client_id=client_id)
    if not watchlist:
        raise ValueError(f"watchlist not found or tenant mismatch: {watchlist_id}")
    filters = watchlist.get("filters") or {}
    candidates = [
        filters.get("brand_name"),
        filters.get("product_name"),
        *(filters.get("keywords") or []),
        *(filters.get("competitors") or []),
    ]
    return list(
        dict.fromkeys(
            str(candidate).strip()
            for candidate in candidates
            if str(candidate or "").strip()
        )
    )


def _clean_text(text: object) -> str | None:
    normalized = str(text or "").strip()
    if len(normalized) < 3:
        return None
    normalized = re.sub(r"http\S+|www\.\S+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized if len(normalized) >= 3 else None


def _document_id(*, place_id: str, review_id: str, text: str) -> str:
    stable_value = "|".join((place_id, review_id, text))
    return hashlib.md5(stable_value.encode("utf-8")).hexdigest()


def _build_run_input(
    *,
    search_terms: list[str],
    country_code: str | None,
    city: str | None,
    language: str | None,
    max_places: int,
    max_reviews_per_place: int,
    reviews_since: str | None,
) -> dict:
    run_input: dict[str, object] = {
        "searchStringsArray": search_terms,
        "maxCrawledPlacesPerSearch": max_places,
        "maxReviews": max_reviews_per_place,
        "reviewsSort": "newest",
        # Ne jamais demander les donnees personnelles des auteurs.
        "scrapeReviewsPersonalData": False,
        "skipClosedPlaces": True,
    }
    if country_code:
        run_input["countryCode"] = country_code
    if city:
        run_input["city"] = city
    if language:
        run_input["language"] = language
    if reviews_since:
        run_input["reviewsStartDate"] = reviews_since
    return run_input


def _review_to_document(
    review: dict,
    *,
    place: dict,
    language: str | None,
    watchlist_id: str | None = None,
) -> dict[str, object] | None:
    raw_text = _clean_text(review.get("text"))
    if not raw_text:
        return None

    original_language = str(review.get("originalLanguage") or "").strip().lower()
    if language and original_language and original_language != language.strip().lower():
        # Avis traduit vers la langue demandee : ce n'est pas le texte d'origine.
        return None

    place_id = str(place.get("placeId") or "").strip()
    review_id = str(review.get("reviewId") or "").strip()
    return {
        "external_document_id": _document_id(
            place_id=place_id, review_id=review_id, text=raw_text
        ),
        "raw_text": raw_text,
        "source_url": str(review.get("reviewUrl") or place.get("url") or "").strip(),
        "raw_payload": review,
        "raw_metadata": {
            "channel": "google_maps",
            "watchlist_id": watchlist_id,
            "source_url": str(review.get("reviewUrl") or place.get("url") or "").strip(),
            "place_id": place_id,
            "place_name": place.get("title"),
            "place_category": place.get("categoryName"),
            "place_city": place.get("city"),
            "place_country": place.get("countryCode"),
            "place_rating": place.get("totalScore"),
            "place_reviews_count": place.get("reviewsCount"),
            "rating": review.get("stars"),
            "original_language": original_language or None,
            "published_at": str(review.get("publishedAtDate") or ""),
            "review_id": review_id,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def collect_google_maps_reviews_apify(
    *,
    client_id: str,
    watchlist_id: str | None = None,
    search_terms: Iterable[str] | None = None,
    country_code: str | None = None,
    city: str | None = None,
    language: str | None = None,
    max_places: int = _DEFAULT_MAX_PLACES,
    max_reviews_per_place: int = _DEFAULT_MAX_REVIEWS,
    reviews_since: str | None = None,
) -> list[dict[str, object]] | dict[str, object]:
    """Collecte des avis Google Maps, ou renvoie un statut `skipped` explicite.

    `language` filtre sur la langue d'origine des avis. Le laisser a `None`
    conserve toutes les langues, ce qui est le bon choix pour un corpus
    algerien ou francais, arabe et arabizi coexistent.
    """
    apify_token = _resolve_apify_token()
    if not apify_token:
        return {"status": "skipped", "documents": [], "reason": "missing_api_key"}
    if ApifyClient is None:
        return {"status": "skipped", "documents": [], "reason": "missing_dependency"}

    terms = _resolve_search_terms(
        client_id=client_id,
        watchlist_id=watchlist_id,
        search_terms=search_terms,
    )
    if not terms:
        return {"status": "skipped", "documents": [], "reason": "no_search_terms"}

    run_input = _build_run_input(
        search_terms=terms,
        country_code=country_code,
        city=city,
        language=language,
        max_places=max_places,
        max_reviews_per_place=max_reviews_per_place,
        reviews_since=reviews_since,
    )

    apify_client = ApifyClient(apify_token)
    try:
        run = apify_client.actor(APIFY_MAPS_ACTOR).call(
            run_input=run_input, timeout_secs=1800
        )
    except Exception as exc:  # pragma: no cover - network failures are mocked in tests
        logger.warning("Google Maps collection failed for %s: %s", terms, exc)
        return {"status": "skipped", "documents": [], "reason": "actor_failed"}

    documents: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for place in apify_client.dataset(default_dataset_id(run)).iterate_items():
        for review in place.get("reviews") or []:
            document = _review_to_document(
                review,
                place=place,
                language=language,
                watchlist_id=watchlist_id,
            )
            if not document:
                continue
            external_document_id = str(document["external_document_id"])
            if external_document_id in seen_ids:
                continue
            seen_ids.add(external_document_id)
            documents.append(document)
    return documents
