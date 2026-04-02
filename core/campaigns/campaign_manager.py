"""Gestionnaire CRUD des campagnes marketing RamyPulse.

Utilise SQLite directement via le pattern _get_connection() défini dans INTERFACES.md.
Chaque fonction ouvre et ferme sa propre connexion.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from uuid import uuid4

from config import DEFAULT_CLIENT_ID, SQLITE_DB_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schéma SQLite — synchronisé avec INTERFACES.md Section 2
# ---------------------------------------------------------------------------

_DDL_CAMPAIGNS = """
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id       TEXT PRIMARY KEY,
    client_id         TEXT NOT NULL DEFAULT 'ramy_client_001',
    campaign_name     TEXT NOT NULL,
    campaign_type     TEXT,
    platform          TEXT,
    description       TEXT,
    influencer_handle TEXT,
    influencer_tier   TEXT,
    target_segment    TEXT,
    target_aspects    TEXT,
    target_regions    TEXT,
    keywords          TEXT,
    budget_dza        INTEGER,
    start_date        TEXT,
    end_date          TEXT,
    pre_window_days   INTEGER DEFAULT 14,
    post_window_days  INTEGER DEFAULT 14,
    status            TEXT DEFAULT 'planned',
    created_at        TEXT,
    updated_at        TEXT
)
"""

_JSON_FIELDS = ("target_aspects", "target_regions", "keywords")
_VALID_STATUSES = frozenset({"planned", "active", "completed", "cancelled"})


# ---------------------------------------------------------------------------
# Utilitaires privés
# ---------------------------------------------------------------------------


def _get_connection() -> sqlite3.Connection:
    """Ouvre une connexion SQLite et s'assure que la table existe."""
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(_DDL_CAMPAIGNS)
    conn.commit()
    return conn


def _serialize_list(value: list | None) -> str:
    """Sérialise une liste Python en JSON string pour SQLite."""
    return json.dumps(value or [], ensure_ascii=False)


def _deserialize_list(value: str | None) -> list:
    """Désérialise une JSON string en liste Python."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _new_id() -> str:
    """Génère un UUID string."""
    return str(uuid4())


def _now() -> str:
    """Retourne le timestamp ISO courant."""
    return datetime.now().isoformat()


def _row_to_dict(row) -> dict | None:
    """Convertit une sqlite3.Row en dict avec les champs JSON désérialisés."""
    if row is None:
        return None
    d = dict(row)
    for field in _JSON_FIELDS:
        if field in d:
            d[field] = _deserialize_list(d[field])
    return d


# ---------------------------------------------------------------------------
# CRUD public
# ---------------------------------------------------------------------------


def create_campaign(campaign_data: dict) -> str:
    """Insère une campagne. Returns campaign_id (UUID str)."""
    campaign_id = _new_id()
    now = _now()
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO campaigns (
                campaign_id, client_id, campaign_name, campaign_type, platform,
                description, influencer_handle, influencer_tier, target_segment,
                target_aspects, target_regions, keywords, budget_dza,
                start_date, end_date, pre_window_days, post_window_days,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                campaign_data.get("client_id", DEFAULT_CLIENT_ID),
                campaign_data["campaign_name"],
                campaign_data.get("campaign_type"),
                campaign_data.get("platform"),
                campaign_data.get("description"),
                campaign_data.get("influencer_handle"),
                campaign_data.get("influencer_tier"),
                campaign_data.get("target_segment"),
                _serialize_list(campaign_data.get("target_aspects")),
                _serialize_list(campaign_data.get("target_regions")),
                _serialize_list(campaign_data.get("keywords")),
                campaign_data.get("budget_dza"),
                campaign_data.get("start_date"),
                campaign_data.get("end_date"),
                campaign_data.get("pre_window_days", 14),
                campaign_data.get("post_window_days", 14),
                campaign_data.get("status", "planned"),
                now,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    logger.debug("Campagne créée : %s (id=%s)", campaign_data.get("campaign_name"), campaign_id)
    return campaign_id


def get_campaign(campaign_id: str) -> dict | None:
    """Returns dict avec tous les champs, listes JSON désérialisées en list."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM campaigns WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def list_campaigns(
    status: str | None = None,
    platform: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Returns liste de campagnes. Champs JSON désérialisés automatiquement."""
    conditions: list[str] = []
    params: list = []
    if status is not None:
        conditions.append("status = ?")
        params.append(status)
    if platform is not None:
        conditions.append("platform = ?")
        params.append(platform)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT * FROM campaigns {where} ORDER BY created_at DESC LIMIT ?",
            tuple(params),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(row) for row in rows]


def update_campaign_status(campaign_id: str, status: str) -> bool:
    """Met à jour le statut d'une campagne. Status valides : planned, active, completed, cancelled."""
    if status not in _VALID_STATUSES:
        return False
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "UPDATE campaigns SET status = ?, updated_at = ? WHERE campaign_id = ?",
            (status, _now(), campaign_id),
        )
        conn.commit()
        updated = cursor.rowcount > 0
    finally:
        conn.close()
    return updated


def delete_campaign(campaign_id: str) -> bool:
    """Supprime définitivement une campagne."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM campaigns WHERE campaign_id = ?",
            (campaign_id,),
        )
        conn.commit()
        deleted = cursor.rowcount > 0
    finally:
        conn.close()
    return deleted
