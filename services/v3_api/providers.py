"""Adaptateurs V1 : YouTube officiel et Apify pilote.

Les acteurs Apify restent des details de configuration. Le domaine ne connait
que ``PublicSourceConnector`` et peut donc changer de fournisseur sans migration.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import AsyncIterator, Callable
from typing import Any

from services.v3_api.connectors import (
    CollectedDocument,
    CollectionCheckpoint,
    CollectionCost,
    DiscoveryTarget,
    PublicSourceConnector,
)


def _first_text(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


class ApifyPublicConnector(PublicSourceConnector):
    provider = "apify"

    def __init__(
        self,
        *,
        platform: str,
        actor_id: str,
        token: str,
        input_builder: Callable[[DiscoveryTarget], dict[str, object]],
    ) -> None:
        if platform not in {"facebook", "tiktok", "google_maps"}:
            raise ValueError("plateforme Apify V1 non supportee")
        self.platform = platform
        self.actor_id = actor_id
        self._token = token
        self._input_builder = input_builder
        self._checkpoint = CollectionCheckpoint(None, 0, 0)
        self._cost = CollectionCost("apify", 0, 0, 0, "usageUsd x APIFY_USD_DZD_RATE")

    async def discover(self, query: str, *, limit: int) -> list[DiscoveryTarget]:
        del limit
        query = query.strip()
        if not query:
            return []
        external_id = hashlib.sha256(f"{self.platform}:{query}".encode()).hexdigest()[:20]
        return [DiscoveryTarget(external_id=external_id, canonical_url=query, label=query)]

    async def collect(
        self,
        target: DiscoveryTarget,
        *,
        checkpoint: CollectionCheckpoint | None,
    ) -> AsyncIterator[CollectedDocument]:
        del checkpoint
        try:
            from apify_client import ApifyClient
        except ImportError as exc:  # pragma: no cover - dependance d'exploitation
            raise RuntimeError("apify-client est requis pour ce connecteur") from exc

        client = ApifyClient(self._token)
        run = await asyncio.to_thread(
            client.actor(self.actor_id).call,
            run_input=self._input_builder(target),
        )
        dataset_id = str(run.get("defaultDatasetId") or "")
        items = await asyncio.to_thread(lambda: list(client.dataset(dataset_id).iterate_items()))
        count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            text = _first_text(item, "text", "comment", "reviewText", "caption", "content")
            if not text:
                continue
            count += 1
            external_id = _first_text(item, "id", "commentId", "reviewId") or hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest()
            url = _first_text(item, "url", "postUrl", "reviewUrl", "placeUrl") or target.canonical_url
            published_at = _first_text(item, "timestamp", "publishedAtDate", "date", "createdAt")
            yield CollectedDocument(external_id, url, text, published_at, item)

        rate = float(os.getenv("APIFY_USD_DZD_RATE", "135"))
        usage_usd = float(run.get("usageTotalUsd") or 0)
        self._checkpoint = CollectionCheckpoint(dataset_id or None, count, round(usage_usd * rate, 2))
        self._cost = CollectionCost("apify", count, 1, round(usage_usd * rate, 2), f"{usage_usd:.4f} USD x {rate}")

    def normalize(self, document: CollectedDocument) -> dict[str, object]:
        return {
            "external_id": document.external_id,
            "canonical_url": document.canonical_url,
            "text": document.content,
            "source": self.platform,
            "source_url": document.canonical_url,
            "published_at": document.published_at,
            "raw_metadata": dict(document.metadata),
        }

    def checkpoint(self) -> CollectionCheckpoint:
        return self._checkpoint

    def report_cost(self) -> CollectionCost:
        return self._cost


class YouTubeOfficialConnector(PublicSourceConnector):
    provider = "youtube_data_api_v3"
    platform = "youtube"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._checkpoint = CollectionCheckpoint(None, 0, 0)
        self._cost = CollectionCost(self.provider, 0, 0, 0, "quota API; cout monetaire non fourni")

    async def discover(self, query: str, *, limit: int) -> list[DiscoveryTarget]:
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("google-api-python-client est requis") from exc

        def execute() -> dict[str, Any]:
            client = build("youtube", "v3", developerKey=self._api_key, cache_discovery=False)
            return client.search().list(part="snippet", q=query, type="video", maxResults=min(limit, 50)).execute()

        response = await asyncio.to_thread(execute)
        return [
            DiscoveryTarget(
                external_id=str(item["id"]["videoId"]),
                canonical_url=f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                label=str(item["snippet"]["title"]),
            )
            for item in response.get("items", [])
        ]

    async def collect(
        self,
        target: DiscoveryTarget,
        *,
        checkpoint: CollectionCheckpoint | None,
    ) -> AsyncIterator[CollectedDocument]:
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("google-api-python-client est requis") from exc

        page_token = checkpoint.cursor if checkpoint else None
        count = 0
        requests = 0
        while True:
            def execute() -> dict[str, Any]:
                client = build("youtube", "v3", developerKey=self._api_key, cache_discovery=False)
                return client.commentThreads().list(
                    part="snippet", videoId=target.external_id, maxResults=100,
                    pageToken=page_token, textFormat="plainText",
                ).execute()

            response = await asyncio.to_thread(execute)
            requests += 1
            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                count += 1
                yield CollectedDocument(
                    external_id=str(item["id"]),
                    canonical_url=target.canonical_url,
                    content=str(snippet["textDisplay"]),
                    published_at=str(snippet["publishedAt"]),
                    metadata={"like_count": snippet.get("likeCount", 0), "video_id": target.external_id},
                )
            page_token = response.get("nextPageToken")
            self._checkpoint = CollectionCheckpoint(page_token, count, 0)
            if not page_token:
                break
        self._cost = CollectionCost(self.provider, count, requests, 0, "quota API; cout monetaire non fourni")

    def normalize(self, document: CollectedDocument) -> dict[str, object]:
        return {
            "external_id": document.external_id,
            "canonical_url": document.canonical_url,
            "text": document.content,
            "source": "youtube",
            "source_url": document.canonical_url,
            "published_at": document.published_at,
            "raw_metadata": dict(document.metadata),
        }

    def checkpoint(self) -> CollectionCheckpoint:
        return self._checkpoint

    def report_cost(self) -> CollectionCost:
        return self._cost


def build_pilot_connectors() -> dict[str, PublicSourceConnector]:
    token = os.getenv("APIFY_API_KEY", "")
    connectors: dict[str, PublicSourceConnector] = {}
    actor_ids = {
        "facebook": os.getenv("APIFY_FACEBOOK_ACTOR_ID", ""),
        "tiktok": os.getenv("APIFY_TIKTOK_ACTOR_ID", ""),
        "google_maps": os.getenv("APIFY_GOOGLE_MAPS_ACTOR_ID", ""),
    }
    for platform, actor_id in actor_ids.items():
        if token and actor_id:
            connectors[platform] = ApifyPublicConnector(
                platform=platform,
                actor_id=actor_id,
                token=token,
                input_builder=lambda target, selected=platform: {
                    "startUrls": [{"url": target.canonical_url}],
                    "searchQueries": [target.label],
                    "platform": selected,
                },
            )
    youtube_key = os.getenv("YOUTUBE_API_KEY", "")
    if youtube_key:
        connectors["youtube"] = YouTubeOfficialConnector(youtube_key)
    return connectors
