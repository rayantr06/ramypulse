"""Gestion des parametres runtime persistes dans SQLite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

import config
from core.database import DatabaseManager

_SETTINGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runtime_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""


def _get_connection() -> sqlite3.Connection:
    """Ouvre une connexion SQLite courte duree avec row_factory."""
    connection = sqlite3.connect(str(config.SQLITE_DB_PATH))
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_runtime_settings_table(connection: sqlite3.Connection) -> None:
    """Garantit la presence de la table des parametres runtime."""
    connection.execute(_SETTINGS_TABLE_SQL)
    connection.commit()


def _encode_value(value: object) -> str:
    """Convertit une valeur Python en texte stockable."""
    return json.dumps(value, ensure_ascii=False)


def _decode_value(value: str | None) -> object | None:
    """Reconstitue une valeur Python depuis le stockage texte."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def get_runtime_setting(setting_key: str, default: object | None = None) -> object | None:
    """Retourne la valeur runtime associee a une cle, ou une valeur par defaut."""
    DatabaseManager().create_tables()
    with _get_connection() as connection:
        _ensure_runtime_settings_table(connection)
        row = connection.execute(
            "SELECT setting_value FROM runtime_settings WHERE setting_key = ?",
            (setting_key,),
        ).fetchone()
    if row is None:
        return default
    return _decode_value(row["setting_value"])


def set_runtime_setting(setting_key: str, value: object) -> object:
    """Ecrit ou remplace une valeur runtime et la retourne."""
    DatabaseManager().create_tables()
    serialized = _encode_value(value)
    now = datetime.now().isoformat()
    with _get_connection() as connection:
        _ensure_runtime_settings_table(connection)
        connection.execute(
            """
            INSERT INTO runtime_settings (setting_key, setting_value, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = excluded.updated_at
            """,
            (setting_key, serialized, now, now),
        )
        connection.commit()
    return value
