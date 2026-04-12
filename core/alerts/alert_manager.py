"""Gestion CRUD et deduplication des alertes RamyPulse."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
import importlib
from datetime import datetime

import config
import pandas as pd
from core.notifications.notification_manager import (
    send_email_notification,
    send_slack_notification,
)
from core.security.secret_manager import resolve_secret

logger = logging.getLogger(__name__)

_ACTIVE_STATUSES = {"new", "acknowledged", "investigating"}
_VALID_STATUSES = _ACTIVE_STATUSES | {"resolved", "dismissed"}
_VALID_SEVERITIES = {"critical", "high", "medium", "low"}
_REQUIRED_COLUMNS = {
    "alert_id",
    "client_id",
    "watchlist_id",
    "alert_rule_id",
    "title",
    "description",
    "severity",
    "status",
    "detected_at",
    "resolved_at",
    "alert_payload",
    "dedup_key",
    "navigation_url",
}


def _config_module():
    """Retourne le module config courant, meme apres reload dans les tests."""
    return importlib.import_module("config")


def _get_connection() -> sqlite3.Connection:
    """Retourne une connexion SQLite courte duree pour les alertes."""
    cfg = _config_module()
    connection = sqlite3.connect(cfg.SQLITE_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _deserialize_dict(value: str | None) -> dict:
    """Deserialise une chaine JSON en dictionnaire Python."""
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _serialize_dict(value: dict | None) -> str:
    """Serialise un dictionnaire Python vers SQLite."""
    return json.dumps(value or {}, ensure_ascii=False)


def _new_id() -> str:
    """Genere un identifiant UUID textuel."""
    return str(uuid.uuid4())


def _now() -> str:
    """Retourne le timestamp ISO courant."""
    return datetime.now().isoformat()


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """Indique si une table SQLite existe deja."""
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    """Liste les colonnes presentes sur une table."""
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_alerts_table(connection: sqlite3.Connection) -> None:
    """Garantit la presence de la table alerts conforme au contrat."""
    if _table_exists(connection, "alerts"):
        columns = _table_columns(connection, "alerts")
        missing = _REQUIRED_COLUMNS - columns
        if missing:
            raise RuntimeError(
                "Schema alerts incompatible avec INTERFACES.md: "
                f"colonnes manquantes {sorted(missing)}"
            )
        return

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id TEXT PRIMARY KEY,
            client_id TEXT DEFAULT 'ramy_client_001',
            watchlist_id TEXT,
            alert_rule_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            severity TEXT,
            status TEXT DEFAULT 'new',
            detected_at TEXT,
            resolved_at TEXT,
            alert_payload TEXT,
            dedup_key TEXT,
            navigation_url TEXT
        )
        """
    )
    connection.commit()


def _severity_rank(severity: str) -> int:
    """Convertit une severite en rang croissant de criticite."""
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return order.get(str(severity).strip().lower(), -1)


def _load_dataframe_for_autotrigger() -> pd.DataFrame:
    """Charge les donnees annotees pour alimenter le contexte reco."""
    cfg = _config_module()
    try:
        dataframe = pd.read_parquet(cfg.ANNOTATED_PARQUET_PATH)
    except FileNotFoundError:
        return pd.DataFrame()
    except Exception:
        logger.exception("Impossible de charger annotated.parquet pour auto-trigger")
        return pd.DataFrame()

    if "timestamp" in dataframe.columns:
        dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], errors="coerce")
    return dataframe


def _patch_alert_payload(alert_id: str, patch: dict) -> None:
    """Met a jour partiellement le payload JSON d'une alerte existante."""
    with _get_connection() as connection:
        _ensure_alerts_table(connection)
        row = connection.execute(
            "SELECT alert_payload FROM alerts WHERE alert_id = ?",
            (alert_id,),
        ).fetchone()
        if row is None:
            return
        payload = _deserialize_dict(row["alert_payload"])
        payload.update(patch)
        connection.execute(
            "UPDATE alerts SET alert_payload = ? WHERE alert_id = ?",
            (_serialize_dict(payload), alert_id),
        )
        connection.commit()


def _should_auto_trigger(agent_config: dict, severity: str) -> bool:
    """Indique si une alerte respecte la politique de declenchement auto."""
    if not agent_config.get("auto_trigger_on_alert"):
        return False
    return _severity_rank(severity) >= _severity_rank(agent_config.get("auto_trigger_severity", "critical"))


