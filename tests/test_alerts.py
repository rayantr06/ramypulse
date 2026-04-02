"""Tests TDD pour les alertes RamyPulse."""

from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402


def _import_or_fail(module_name: str):
    """Importe un module cible ou fait echouer explicitement le test."""
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:  # pragma: no cover - chemin rouge TDD
        pytest.fail(f"Module absent: {exc}")


def _prepare_sqlite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Configure un fichier SQLite temporaire pour les tests d'alertes."""
    db_path = tmp_path / "alerts.db"
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path)
    return db_path


def _watchlist_filters(**overrides: object) -> dict[str, object]:
    """Construit un filtre de watchlist conforme au contrat."""
    filters: dict[str, object] = {
        "channel": "google_maps",
        "aspect": None,
        "wilaya": "oran",
        "product": "ramy_citron",
        "sentiment": None,
        "period_days": 7,
        "min_volume": 1,
    }
    filters.update(overrides)
    return filters


def _signal(
    timestamp: str,
    sentiment_label: str,
    *,
    channel: str = "google_maps",
    aspect: str = "disponibilité",
    wilaya: str = "oran",
    product: str = "ramy_citron",
    text: str | None = None,
) -> dict[str, object]:
    """Construit un signal annote minimal pour les tests."""
    return {
        "text": text or f"{aspect} {sentiment_label}",
        "text_original": text or f"{aspect} {sentiment_label}",
        "sentiment_label": sentiment_label,
        "confidence": 0.91,
        "channel": channel,
        "aspect": aspect,
        "timestamp": timestamp,
        "source_url": "https://example.test/signal",
        "wilaya": wilaya,
        "product": product,
    }


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Construit un DataFrame annote et normalise les timestamps."""
    dataframe = pd.DataFrame(rows)
    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], errors="coerce")
    return dataframe


def _create_watchlist(
    watchlist_manager,
    *,
    name: str = "Surveillance Oran",
    filters: dict[str, object] | None = None,
) -> str:
    """Cree une watchlist d'assistance pour les tests de detection."""
    return watchlist_manager.create_watchlist(
        name=name,
        description="Watchlist de test",
        scope_type="region",
        filters=filters or _watchlist_filters(),
    )


def _list_rule_ids(alert_manager) -> set[str]:
    """Retourne les identifiants de regle presents dans les payloads."""
    return {
        alert["alert_payload"].get("rule_id", "")
        for alert in alert_manager.list_alerts(limit=200)
    }


def test_alert_manager_expose_le_contrat_public() -> None:
    """Le module doit exposer les 4 fonctions du contrat INTERFACES."""
    module = _import_or_fail("core.alerts.alert_manager")

    for function_name in (
        "create_alert",
        "list_alerts",
        "update_alert_status",
        "get_alert",
    ):
        assert hasattr(module, function_name), f"Fonction manquante: {function_name}"


def test_create_alert_persiste_payload_et_navigation_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """La creation doit persister les champs du contrat et deserialiser le payload."""
    _prepare_sqlite(monkeypatch, tmp_path)
    alert_manager = _import_or_fail("core.alerts.alert_manager")

    alert_id = alert_manager.create_alert(
        title="NSS critique",
        description="Le NSS est passe sous le seuil",
        severity="high",
        watchlist_id="wid-001",
        dedup_key="nss_oran_w12",
        navigation_url="/explorer?wilaya=oran",
        alert_payload={"rule_id": "nss_critical_low", "current": -50.0},
    )

    alert = alert_manager.get_alert(alert_id)

    assert alert is not None
    assert alert["alert_id"] == alert_id
    assert alert["status"] == "new"
    assert alert["severity"] == "high"
    assert alert["watchlist_id"] == "wid-001"
    assert alert["alert_rule_id"] == "nss_critical_low"
    assert alert["alert_payload"]["current"] == -50.0
    assert alert["dedup_key"] == "nss_oran_w12"
    assert alert["navigation_url"] == "/explorer?wilaya=oran"
    assert alert["detected_at"]
    assert alert["resolved_at"] is None


