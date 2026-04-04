"""Tests unitaires purs pour l'identite canonique multi-sources."""

from __future__ import annotations

from core.database import DatabaseManager
from core.ingestion.content_identity import resolve_or_create_content_item


def test_resolve_or_create_content_item_reuses_existing_content_item() -> None:
    """Deux resolutions du meme contenu logique doivent partager un seul content_item."""
    db = DatabaseManager(":memory:")
    db.create_tables()

    kwargs = {
        "client_id": "ramy_client_001",
        "platform": "facebook",
        "external_content_id": "fb-post-123",
        "canonical_url": "https://facebook.com/posts/fb-post-123",
        "owner_type": "owned",
        "coverage_key": "owned:facebook:ramy-official",
        "checksum_sha256": "sha-123",
        "fallback_id": "raw-123",
    }

    first_id, first_key, first_url = resolve_or_create_content_item(db.connection, **kwargs)
    second_id, second_key, second_url = resolve_or_create_content_item(db.connection, **kwargs)

    rows = db.connection.execute(
        """
        SELECT content_item_id, canonical_key, canonical_url
        FROM content_items
        WHERE client_id = ?
        """,
        ("ramy_client_001",),
    ).fetchall()

    assert first_id == second_id
    assert first_key == second_key == "facebook:fb-post-123"
    assert first_url == second_url == "https://facebook.com/posts/fb-post-123"
    assert len(rows) == 1
    assert rows[0]["content_item_id"] == first_id
    assert rows[0]["canonical_key"] == "facebook:fb-post-123"
    assert rows[0]["canonical_url"] == "https://facebook.com/posts/fb-post-123"

    db.close()