def _should_auto_notify(severity: str) -> bool:
    """Indique si la severite respecte le seuil de notification automatique."""
    cfg = _config_module()
    minimum = getattr(cfg, "ALERT_NOTIFICATION_MIN_SEVERITY", "critical")
    return _severity_rank(severity) >= _severity_rank(minimum)


def _format_alert_notification_message(title: str, description: str, navigation_url: str | None) -> str:
    """Construit un message simple reutilisable pour email et Slack."""
    lines = [str(description or "").strip() or title]
    if navigation_url:
        lines.extend(["", f"Lien: {navigation_url}"])
    return "\n".join(lines).strip()


def _run_recommendation_auto_trigger(alert_id: str, severity: str) -> None:
    """Genere une recommandation automatiquement si la configuration le permet."""
    try:
        from core.recommendation.agent_client import generate_recommendations
        from core.recommendation.context_builder import build_recommendation_context
        from core.recommendation.recommendation_manager import (
            get_client_agent_config,
            save_recommendation,
        )

        agent_config = get_client_agent_config()
        if not _should_auto_trigger(agent_config, severity):
            return

        dataframe = _load_dataframe_for_autotrigger()
        context = build_recommendation_context(
            trigger_type="alert_triggered",
            trigger_id=alert_id,
            df_annotated=dataframe,
            max_rag_chunks=8,
        )
        result = generate_recommendations(
            context=context,
            provider=agent_config.get("provider") or _config_module().DEFAULT_AGENT_PROVIDER,
            model=agent_config.get("model"),
            api_key=resolve_secret(agent_config.get("api_key_encrypted")) or None,
        )
        result["alert_id"] = alert_id
        result["context_tokens"] = context.get("estimated_tokens")
        recommendation_id = save_recommendation(
            result=result,
            trigger_type="alert_triggered",
            trigger_id=alert_id,
        )
        _patch_alert_payload(
            alert_id,
            {
                "has_recommendations": True,
                "recommendation_id": recommendation_id,
            },
        )
    except Exception:
        logger.exception("Echec auto-trigger recommandation pour alerte %s", alert_id)


def _run_notification_auto_trigger(
    *,
    alert_id: str,
    client_id: str,
    title: str,
    description: str,
    severity: str,
    navigation_url: str | None,
) -> None:
    """Envoie les notifications auto configurees pour une alerte si le seuil le permet."""
    try:
        if not _should_auto_notify(severity):
            return

        cfg = _config_module()
        email_recipient = getattr(cfg, "ALERT_NOTIFICATION_EMAIL_TO", "")
        slack_reference = getattr(cfg, "ALERT_NOTIFICATION_SLACK_WEBHOOK_REFERENCE", "")
        if not email_recipient and not resolve_secret(slack_reference):
            return

        message = _format_alert_notification_message(title, description, navigation_url)
        if email_recipient:
            send_email_notification(
                title=f"RamyPulse Alert - {title}",
                message=message,
                recipient=email_recipient,
                reference_id=alert_id,
                notification_type="alert",
                client_id=client_id,
            )
        if resolve_secret(slack_reference):
            send_slack_notification(
                title=f"RamyPulse Alert - {title}",
                message=message,
                webhook_url=slack_reference,
                reference_id=alert_id,
                notification_type="alert",
                client_id=client_id,
            )
    except Exception:
        logger.exception("Echec auto-notification pour alerte %s", alert_id)


def _row_to_alert(row: sqlite3.Row | None) -> dict | None:
    """Convertit une ligne SQLite en dictionnaire d'alerte."""
    if row is None:
        return None
    payload = dict(row)
    payload["alert_payload"] = _deserialize_dict(payload.get("alert_payload"))
    return payload


