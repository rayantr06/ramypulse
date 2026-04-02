"""Gestionnaire SQLite pour les recommandations generees par l'agent AI.

CRUD complet sur la table `recommendations` selon le schema INTERFACES.md.
Utilise le pattern _get_connection() de la Section 7 (jamais DatabaseManager).
"""

import json
import logging
import sqlite3
import uuid
import importlib
from datetime import datetime

import config
from config import DEFAULT_CLIENT_ID, SQLITE_DB_PATH

logger = logging.getLogger(__name__)

_VALID_STATUSES = ("active", "archived", "dismissed")
_VALID_AUTO_TRIGGER_SEVERITIES = ("low", "medium", "high", "critical")

_DDL_CLIENT_AGENT_CONFIG = """
CREATE TABLE IF NOT EXISTS client_agent_config (
    config_id               TEXT PRIMARY KEY,
    client_id               TEXT NOT NULL UNIQUE DEFAULT 'ramy_client_001',
    provider                TEXT NOT NULL DEFAULT 'ollama_local',
    model                   TEXT,
    api_key_encrypted       TEXT,
    auto_trigger_on_alert   INTEGER NOT NULL DEFAULT 0,
    auto_trigger_severity   TEXT DEFAULT 'critical',
    weekly_report_enabled   INTEGER NOT NULL DEFAULT 0,
    weekly_report_day       INTEGER DEFAULT 1,
    created_at              TEXT NOT NULL,
    updated_at              TEXT NOT NULL
)
"""


def _config_module():
    """Retourne le module config courant, meme apres reload dans les tests."""
    return importlib.import_module("config")


# ---------------------------------------------------------------------------
# Helpers SQLite (Section 7 de INTERFACES.md)
# ---------------------------------------------------------------------------

def _get_connection(db_path=None) -> sqlite3.Connection:
    """Ouvre une connexion SQLite avec row_factory.

    Args:
        db_path: Chemin vers la base. None = utiliser SQLITE_DB_PATH.

    Returns:
        Connexion SQLite avec sqlite3.Row factory.
    """
    cfg = _config_module()
    resolved = str(db_path) if db_path else str(getattr(cfg, "SQLITE_DB_PATH", SQLITE_DB_PATH))
    conn = sqlite3.connect(resolved)
    conn.row_factory = sqlite3.Row
    return conn


def _serialize_list(value) -> str:
    """Serialise une liste en JSON string pour SQLite."""
    return json.dumps(value or [], ensure_ascii=False)


def _deserialize_list(value) -> list:
    """Deserialise une JSON string en liste."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _new_id() -> str:
    """Genere un UUID string."""
    return str(uuid.uuid4())


def _now() -> str:
    """Timestamp ISO courant."""
    return datetime.now().isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convertit un sqlite3.Row en dict avec deserialisation des champs JSON.

    Args:
        row: Ligne SQLite.

    Returns:
        Dict avec recommendations et watchlist_priorities sous forme de list.
    """
    d = dict(row)
    d["recommendations"] = _deserialize_list(d.get("recommendations"))
    d["watchlist_priorities"] = _deserialize_list(d.get("watchlist_priorities"))
    return d


def _ensure_client_agent_config_table(conn: sqlite3.Connection) -> None:
    """Garantit la presence de la table de configuration agent."""
    conn.execute(_DDL_CLIENT_AGENT_CONFIG)
    conn.commit()


def _default_agent_config_payload(client_id: str) -> tuple:
    """Construit la ligne de configuration par defaut pour un client."""
    cfg = _config_module()
    now = _now()
    return (
        f"cfg-{client_id}",
        client_id,
        getattr(cfg, "DEFAULT_AGENT_PROVIDER", "ollama_local"),
        getattr(cfg, "DEFAULT_AGENT_MODEL", "qwen2.5:14b"),
        None,
        0,
        "critical",
        0,
        1,
        now,
        now,
    )


