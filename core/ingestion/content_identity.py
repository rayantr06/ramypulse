"""Helpers d'identité canonique pour le contenu multi-sources."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


VALID_SOURCE_PURPOSES = frozenset(
    {
        "owned_content",
        "campaign_engagement",
        "market_monitoring",
        "competitor_monitoring",
        "manual_evidence",
        "bulk_import",
    }
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def parse_json_object(value: object) -> dict:
    """Retourne un dictionnaire JSON ou {}."""
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(payload, dict):
            return payload
    return {}


def infer_source_purpose(
    *,
    platform: str | None,
    source_type: str | None,
    owner_type: str | None,
    explicit: str | None = None,
) -> str:
    """Déduit un usage métier si le payload n'en fournit pas explicitement."""
    if explicit in VALID_SOURCE_PURPOSES:
        return explicit

    normalized_platform = (platform or "").strip().lower()
    normalized_type = (source_type or "").strip().lower()
    normalized_owner = (owner_type or "").strip().lower()

    if normalized_platform == "import" or normalized_type == "batch_import":
        return "bulk_import"
    if normalized_owner == "competitor":
        return "competitor_monitoring"
    if normalized_owner == "market":
        return "market_monitoring"
    return "owned_content"


def default_source_priority(source_purpose: str) -> int:
    """Retourne la priorité par défaut d'une source."""
    mapping = {
        "owned_content": 1,
        "campaign_engagement": 1,
        "manual_evidence": 2,
        "market_monitoring": 3,
        "competitor_monitoring": 3,
        "bulk_import": 4,
    }
    return mapping.get(source_purpose, 3)


def default_coverage_key(source_id: str, platform: str | None) -> str:
    """Fabrique une coverage_key conservatrice quand rien n'est fourni."""
    normalized_platform = (platform or "unknown").strip().lower() or "unknown"
    return f"legacy:{normalized_platform}:{source_id}"


def normalize_canonical_url(value: str | None) -> str | None:
    """Normalise légèrement une URL pour la clé canonique."""
    if value in (None, ""):
        return None
    raw = str(value).strip()
    if not raw:
        return None

    try:
        parsed = urlsplit(raw)
    except ValueError:
        return raw

    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    normalized = urlunsplit((scheme, netloc, path, parsed.query, ""))
    return normalized or raw


def extract_canonical_url(
    *,
    raw_payload: object = None,
    raw_metadata: object = None,
    explicit_url: str | None = None,
) -> str | None:
    """Extrait une URL canonique depuis les payloads connus."""
    if explicit_url:
        return normalize_canonical_url(explicit_url)

    payload = parse_json_object(raw_payload)
    metadata = parse_json_object(raw_metadata)
    for candidate in (
        metadata.get("source_url"),
        metadata.get("post_url"),
        metadata.get("url"),
        payload.get("source_url"),
        payload.get("post_url"),
        payload.get("url"),
    ):
        normalized = normalize_canonical_url(candidate)
        if normalized:
            return normalized
    return None


def build_canonical_key(
    *,
    platform: str | None,
    external_content_id: str | None,
    canonical_url: str | None,
    checksum_sha256: str | None,
    fallback_id: str,
) -> str:
    """Construit la clé canonique d'un contenu."""
    normalized_platform = (platform or "unknown").strip().lower() or "unknown"
    if external_content_id:
        return f"{normalized_platform}:{external_content_id}"
    if canonical_url:
        return f"url:{canonical_url}"
    if checksum_sha256:
        return f"sha256:{checksum_sha256}"
    return f"raw:{fallback_id}"


def resolve_or_create_content_item(
    connection: sqlite3.Connection,
    *,
    client_id: str,
    platform: str | None,
    external_content_id: str | None,
    canonical_url: str | None,
    owner_type: str | None,
    coverage_key: str | None,
    checksum_sha256: str | None,
    fallback_id: str,
) -> tuple[str, str, str | None]:
    """Résout ou crée le content_item canonique pour un contenu observé."""
    canonical_key = build_canonical_key(
        platform=platform,
        external_content_id=external_content_id,
        canonical_url=canonical_url,
        checksum_sha256=checksum_sha256,
        fallback_id=fallback_id,
    )

    row = connection.execute(
        """
        SELECT content_item_id
        FROM content_items
        WHERE client_id = ? AND canonical_key = ?
        """,
        (client_id, canonical_key),
    ).fetchone()
    if row:
        return row["content_item_id"], canonical_key, canonical_url

    content_item_id = _new_id("cnt")
    now = _now()
    connection.execute(
        """
        INSERT INTO content_items (
            content_item_id, client_id, platform, external_content_id,
            canonical_url, canonical_key, owner_type, coverage_key,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            content_item_id,
            client_id,
            (platform or "unknown").strip().lower() or "unknown",
            external_content_id,
            canonical_url,
            canonical_key,
            owner_type,
            coverage_key,
            now,
            now,
        ),
    )
    return content_item_id, canonical_key, canonical_url