def create_alert(
    title: str,
    description: str,
    severity: str,
    alert_payload: dict,
    watchlist_id: str | None = None,
    dedup_key: str | None = None,
    navigation_url: str | None = None,
    client_id: str | None = None,
) -> str | None:
    """Cree une alerte ou retourne None si la deduplication bloque un doublon."""
    if severity not in _VALID_SEVERITIES:
        raise ValueError(f"severity invalide: {severity}")
    if not isinstance(alert_payload, dict):
        raise ValueError("alert_payload doit etre un dict")
    if not title or not str(title).strip():
        raise ValueError("title est requis")

    alert_rule_id = alert_payload.get("rule_id") or alert_payload.get("alert_rule_id")
    detected_at = _now()

    effective_client_id = client_id or config.DEFAULT_CLIENT_ID

    with _get_connection() as connection:
        _ensure_alerts_table(connection)
        if dedup_key:
            duplicate = connection.execute(
                """
                SELECT alert_id
                FROM alerts
                WHERE dedup_key = ?
                  AND status IN ('new', 'acknowledged', 'investigating')
                LIMIT 1
                """,
                (dedup_key,),
            ).fetchone()
            if duplicate is not None:
                logger.info("Alerte dedupliquee: %s", dedup_key)
                return None

        alert_id = _new_id()
        connection.execute(
            """
            INSERT INTO alerts (
                alert_id,
                client_id,
                watchlist_id,
                alert_rule_id,
                title,
                description,
                severity,
                status,
                detected_at,
                resolved_at,
                alert_payload,
                dedup_key,
                navigation_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                effective_client_id,
                watchlist_id,
                str(alert_rule_id) if alert_rule_id else None,
                str(title).strip(),
                str(description or "").strip(),
                severity,
                "new",
                detected_at,
                None,
                _serialize_dict(alert_payload),
                dedup_key,
                navigation_url,
            ),
        )
        connection.commit()

    logger.info("Alerte creee: %s", alert_id)
    _run_recommendation_auto_trigger(alert_id, severity)
    _run_notification_auto_trigger(
        alert_id=alert_id,
        client_id=effective_client_id,
        title=str(title).strip(),
        description=str(description or "").strip(),
        severity=severity,
        navigation_url=navigation_url,
    )
    return alert_id


def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    limit: int = 100,
    client_id: str | None = None,
) -> list[dict]:
    """Liste les alertes avec payload JSON automatiquement deserialise."""
    clauses = []
    params: list[object] = []
    if client_id is not None and str(client_id).strip():
        clauses.append("client_id = ?")
        params.append(str(client_id).strip())
    if status is not None:
        if status not in _VALID_STATUSES:
            raise ValueError(f"status invalide: {status}")
        clauses.append("status = ?")
        params.append(status)
    if severity is not None:
        if severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity invalide: {severity}")
        clauses.append("severity = ?")
        params.append(severity)

    sql = "SELECT * FROM alerts"
    if clauses:
        sql += f" WHERE {' AND '.join(clauses)}"
    sql += " ORDER BY detected_at DESC, alert_id DESC LIMIT ?"
    params.append(max(1, int(limit)))

    with _get_connection() as connection:
        _ensure_alerts_table(connection)
        rows = connection.execute(sql, params).fetchall()

    return [_row_to_alert(row) for row in rows]


def update_alert_status(
    alert_id: str,
    status: str,
    client_id: str | None = None,
) -> bool:
    """Met a jour le statut d'une alerte selon le cycle de vie autorise."""
    if status not in _VALID_STATUSES:
        raise ValueError(f"status invalide: {status}")

    resolved_at = _now() if status in {"resolved", "dismissed"} else None
    with _get_connection() as connection:
        _ensure_alerts_table(connection)
        sql = """
            UPDATE alerts
            SET status = ?, resolved_at = ?
            WHERE alert_id = ?
            """
        params: list[object] = [status, resolved_at, alert_id]
        if client_id is not None and str(client_id).strip():
            sql = """
            UPDATE alerts
            SET status = ?, resolved_at = ?
            WHERE alert_id = ? AND client_id = ?
            """
            params.append(str(client_id).strip())
        cursor = connection.execute(
            sql,
            tuple(params),
        )
        connection.commit()

    updated = cursor.rowcount > 0
    if updated:
        logger.info("Alerte %s -> %s", alert_id, status)
    return updated


def get_alert(alert_id: str, client_id: str | None = None) -> dict | None:
    """Retourne une alerte complete ou None si absente."""
    sql = "SELECT * FROM alerts WHERE alert_id = ?"
    params: list[object] = [alert_id]
    if client_id is not None and str(client_id).strip():
        sql += " AND client_id = ?"
        params.append(str(client_id).strip())
    with _get_connection() as connection:
        _ensure_alerts_table(connection)
        row = connection.execute(sql, tuple(params)).fetchone()
    return _row_to_alert(row)
