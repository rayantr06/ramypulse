"""Gestion des credentials plateforme pour les métriques d'engagement."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime

import config
from core.security.secret_manager import resolve_secret, store_secret

logger = logging.getLogger(__name__)


def _get_conn() -> sqlite3.Connection:
    """Retourne une connexion SQLite dédiée au module."""
    conn = sqlite3.connect(str(config.SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_credential(
    *,
    entity_type: str,
    entity_name: str,
    platform: str,
    account_id: str | None = None,
    access_token: str | None = None,
    app_id: str | None = None,
    app_secret: str | None = None,
    extra_config: dict | None = None,
    client_id: str = "ramy_client_001",
) -> str:
    """Crée un credential et stocke les secrets hors base."""
    credential_id = f"cred-{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()

    access_token_ref = store_secret(
        access_token,
        label=f"{platform}:{entity_name}:access_token",
    )
    app_secret_ref = store_secret(
        app_secret,
        label=f"{platform}:{entity_name}:app_secret",
    )

    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO platform_credentials (
                credential_id, client_id, entity_type, entity_name, platform,
                account_id, access_token_ref, app_id, app_secret_ref,
                extra_config, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                credential_id,
                client_id,
                entity_type,
                entity_name,
                platform,
                account_id,
                access_token_ref,
                app_id,
                app_secret_ref,
                json.dumps(extra_config or {}, ensure_ascii=False),
                now,
                now,
            ),
        )
        conn.commit()

    logger.info("Credential créé : %s (%s / %s)", credential_id, platform, entity_name)
    return credential_id


def list_credentials(
    platform: str | None = None,
    entity_type: str | None = None,
    is_active: bool = True,
    client_id: str = "ramy_client_001",
) -> list[dict]:
    """Liste les credentials sans exposer les secrets."""
    conditions = ["client_id = ?"]
    params: list[object] = [client_id]

    if is_active is not None:
        conditions.append("is_active = ?")
        params.append(1 if is_active else 0)
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    if entity_type:
        conditions.append("entity_type = ?")
        params.append(entity_type)

    where = " AND ".join(conditions)
    with _get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT credential_id, entity_type, entity_name, platform,
                   account_id, app_id, is_active, created_at, updated_at
            FROM platform_credentials
            WHERE {where}
            ORDER BY created_at DESC
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def get_credential(credential_id: str) -> dict | None:
    """Récupère un credential avec résolution des secrets."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM platform_credentials WHERE credential_id = ?",
            [credential_id],
        ).fetchone()
    if not row:
        return None

    record = dict(row)
    record["access_token"] = resolve_secret(record.pop("access_token_ref", None))
    record["app_secret"] = resolve_secret(record.pop("app_secret_ref", None))
    try:
        record["extra_config"] = json.loads(record.get("extra_config") or "{}")
    except (TypeError, ValueError):
        record["extra_config"] = {}
    return record


def deactivate_credential(credential_id: str) -> bool:
    """Désactive logiquement un credential."""
    now = datetime.now().isoformat()
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE platform_credentials
            SET is_active = 0, updated_at = ?
            WHERE credential_id = ?
            """,
            [now, credential_id],
        )
        conn.commit()
    return cursor.rowcount > 0


def update_credential_token(
    credential_id: str,
    *,
    new_access_token: str,
    extra_config_updates: dict | None = None,
) -> bool:
    """Update the access token (and optionally extra_config fields) for a credential.

    Returns True if the credential was found and updated, False otherwise.
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT extra_config FROM platform_credentials WHERE credential_id = ?",
            [credential_id],
        ).fetchone()
        if not row:
            return False

        # Store the new token via secret_manager
        new_token_ref = store_secret(
            new_access_token,
            label=f"refreshed_token:{credential_id}",
        )

        # Merge extra_config updates
        try:
            existing_extra = json.loads(row["extra_config"] or "{}")
        except (TypeError, ValueError):
            existing_extra = {}
        if extra_config_updates:
            existing_extra.update(extra_config_updates)

        now = datetime.now().isoformat()
        conn.execute(
            """
            UPDATE platform_credentials
            SET access_token_ref = ?, extra_config = ?, updated_at = ?
            WHERE credential_id = ?
            """,
            [new_token_ref, json.dumps(existing_extra, ensure_ascii=False), now, credential_id],
        )
        conn.commit()

    logger.info("Token updated for credential %s", credential_id)
    return True