def _ensure_client_agent_config_row(conn: sqlite3.Connection, client_id: str) -> None:
    """Insere une configuration par defaut si le client n'en a pas encore."""
    _ensure_client_agent_config_table(conn)
    conn.execute(
        """
        INSERT OR IGNORE INTO client_agent_config (
            config_id,
            client_id,
            provider,
            model,
            api_key_encrypted,
            auto_trigger_on_alert,
            auto_trigger_severity,
            weekly_report_enabled,
            weekly_report_day,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _default_agent_config_payload(client_id),
    )
    conn.commit()


def _row_to_agent_config(row: sqlite3.Row | None) -> dict | None:
    """Convertit une ligne SQLite en configuration agent exploitable."""
    if row is None:
        return None
    payload = dict(row)
    payload["auto_trigger_on_alert"] = bool(payload.get("auto_trigger_on_alert", 0))
    payload["weekly_report_enabled"] = bool(payload.get("weekly_report_enabled", 0))
    payload["weekly_report_day"] = int(payload.get("weekly_report_day") or 1)
    return payload


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def save_recommendation(
    result: dict,
    trigger_type: str,
    trigger_id: str | None,
    client_id: str = DEFAULT_CLIENT_ID,
    db_path=None,
) -> str:
    """Persiste une recommandation generee par l'agent AI.

    Args:
        result: Dict retourne par generate_recommendations().
        trigger_type: 'manual' | 'alert_triggered' | 'scheduled'.
        trigger_id: ID de l'alerte/watchlist/campagne. None si global.
        client_id: Identifiant client.
        db_path: Chemin DB optionnel (pour les tests).

    Returns:
        recommendation_id (UUID string).
    """
    rec_id = _new_id()
    sql = """
        INSERT INTO recommendations (
            recommendation_id, client_id, trigger_type, trigger_id, alert_id,
            analysis_summary, recommendations, watchlist_priorities,
            confidence_score, data_quality_note, provider_used, model_used,
            context_tokens, generation_ms, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        rec_id,
        client_id,
        trigger_type,
        trigger_id,
        result.get("alert_id"),
        result.get("analysis_summary", ""),
        _serialize_list(result.get("recommendations", [])),
        _serialize_list(result.get("watchlist_priorities", [])),
        result.get("confidence_score"),
        result.get("data_quality_note", ""),
        result.get("provider_used", ""),
        result.get("model_used", ""),
        result.get("context_tokens") or result.get("estimated_tokens"),
        result.get("generation_ms"),
        "active",
        _now(),
    )
    conn = _get_connection(db_path)
    try:
        conn.execute(sql, params)
        conn.commit()
        logger.info("Recommandation sauvegardee : %s (trigger=%s)", rec_id, trigger_type)
    except sqlite3.Error as exc:
        logger.error("Erreur lors de la sauvegarde : %s", exc)
        raise
    finally:
        conn.close()
    return rec_id


def get_client_agent_config(
    client_id: str = DEFAULT_CLIENT_ID,
    db_path=None,
) -> dict:
    """Retourne la configuration persistée de l'agent pour un client."""
    conn = _get_connection(db_path)
    try:
        _ensure_client_agent_config_row(conn, client_id)
        row = conn.execute(
            "SELECT * FROM client_agent_config WHERE client_id = ?",
            (client_id,),
        ).fetchone()
        payload = _row_to_agent_config(row)
        if payload is None:
            raise RuntimeError(f"Configuration agent introuvable pour {client_id}")
        return payload
    finally:
        conn.close()


def update_client_agent_config(
    updates: dict,
    client_id: str = DEFAULT_CLIENT_ID,
    db_path=None,
) -> dict:
    """Met a jour la configuration agent client et retourne la version persistée."""
    allowed = {
        "provider",
        "model",
        "api_key_encrypted",
        "auto_trigger_on_alert",
        "auto_trigger_severity",
        "weekly_report_enabled",
        "weekly_report_day",
    }
    payload = {key: value for key, value in dict(updates or {}).items() if key in allowed}

    if "auto_trigger_severity" in payload:
        severity = str(payload["auto_trigger_severity"]).strip().lower()
        if severity not in _VALID_AUTO_TRIGGER_SEVERITIES:
            raise ValueError(f"Severite auto_trigger invalide : {severity}")
        payload["auto_trigger_severity"] = severity

    if "auto_trigger_on_alert" in payload:
        payload["auto_trigger_on_alert"] = 1 if bool(payload["auto_trigger_on_alert"]) else 0

    if "weekly_report_enabled" in payload:
        payload["weekly_report_enabled"] = 1 if bool(payload["weekly_report_enabled"]) else 0

    if "weekly_report_day" in payload:
        payload["weekly_report_day"] = max(1, min(7, int(payload["weekly_report_day"])))

    if "provider" in payload:
        cfg = _config_module()
        payload["provider"] = str(payload["provider"]).strip() or getattr(
            cfg,
            "DEFAULT_AGENT_PROVIDER",
            "ollama_local",
        )

    if "model" in payload and payload["model"] is not None:
        payload["model"] = str(payload["model"]).strip() or None

    conn = _get_connection(db_path)
    try:
        _ensure_client_agent_config_row(conn, client_id)
        if payload:
            payload["updated_at"] = _now()
            assignments = ", ".join(f"{column} = ?" for column in payload)
            params = list(payload.values()) + [client_id]
            conn.execute(
                f"UPDATE client_agent_config SET {assignments} WHERE client_id = ?",
                params,
            )
            conn.commit()
        return get_client_agent_config(client_id=client_id, db_path=db_path)
    finally:
        conn.close()


def list_recommendations(
    status: str | None = None,
    limit: int = 20,
    db_path=None,
) -> list:
    """Retourne la liste des recommandations, triees par date decroissante.

    Args:
        status: Filtre sur le statut. None = tous.
        limit: Nombre maximum de resultats.
        db_path: Chemin DB optionnel.

    Returns:
        Liste de dicts avec recommendations et watchlist_priorities deserialises.
    """
    if status:
        sql = "SELECT * FROM recommendations WHERE status = ? ORDER BY created_at DESC LIMIT ?"
        params: tuple = (status, limit)
    else:
        sql = "SELECT * FROM recommendations ORDER BY created_at DESC LIMIT ?"
        params = (limit,)

    conn = _get_connection(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def get_recommendation(recommendation_id: str, db_path=None) -> dict | None:
    """Retourne une recommandation par son ID.

    Args:
        recommendation_id: UUID string.
        db_path: Chemin DB optionnel.

    Returns:
        Dict avec champs deserialises, ou None si non trouve.
    """
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM recommendations WHERE recommendation_id = ?",
            (recommendation_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def update_recommendation_status(
    recommendation_id: str,
    status: str,
    db_path=None,
) -> bool:
    """Met a jour le statut d'une recommandation.

    Args:
        recommendation_id: UUID string.
        status: 'active' | 'archived' | 'dismissed'.
        db_path: Chemin DB optionnel.

    Returns:
        True si la mise a jour a affecte une ligne, False sinon.

    Raises:
        ValueError: Si le statut est invalide.
    """
    if status not in _VALID_STATUSES:
        raise ValueError(
            f"Statut invalide : {status!r}. Valeurs valides : {_VALID_STATUSES}"
        )
    conn = _get_connection(db_path)
    try:
        cursor = conn.execute(
            "UPDATE recommendations SET status = ? WHERE recommendation_id = ?",
            (status, recommendation_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Erreur mise a jour statut : %s", exc)
        return False
    finally:
        conn.close()
