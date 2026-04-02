"""Tests TDD pour la couche de notifications e-mail / Slack."""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402


def _config_module():
    """Retourne le module config courant, meme apres reload."""
    return importlib.import_module("config")


@pytest.fixture
def tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Base SQLite temporaire avec schema complet pour les notifications."""
    from core.database import DatabaseManager

    db_path = tmp_path / "notifications.db"
    monkeypatch.setattr(_config_module(), "SQLITE_DB_PATH", db_path, raising=False)
    db = DatabaseManager(str(db_path))
    db.create_tables()
    db.close()
    return db_path


def test_create_notification_persiste_en_base(tmp_db: Path) -> None:
    """La creation d'une notification doit persister le message et la reference."""
    from core.notifications.notification_manager import create_notification, list_notifications

    notification_id = create_notification(
        notification_type="recommendation",
        reference_id="rec-123",
        title="Rapport hebdo",
        message="3 priorites detectees",
        channel="email",
        recipient="team@example.com",
    )

    notifications = list_notifications(limit=10)

    assert isinstance(notification_id, str)
    assert notifications[0]["reference_id"] == "rec-123"
    assert notifications[0]["channel"] == "email"
    assert notifications[0]["message"] == "3 priorites detectees"


def test_send_email_notification_utilise_smtplib_et_persiste(
    tmp_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L'envoi e-mail doit passer par SMTP et creer une notification."""
    import core.notifications.notification_manager as notification_manager

    smtp_instance = MagicMock()
    smtp_factory = MagicMock(return_value=smtp_instance)
    monkeypatch.setattr(notification_manager.smtplib, "SMTP", smtp_factory)
    cfg = _config_module()
    monkeypatch.setattr(cfg, "SMTP_HOST", "smtp.example.com", raising=False)
    monkeypatch.setattr(cfg, "SMTP_PORT", 587, raising=False)
    monkeypatch.setattr(cfg, "SMTP_USERNAME", "user", raising=False)
    monkeypatch.setattr(cfg, "SMTP_PASSWORD_REFERENCE", None, raising=False)
    monkeypatch.setattr(cfg, "SMTP_FROM_EMAIL", "noreply@example.com", raising=False)

    notification_id = notification_manager.send_email_notification(
        title="Rapport hebdo",
        message="contenu",
        recipient="owner@example.com",
    )

    assert isinstance(notification_id, str)
    assert smtp_factory.called
    assert smtp_instance.sendmail.called


def test_send_slack_notification_appelle_requests_post_et_persiste(
    tmp_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L'envoi Slack doit poster sur le webhook et persister une notification."""
    import core.notifications.notification_manager as notification_manager

    response = MagicMock()
    response.raise_for_status = MagicMock()
    post = MagicMock(return_value=response)
    monkeypatch.setattr(notification_manager.requests, "post", post)

    notification_id = notification_manager.send_slack_notification(
        title="Rapport hebdo",
        message="contenu",
        webhook_url="https://hooks.slack.test/services/abc",
    )

    assert isinstance(notification_id, str)
    assert post.called


def test_send_email_notification_suit_le_module_config_recharge(
    tmp_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le module notifications doit lire le config courant meme apres reload."""
    import core.notifications.notification_manager as notification_manager

    smtp_instance = MagicMock()
    smtp_factory = MagicMock(return_value=smtp_instance)
    monkeypatch.setattr(notification_manager.smtplib, "SMTP", smtp_factory)

    if "config" in sys.modules:
        del sys.modules["config"]
    reloaded_config = importlib.import_module("config")

    monkeypatch.setattr(reloaded_config, "SQLITE_DB_PATH", tmp_db, raising=False)
    monkeypatch.setattr(reloaded_config, "SMTP_HOST", "smtp.example.com", raising=False)
    monkeypatch.setattr(reloaded_config, "SMTP_PORT", 587, raising=False)
    monkeypatch.setattr(reloaded_config, "SMTP_USERNAME", "user", raising=False)
    monkeypatch.setattr(reloaded_config, "SMTP_PASSWORD_REFERENCE", None, raising=False)
    monkeypatch.setattr(reloaded_config, "SMTP_FROM_EMAIL", "noreply@example.com", raising=False)

    notification_id = notification_manager.send_email_notification(
        title="Rapport hebdo",
        message="contenu",
        recipient="owner@example.com",
    )

    assert isinstance(notification_id, str)
    assert smtp_instance.sendmail.called
