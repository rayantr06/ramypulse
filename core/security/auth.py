"""FastAPI auth dependency — API key verification."""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import sqlite3
import uuid
from datetime import datetime
from typing import NamedTuple

from fastapi import Header, HTTPException

import config

logger = logging.getLogger(__name__)

KEY_PREFIX = "rpk_"


class AuthContext(NamedTuple):
    """Resolved identity from a valid API key."""

    client_id: str
    key_id: str
    scopes: list[str]


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def hash_key(raw_key: str) -> str:
    """SHA-256 hash of a raw API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_raw_key() -> str:
    """Generate a new raw API key: rpk_ + 32 hex chars."""
    return f"{KEY_PREFIX}{secrets.token_hex(16)}"


def get_current_client(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> AuthContext:
    """FastAPI dependency. Validates the API key and returns the auth context.

    Raises HTTPException 401 if the key is missing, invalid, or inactive.
    """
    key_hash = hash_key(x_api_key)
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT key_id, client_id, scopes
            FROM api_keys
            WHERE key_hash = ? AND is_active = 1
            """,
            (key_hash,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
            )

        conn.execute(
            "UPDATE api_keys SET last_used_at = ? WHERE key_id = ?",
            (datetime.now().isoformat(), row["key_id"]),
        )
        conn.commit()

    scopes = json.loads(row["scopes"]) if row["scopes"] else ["*"]
    return AuthContext(
        client_id=row["client_id"],
        key_id=row["key_id"],
        scopes=scopes,
    )


def create_api_key(
    client_id: str,
    label: str | None = None,
) -> tuple[str, str]:
    """Create a new API key in the database.

    Returns (key_id, raw_key). The raw key is never stored.
    """
    raw_key = generate_raw_key()
    key_id = f"key-{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO api_keys (
                key_id, client_id, key_hash, key_prefix, label,
                scopes, is_active, created_at, last_used_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, NULL)
            """,
            (
                key_id,
                client_id,
                hash_key(raw_key),
                raw_key[:12],
                label or "",
                '["*"]',
                now,
            ),
        )
        conn.commit()

    return key_id, raw_key


def list_api_keys(client_id: str | None = None) -> list[dict]:
    """List API keys (never exposes hash or raw key)."""
    with _get_connection() as conn:
        if client_id:
            rows = conn.execute(
                """
                SELECT key_id, client_id, key_prefix, label, is_active,
                       created_at, last_used_at
                FROM api_keys WHERE client_id = ?
                ORDER BY created_at DESC
                """,
                (client_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT key_id, client_id, key_prefix, label, is_active,
                       created_at, last_used_at
                FROM api_keys
                ORDER BY created_at DESC
                """
            ).fetchall()
    return [dict(row) for row in rows]


def deactivate_api_key(key_id: str) -> bool:
    """Soft-delete an API key by setting is_active = 0."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "UPDATE api_keys SET is_active = 0 WHERE key_id = ?",
            (key_id,),
        )
        conn.commit()
    return cursor.rowcount > 0
