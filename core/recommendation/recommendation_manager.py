"""Gestionnaire SQLite pour les recommandations generees par l'agent AI.

CRUD complet sur la table `recommendations` selon le schema INTERFACES.md.
Utilise le pattern _get_connection() de la Section 7 (jamais DatabaseManager).
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from config import DEFAULT_CLIENT_ID, SQLITE_DB_PATH

logger = logging.getLogger(__name__)

_VALID_STATUSES = ("active", "archived", "dismissed")


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
    resolved = str(db_path) if db_path else str(SQLITE_DB_PATH)
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
        result.get("context_tokens"),
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
