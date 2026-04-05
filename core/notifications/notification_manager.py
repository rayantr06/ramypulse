"""Gestionnaire de notifications e-mail / Slack et journalisation SQLite."""

from __future__ import annotations

import importlib
import logging
import smtplib
import sqlite3
import uuid
from datetime import datetime
from email.message import EmailMessage

import requests

from core.security.secret_manager import resolve_secret

logger = logging.getLogger(__name__)

_DDL_NOTIFICATIONS = """
CREATE TABLE IF NOT EXISTS notifications (
    notification_id   TEXT PRIMARY KEY,
    client_id         TEXT NOT NULL DEFAULT 'ramy_client_001',
    notification_type TEXT,
    reference_id      TEXT,
    title             TEXT NOT NULL,
    message           TEXT,
    channel           TEXT,
    status            TEXT DEFAULT 'unread',
    created_at        TEXT,
    read_at           TEXT
)
"""


def _config_module():
    """Retourne le module config courant, meme apres reload dans les tests."""
    return importlib.import_module("config")


def _get_connection() -> sqlite3.Connection:
    """Ouvre une connexion SQLite courte duree pour les notifications."""
    cfg = _config_module()
    connection = sqlite3.connect(str(cfg.SQLITE_DB_PATH))
    connection.row_factory = sqlite3.Row
    connection.execute(_DDL_NOTIFICATIONS)
    connection.commit()
    return connection


def _now() -> str:
    """Retourne un timestamp ISO courant."""
    return datetime.now().isoformat()


def _new_id() -> str:
    """Genere un identifiant UUID textuel."""
    return str(uuid.uuid4())


def create_notification(
    notification_type: str,
    reference_id: str | None,
    title: str,
    message: str,
    channel: str,
    recipient: str | None = None,
    status: str = "unread",
    client_id: str | None = None,
) -> str:
    """Persiste une notification et retourne son identifiant."""
    cfg = _config_module()
    notification_id = _new_id()

    with _get_connection() as connection:
        connection.execute(
            """
            INSERT INTO notifications (
                notification_id,
                client_id,
                notification_type,
                reference_id,
                title,
                message,
                channel,
                status,
                created_at,
                read_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notification_id,
                client_id or cfg.DEFAULT_CLIENT_ID,
                notification_type,
                reference_id,
                str(title).strip(),
                str(message or "").strip(),
                channel,
                status,
                _now(),
                None,
            ),
        )
        connection.commit()
    return notification_id


def list_notifications(
    status: str | None = None,
    channel: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Liste les notifications les plus recentes."""
    clauses: list[str] = []
    params: list[object] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if channel:
        clauses.append("channel = ?")
        params.append(channel)
    sql = "SELECT * FROM notifications"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(max(1, int(limit)))

    with _get_connection() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def mark_notification_read(notification_id: str) -> bool:
    """Marque une notification comme lue."""
    with _get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE notifications
            SET status = 'read', read_at = ?
            WHERE notification_id = ?
            """,
            (_now(), notification_id),
        )
        connection.commit()
    return cursor.rowcount > 0


def send_email_notification(
    title: str,
    message: str,
    recipient: str,
    reference_id: str | None = None,
    notification_type: str = "report",
    client_id: str | None = None,
) -> str:
    """Envoie une notification e-mail et la journalise."""
    cfg = _config_module()
    smtp_host = getattr(cfg, "SMTP_HOST", "")
    smtp_port = int(getattr(cfg, "SMTP_PORT", 587))
    smtp_username = getattr(cfg, "SMTP_USERNAME", "")
    smtp_password = resolve_secret(getattr(cfg, "SMTP_PASSWORD_REFERENCE", ""))
    from_email = getattr(cfg, "SMTP_FROM_EMAIL", "") or smtp_username
    if not smtp_host or not from_email:
        raise ValueError("Configuration SMTP incomplete")

    mail = EmailMessage()
    mail["Subject"] = title
    mail["From"] = from_email
    mail["To"] = recipient
    mail.set_content(message)

    client = smtplib.SMTP(smtp_host, smtp_port)
    try:
        try:
            client.starttls()
        except Exception:
            logger.debug("STARTTLS non disponible ou non necessaire", exc_info=True)
        if smtp_username and smtp_password:
            client.login(smtp_username, smtp_password)
        client.sendmail(from_email, recipient, mail.as_string())
    finally:
        try:
            client.quit()
        except Exception:
            pass

    return create_notification(
        notification_type=notification_type,
        reference_id=reference_id,
        title=title,
        message=message,
        channel="email",
        recipient=recipient,
        status="sent",
        client_id=client_id,
    )


def send_slack_notification(
    title: str,
    message: str,
    webhook_url: str,
    reference_id: str | None = None,
    notification_type: str = "report",
    client_id: str | None = None,
) -> str:
    """Envoie une notification Slack via webhook et la journalise."""
    resolved_webhook = resolve_secret(webhook_url)
    if not resolved_webhook:
        raise ValueError("Webhook Slack absent")

    response = requests.post(
        resolved_webhook,
        json={"text": f"*{title}*\n{message}"},
        timeout=30,
    )
    response.raise_for_status()

    return create_notification(
        notification_type=notification_type,
        reference_id=reference_id,
        title=title,
        message=message,
        channel="slack",
        recipient=resolved_webhook,
        status="sent",
        client_id=client_id,
    )
