"""Gestion CRUD des clients RamyPulse."""

from __future__ import annotations

import importlib
import re
import sqlite3
import uuid
from datetime import datetime

import config
from core.database import DatabaseManager, _seed_default_alert_rules
from core.runtime.runtime_settings_manager import get_runtime_setting, set_runtime_setting

ACTIVE_CLIENT_SETTING_KEY = "active_client_id"

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _config_module():
    """Retourne le module config courant, même après reload dans les tests."""
    return importlib.import_module("config")


def _get_connection() -> sqlite3.Connection:
    """Ouvre une connexion SQLite courte duree avec row_factory."""
    cfg = _config_module()
    connection = sqlite3.connect(str(getattr(cfg, "SQLITE_DB_PATH", config.SQLITE_DB_PATH)))
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_schema() -> None:
    """Garantit que le schema plateforme est initialise."""
    cfg = _config_module()
    DatabaseManager(str(getattr(cfg, "SQLITE_DB_PATH", config.SQLITE_DB_PATH))).create_tables()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, object] | None:
    """Convertit une ligne SQLite en dictionnaire exploitable."""
    if row is None:
        return None
    return dict(row)


def _slugify(client_name: str) -> str:
    """Construit un identifiant lisible a partir du nom client."""
    slug = _SLUG_PATTERN.sub("-", client_name.strip().lower()).strip("-")
    return slug or f"client-{uuid.uuid4().hex[:8]}"


def _unique_client_id(connection: sqlite3.Connection, base_client_id: str) -> str:
    """Derive un identifiant client unique a partir d'une base slugifiee."""
    candidate = base_client_id
    suffix = 2
    while connection.execute(
        "SELECT 1 FROM clients WHERE client_id = ?",
        (candidate,),
    ).fetchone() is not None:
        candidate = f"{base_client_id}-{suffix}"
        suffix += 1
    return candidate


def list_clients() -> list[dict[str, object]]:
    """Retourne la liste des clients enregistrés."""
    _ensure_schema()
    with _get_connection() as connection:
        rows = connection.execute(
            """
            SELECT client_id, client_name, industry, created_at, updated_at
            FROM clients
            ORDER BY created_at ASC, client_name ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_client(client_id: str) -> dict[str, object] | None:
    """Retourne un client par identifiant ou None s'il est absent."""
    _ensure_schema()
    with _get_connection() as connection:
        row = connection.execute(
            """
            SELECT client_id, client_name, industry, created_at, updated_at
            FROM clients
            WHERE client_id = ?
            """,
            (client_id,),
        ).fetchone()
    return _row_to_dict(row)


def create_client(
    client_name: str,
    industry: str | None = None,
    client_id: str | None = None,
) -> dict[str, object]:
    """Crée un nouveau client et retourne sa ligne complète."""
    normalized_name = client_name.strip()
    if not normalized_name:
        raise ValueError("client_name est obligatoire")

    _ensure_schema()
    now = datetime.now().isoformat()
    with _get_connection() as connection:
        base_client_id = client_id.strip() if client_id and client_id.strip() else _slugify(normalized_name)
        resolved_client_id = _unique_client_id(connection, base_client_id)
        connection.execute(
            """
            INSERT INTO clients (
                client_id,
                client_name,
                industry,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                resolved_client_id,
                normalized_name,
                industry.strip() if isinstance(industry, str) and industry.strip() else None,
                now,
                now,
            ),
        )
        _seed_default_alert_rules(connection, resolved_client_id)
        connection.commit()
    client = get_client(resolved_client_id)
    if client is None:
        raise RuntimeError(f"Client introuvable apres creation: {resolved_client_id}")
    return client


def get_or_create_client(
    client_id: str | None = None,
    client_name: str | None = None,
    industry: str | None = None,
) -> dict[str, object]:
    """Retourne un client existant ou en cree un nouveau."""
    if client_id:
        client = get_client(client_id)
        if client is not None:
            return client
        return create_client(
            client_name=client_name or client_id,
            industry=industry,
            client_id=client_id,
        )

    if client_name is None:
        raise ValueError("client_name est obligatoire quand client_id est absent")
    return create_client(client_name=client_name, industry=industry)


def set_active_client(client_id: str) -> dict[str, object]:
    """Enregistre le client actif runtime et retourne sa ligne."""
    client = get_client(client_id)
    if client is None:
        raise KeyError(client_id)
    set_runtime_setting(ACTIVE_CLIENT_SETTING_KEY, client_id)
    return client


def get_active_client() -> dict[str, object]:
    """Retourne le client actif courant, avec fallback technique."""
    resolved_client_id = resolve_active_client_id()
    client = get_client(resolved_client_id)
    if client is not None:
        return client
    cfg = _config_module()
    safe_expo_client_id = getattr(cfg, "SAFE_EXPO_CLIENT_ID", config.SAFE_EXPO_CLIENT_ID)
    if resolved_client_id == safe_expo_client_id:
        return create_client(
            client_name="Safe Expo",
            client_id=resolved_client_id,
        )
    raise KeyError(resolved_client_id)


def resolve_active_client_id() -> str:
    """Retourne l'identifiant du client actif selon le runtime et le fallback expo."""
    runtime_client_id = get_runtime_setting(ACTIVE_CLIENT_SETTING_KEY)
    if isinstance(runtime_client_id, str) and runtime_client_id.strip():
        return runtime_client_id.strip()
    cfg = _config_module()
    return getattr(cfg, "SAFE_EXPO_CLIENT_ID", config.SAFE_EXPO_CLIENT_ID)