def test_create_alert_dedup_sur_les_alertes_actives(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Une meme dedup_key ne doit pas creer de doublon tant que l'alerte est active."""
    _prepare_sqlite(monkeypatch, tmp_path)
    alert_manager = _import_or_fail("core.alerts.alert_manager")

    first_id = alert_manager.create_alert(
        title="Volume en chute",
        description="desc",
        severity="medium",
        dedup_key="volume_drop_oran_w12",
        alert_payload={"rule_id": "volume_drop"},
    )
    second_id = alert_manager.create_alert(
        title="Volume en chute",
        description="desc",
        severity="medium",
        dedup_key="volume_drop_oran_w12",
        alert_payload={"rule_id": "volume_drop"},
    )

    assert first_id is not None
    assert second_id is None

    assert alert_manager.update_alert_status(first_id, "resolved") is True

    third_id = alert_manager.create_alert(
        title="Volume en chute",
        description="desc",
        severity="medium",
        dedup_key="volume_drop_oran_w12",
        alert_payload={"rule_id": "volume_drop"},
    )
    assert third_id is not None
    assert third_id != first_id


def test_list_alerts_filtre_par_statut_et_severite(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Le listing doit filtrer les alertes par statut et criticite."""
    _prepare_sqlite(monkeypatch, tmp_path)
    alert_manager = _import_or_fail("core.alerts.alert_manager")

    first_id = alert_manager.create_alert(
        title="A1",
        description="desc",
        severity="high",
        alert_payload={"rule_id": "nss_critical_low"},
    )
    second_id = alert_manager.create_alert(
        title="A2",
        description="desc",
        severity="low",
        alert_payload={"rule_id": "no_recent_signals"},
    )
    assert first_id and second_id
    assert alert_manager.update_alert_status(second_id, "acknowledged") is True

    new_high = alert_manager.list_alerts(status="new", severity="high")
    acknowledged = alert_manager.list_alerts(status="acknowledged")

    assert [alert["alert_id"] for alert in new_high] == [first_id]
    assert [alert["alert_id"] for alert in acknowledged] == [second_id]


def test_compute_watchlist_metrics_calcule_nss_et_deltas(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Les metriques doivent comparer la periode courante et la precedente."""
    _prepare_sqlite(monkeypatch, tmp_path)
    watchlist_manager = _import_or_fail("core.watchlists.watchlist_manager")
    detector = _import_or_fail("core.alerts.alert_detector")

    watchlist_id = _create_watchlist(
        watchlist_manager,
        filters=_watchlist_filters(aspect="disponibilite"),
    )
    watchlist = watchlist_manager.get_watchlist(watchlist_id)
    assert watchlist is not None

    df_annotated = _frame(
        [
            _signal("2026-03-08T10:00:00", "positif", aspect="disponibilité"),
            _signal("2026-03-09T10:00:00", "positif", aspect="disponibilité"),
            _signal("2026-03-10T10:00:00", "positif", aspect="disponibilité"),
            _signal("2026-03-11T10:00:00", "positif", aspect="disponibilité"),
            _signal("2026-03-18T10:00:00", "positif", aspect="disponibilité"),
            _signal("2026-03-19T10:00:00", "négatif", aspect="disponibilité"),
            _signal("2026-03-20T10:00:00", "négatif", aspect="disponibilité"),
        ]
    )

    metrics = detector.compute_watchlist_metrics(watchlist, df_annotated)

    assert metrics["watchlist_id"] == watchlist_id
    assert metrics["volume_previous"] == 4
    assert metrics["volume_current"] == 3
    assert metrics["nss_previous"] == pytest.approx(100.0)
    assert metrics["nss_current"] == pytest.approx(-33.3333333333)
    assert metrics["delta_nss"] == pytest.approx(-133.3333333333)
    assert metrics["delta_volume_pct"] == pytest.approx(-25.0)
    assert metrics["aspect_breakdown"]["disponibilité"] == pytest.approx(-33.3333333333)
    assert metrics["computed_at"]


def test_run_alert_detection_declenche_nss_critical_low_et_contexte_campagne(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Une baisse forte du NSS doit creer une alerte avec contexte campagne si disponible."""
    _prepare_sqlite(monkeypatch, tmp_path)
    watchlist_manager = _import_or_fail("core.watchlists.watchlist_manager")
    alert_manager = _import_or_fail("core.alerts.alert_manager")
    detector = _import_or_fail("core.alerts.alert_detector")

    _create_watchlist(
        watchlist_manager,
        filters=_watchlist_filters(aspect="disponibilite"),
    )

    with sqlite3.connect(config.SQLITE_DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE campaigns (
                campaign_id TEXT PRIMARY KEY,
                client_id TEXT,
                campaign_name TEXT NOT NULL,
                campaign_type TEXT,
                platform TEXT,
                description TEXT,
                influencer_handle TEXT,
                influencer_tier TEXT,
                target_segment TEXT,
                target_aspects TEXT,
                target_regions TEXT,
                keywords TEXT,
                budget_dza INTEGER,
                start_date TEXT,
                end_date TEXT,
                pre_window_days INTEGER,
                post_window_days INTEGER,
                status TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO campaigns (
                campaign_id, client_id, campaign_name, campaign_type, platform,
                target_aspects, target_regions, start_date, end_date, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "camp-001",
                config.DEFAULT_CLIENT_ID,
                "Campagne Oran Disponibilite",
                "promotion",
                "multi_platform",
                '["disponibilité"]',
                '["oran"]',
                "2026-03-15",
                "2026-03-25",
                "active",
            ),
        )
        connection.commit()

    df_annotated = _frame(
        [
            _signal("2026-03-08T10:00:00", "positif", aspect="disponibilité"),
            _signal("2026-03-09T10:00:00", "positif", aspect="disponibilité"),
            _signal("2026-03-18T10:00:00", "négatif", aspect="disponibilité"),
            _signal("2026-03-19T10:00:00", "très_négatif", aspect="disponibilité"),
            _signal("2026-03-20T10:00:00", "négatif", aspect="disponibilité"),
        ]
    )

    alert_ids = detector.run_alert_detection(df_annotated)
    alerts = alert_manager.list_alerts(limit=50)

    assert alert_ids
    assert "nss_critical_low" in _list_rule_ids(alert_manager)
    target_alert = next(
        alert for alert in alerts if alert["alert_payload"].get("rule_id") == "nss_critical_low"
    )
    assert target_alert["watchlist_id"]
    assert target_alert["alert_payload"]["active_campaigns"][0]["campaign_id"] == "camp-001"
    assert target_alert["alert_payload"]["context"]


def test_run_alert_detection_declenche_negative_volume_surge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Un ratio negatif > 60% doit creer une alerte dediee."""
    _prepare_sqlite(monkeypatch, tmp_path)
    watchlist_manager = _import_or_fail("core.watchlists.watchlist_manager")
    alert_manager = _import_or_fail("core.alerts.alert_manager")
    detector = _import_or_fail("core.alerts.alert_detector")

    _create_watchlist(
        watchlist_manager,
        filters=_watchlist_filters(aspect="fraicheur"),
    )
    df_annotated = _frame(
        [
            _signal("2026-03-17T10:00:00", "négatif", aspect="fraîcheur"),
            _signal("2026-03-18T10:00:00", "négatif", aspect="fraîcheur"),
            _signal("2026-03-19T10:00:00", "très_négatif", aspect="fraîcheur"),
            _signal("2026-03-20T10:00:00", "négatif", aspect="fraîcheur"),
            _signal("2026-03-20T12:00:00", "positif", aspect="fraîcheur"),
        ]
    )

    detector.run_alert_detection(df_annotated)

    assert "negative_volume_surge" in _list_rule_ids(alert_manager)


def test_run_alert_detection_declenche_no_recent_signals(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """L'absence de signaux depuis 7 jours doit remonter une alerte."""
    _prepare_sqlite(monkeypatch, tmp_path)
    watchlist_manager = _import_or_fail("core.watchlists.watchlist_manager")
    alert_manager = _import_or_fail("core.alerts.alert_manager")
    detector = _import_or_fail("core.alerts.alert_detector")

    _create_watchlist(
        watchlist_manager,
        filters=_watchlist_filters(channel="youtube", aspect="prix", wilaya="constantine"),
    )
    df_annotated = _frame(
        [
            _signal(
                "2026-03-01T10:00:00",
                "négatif",
                channel="youtube",
                aspect="prix",
                wilaya="constantine",
            ),
            _signal(
                "2026-03-20T10:00:00",
                "positif",
                channel="google_maps",
                aspect="disponibilite",
                wilaya="oran",
            ),
        ]
    )

    detector.run_alert_detection(df_annotated)

    assert "no_recent_signals" in _list_rule_ids(alert_manager)


def test_run_alert_detection_declenche_aspect_critical(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Un aspect sous -10 doit creer une alerte aspect_critical_[aspect]."""
    _prepare_sqlite(monkeypatch, tmp_path)
    watchlist_manager = _import_or_fail("core.watchlists.watchlist_manager")
    alert_manager = _import_or_fail("core.alerts.alert_manager")
    detector = _import_or_fail("core.alerts.alert_detector")

    _create_watchlist(
        watchlist_manager,
        filters=_watchlist_filters(aspect=None),
    )
    df_annotated = _frame(
        [
            _signal("2026-03-17T10:00:00", "positif", aspect="gout"),
            _signal("2026-03-18T10:00:00", "positif", aspect="goût"),
            _signal("2026-03-19T10:00:00", "positif", aspect="goût"),
            _signal("2026-03-20T10:00:00", "positif", aspect="goût"),
            _signal("2026-03-20T12:00:00", "positif", aspect="goût"),
            _signal("2026-03-20T15:00:00", "négatif", aspect="disponibilité"),
        ]
    )

    detector.run_alert_detection(df_annotated)

    assert "aspect_critical_disponibilite" in _list_rule_ids(alert_manager)


def test_run_alert_detection_declenche_volume_drop_sans_doublon(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Une chute de volume doit creer une seule alerte active par dedup_key."""
    _prepare_sqlite(monkeypatch, tmp_path)
    watchlist_manager = _import_or_fail("core.watchlists.watchlist_manager")
    alert_manager = _import_or_fail("core.alerts.alert_manager")
    detector = _import_or_fail("core.alerts.alert_detector")

    _create_watchlist(
        watchlist_manager,
        filters=_watchlist_filters(aspect="emballage"),
    )
    df_annotated = _frame(
        [
            _signal("2026-03-08T10:00:00", "positif", aspect="emballage"),
            _signal("2026-03-09T10:00:00", "positif", aspect="emballage"),
            _signal("2026-03-10T10:00:00", "positif", aspect="emballage"),
            _signal("2026-03-11T10:00:00", "positif", aspect="emballage"),
            _signal("2026-03-12T10:00:00", "positif", aspect="emballage"),
            _signal("2026-03-13T10:00:00", "positif", aspect="emballage"),
            _signal("2026-03-19T10:00:00", "positif", aspect="emballage"),
            _signal("2026-03-20T10:00:00", "positif", aspect="emballage"),
        ]
    )

    first_run = detector.run_alert_detection(df_annotated)
    second_run = detector.run_alert_detection(df_annotated)
    alerts = alert_manager.list_alerts(limit=50)

    assert first_run
    assert second_run == []
    volume_drop_alerts = [
        alert for alert in alerts if alert["alert_payload"].get("rule_id") == "volume_drop"
    ]
    assert len(volume_drop_alerts) == 1
