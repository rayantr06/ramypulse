"""HTTP client for Meta Graph API."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def meta_graph_get(
    endpoint: str,
    *,
    access_token: str,
    fields: str | None = None,
    params: dict[str, str] | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """Execute a GET request against the Meta Graph API."""
    query_params: dict[str, str] = {"access_token": access_token}
    if fields:
        query_params["fields"] = fields
    if params:
        query_params.update(params)

    url = f"{_GRAPH_API_BASE}/{endpoint}?{urllib.parse.urlencode(query_params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "RamyPulse/1.0"})

    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def meta_graph_paginate(
    endpoint: str,
    *,
    access_token: str,
    fields: str | None = None,
    max_pages: int = 20,
    timeout: int = 15,
) -> list[dict[str, Any]]:
    """Fetch all items from a paginated Meta Graph API endpoint."""
    all_items: list[dict[str, Any]] = []
    extra_params: dict[str, str] = {}

    for page_num in range(max_pages):
        response = meta_graph_get(
            endpoint,
            access_token=access_token,
            fields=fields,
            params=extra_params if extra_params else None,
            timeout=timeout,
        )
        items = response.get("data", [])
        if not items:
            break

        all_items.extend(items)

        paging = response.get("paging", {})
        if "next" not in paging:
            break
        after_cursor = paging.get("cursors", {}).get("after")
        if not after_cursor:
            break
        extra_params = {"after": after_cursor}

    logger.info("Fetched %d items in %d pages from %s", len(all_items), page_num + 1, endpoint)
    return all_items
