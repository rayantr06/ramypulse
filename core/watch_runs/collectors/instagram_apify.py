"""Collector for Instagram comments via Apify."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Iterable

import config

from core.watchlists.watchlist_manager import get_watchlist

try:
    from apify_client import ApifyClient
except ImportError:  # pragma: no cover - exercised when dependency is unavailable
    ApifyClient = None

logger = logging.getLogger(__name__)

APIFY_IG_POSTS = "apify/instagram-post-scraper"
APIFY_IG_COMMENTS = "apify/instagram-comment-scraper"
_INSTAGRAM_POST_URL_RE = re.compile(
    r"^https?://(?:www\.)?instagram\.com/(?:(?:[^!@#$%^&*(){},'\"/\s`\\=-]+/)?(?:p|reel)|reels)/[^/]+/?$",
    flags=re.IGNORECASE,
)


def _resolve_apify_token() -> str | None:
    return (
        str(getattr(config, "APIFY_API_KEY", "") or "").strip()
        or str(os.getenv("APIFY_API_KEY") or "").strip()
        or None
    )


def _normalize_seed_urls(seed_urls: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_seed_url in seed_urls or []:
        seed_url = str(raw_seed_url or "").strip()
        lowered = seed_url.lower()
        if not seed_url or "instagram.com" not in lowered:
            continue
        if seed_url in seen:
            continue
        seen.add(seed_url)
        normalized.append(seed_url)
    return normalized


def _extract_profile_reference(profile_url: str) -> str | None:
    """Convertit une URL Instagram en reference compatible avec l'acteur Apify."""
    normalized = str(profile_url or "").strip().rstrip("/")
    if not normalized:
        return None
    match = re.search(r"instagram\.com/([^/?#]+)/?$", normalized, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip() or None
    return normalized


def _is_instagram_post_url(url: str) -> bool:
    """Valide les URLs de posts/reels acceptées par l'acteur commentaires."""
    return bool(_INSTAGRAM_POST_URL_RE.match(str(url or "").strip()))


def _resolve_seed_urls(
    *,
    client_id: str,
    watchlist_id: str | None,
    seed_urls: list[str] | None,
) -> list[str]:
    resolved_seed_urls = _normalize_seed_urls(seed_urls)
    if resolved_seed_urls or not watchlist_id:
        return resolved_seed_urls

    watchlist = get_watchlist(watchlist_id)
    if not watchlist:
        raise ValueError(f"watchlist not found: {watchlist_id}")
    if watchlist.get("client_id") != client_id:
        raise ValueError(f"watchlist tenant mismatch for {watchlist_id}")

    filters = watchlist.get("filters") or {}
    return _normalize_seed_urls(filters.get("seed_urls") or [])


def _clean_text(text: str) -> str | None:
    normalized = str(text or "").strip()
    if len(normalized) < 3:
        return None
    normalized = re.sub(r"http\S+|www\.\S+", "", normalized)
    normalized = re.sub(r"@\w+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized if len(normalized) >= 3 else None


def _document_id(*, author: str, text: str) -> str:
    stable_value = "|".join((text, author))
    return hashlib.md5(stable_value.encode("utf-8")).hexdigest()


def _discover_post_urls(apify_client, profile_url: str, max_posts: int) -> list[str]:
    profile_reference = _extract_profile_reference(profile_url)
    if not profile_reference:
        return []
    try:
        run = apify_client.actor(APIFY_IG_POSTS).call(
            run_input={
                "username": [profile_reference],
                "resultsLimit": max_posts,
                "dataDetailLevel": "basicData",
            },
            timeout_secs=300,
        )
    except Exception as exc:  # pragma: no cover - network failures are mocked in tests
        logger.warning("Instagram post discovery failed for %s: %s", profile_url, exc)
        return []

    post_urls: list[str] = []
    for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
        post_url = str(item.get("url") or "").strip()
        short_code = str(item.get("shortCode") or "").strip()
        if not post_url and short_code:
            post_url = f"https://www.instagram.com/p/{short_code}/"
        if _is_instagram_post_url(post_url):
            post_urls.append(post_url)
    return post_urls


def _collect_post_items(
    apify_client,
    *,
    post_url: str,
    max_comments_per_post: int,
    max_retries: int,
    delay_between_calls: float,
) -> list[dict]:
    run = None
    run_input = {
        "directUrls": [post_url],
        "resultsLimit": max_comments_per_post,
    }
    for attempt in range(1, max_retries + 1):
        try:
            run = apify_client.actor(APIFY_IG_COMMENTS).call(
                run_input=run_input,
                timeout_secs=300,
            )
            break
        except Exception as exc:  # pragma: no cover - network failures are mocked in tests
            logger.warning("Instagram comment collection failed for %s: %s", post_url, exc)
            if attempt < max_retries:
                time.sleep(delay_between_calls * attempt)

    if run is None:
        return []

    return list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())


def _item_to_document(item: dict, *, post_url: str) -> dict[str, object] | None:
    raw_text = _clean_text(item.get("text") or "")
    if not raw_text:
        return None

    author = str(item.get("ownerUsername") or "").strip()
    source_url = post_url
    collected_at = datetime.now(timezone.utc).isoformat()
    return {
        "external_document_id": _document_id(
            author=author,
            text=raw_text,
        ),
        "raw_text": raw_text,
        "source_url": source_url,
        "raw_payload": item,
        "raw_metadata": {
            "channel": "instagram",
            "post_url": post_url,
            "author": author,
            "date": str(item.get("timestamp") or ""),
            "likes": int(item.get("likesCount") or 0),
            "replies_count": int(item.get("repliesCount") or 0),
            "comment_url": "",
            "is_reply": bool(item.get("replyToId")),
            "collected_at": collected_at,
        },
    }


def collect_instagram_comments_apify(
    *,
    client_id: str,
    watchlist_id: str | None = None,
    seed_urls: list[str] | None = None,
    max_posts: int = 20,
    max_comments_per_post: int = 200,
    max_retries: int = 3,
    delay_between_calls: float = 2.0,
) -> list[dict[str, object]] | dict[str, object]:
    """Collect Instagram comments for watch runs, or skip cleanly when unavailable."""
    apify_token = _resolve_apify_token()
    if not apify_token:
        return {"status": "skipped", "documents": [], "reason": "missing_api_key"}
    if ApifyClient is None:
        return {"status": "skipped", "documents": [], "reason": "missing_dependency"}

    resolved_seed_urls = _resolve_seed_urls(
        client_id=client_id,
        watchlist_id=watchlist_id,
        seed_urls=seed_urls,
    )
    if not resolved_seed_urls:
        return {"status": "skipped", "documents": [], "reason": "no_seed_urls"}

    apify_client = ApifyClient(apify_token)
    documents: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for profile_url in resolved_seed_urls:
        post_urls = _discover_post_urls(apify_client, profile_url, max_posts)
        if not post_urls:
            logger.info("No public Instagram posts discovered for %s", profile_url)
            continue
        for post_index, post_url in enumerate(post_urls):
            raw_items = _collect_post_items(
                apify_client,
                post_url=post_url,
                max_comments_per_post=max_comments_per_post,
                max_retries=max_retries,
                delay_between_calls=delay_between_calls,
            )
            for item in raw_items:
                document = _item_to_document(item, post_url=post_url)
                if not document:
                    continue
                external_document_id = str(document["external_document_id"])
                if external_document_id in seen_ids:
                    continue
                seen_ids.add(external_document_id)
                documents.append(document)
            if post_index < len(post_urls) - 1 and delay_between_calls > 0:
                time.sleep(delay_between_calls)
    if not documents:
        return {"status": "skipped", "documents": [], "reason": "no_public_posts"}
    return documents
