"""Collector for YouTube search results and top comments."""

from __future__ import annotations

from typing import Iterable

import config

try:
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover - exercised when dependency is unavailable
    build = None

from core.watchlists.watchlist_manager import get_watchlist


def _normalize_keywords(keywords: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_keyword in keywords or []:
        keyword = str(raw_keyword or "").strip().lower()
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        normalized.append(keyword)
    return normalized


def _resolve_keywords(
    *,
    client_id: str,
    watchlist_id: str | None,
    keywords: list[str] | None,
) -> list[str]:
    resolved_keywords = _normalize_keywords(keywords)
    if resolved_keywords or not watchlist_id:
        return resolved_keywords

    watchlist = get_watchlist(watchlist_id)
    if not watchlist:
        raise ValueError(f"watchlist not found: {watchlist_id}")
    if watchlist.get("client_id") != client_id:
        raise ValueError(f"watchlist tenant mismatch for {watchlist_id}")

    filters = watchlist.get("filters") or {}
    semantic_keywords = list(filters.get("keywords") or [])
    for field_name in ("brand_name", "product_name"):
        candidate = str(filters.get(field_name) or "").strip()
        if candidate:
            semantic_keywords.append(candidate)
    return _normalize_keywords(semantic_keywords)


def collect_youtube_search_results(
    *,
    client_id: str,
    watchlist_id: str | None = None,
    keywords: list[str] | None = None,
    max_videos: int = 5,
    max_comments: int = 10,
) -> list[dict[str, object]] | dict[str, object]:
    """Collect top-level YouTube comments for search hits."""
    resolved_keywords = _resolve_keywords(
        client_id=client_id,
        watchlist_id=watchlist_id,
        keywords=keywords,
    )
    if not resolved_keywords:
        return {"status": "skipped", "documents": [], "reason": "missing_keywords"}
    if not config.YOUTUBE_API_KEY:
        return {"status": "skipped", "documents": [], "reason": "missing_api_key"}
    if build is None:
        return {"status": "skipped", "documents": [], "reason": "missing_dependency"}

    query = " OR ".join(resolved_keywords)
    service = build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY, cache_discovery=False)
    search_response = service.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_videos,
    ).execute()

    documents: list[dict[str, object]] = []
    for item in search_response.get("items", []):
        video_id = str(item.get("id", {}).get("videoId") or "").strip()
        if not video_id:
            continue
        comments_response = service.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_comments,
            order="relevance",
        ).execute()
        for index, comment in enumerate(comments_response.get("items", [])):
            snippet = (
                comment.get("snippet", {})
                .get("topLevelComment", {})
                .get("snippet", {})
            )
            text = str(snippet.get("textDisplay") or "").strip()
            if not text:
                continue
            source_url = f"https://www.youtube.com/watch?v={video_id}"
            documents.append(
                {
                    "external_document_id": f"{video_id}:{index}",
                    "raw_text": text,
                    "source_url": source_url,
                    "raw_payload": {
                        **comment,
                        "keywords": resolved_keywords,
                        "watchlist_id": watchlist_id,
                    },
                    "raw_metadata": {
                        "channel": "youtube",
                        "video_id": video_id,
                        "keywords": resolved_keywords,
                        "source_url": source_url,
                    },
                }
            )
    return documents
