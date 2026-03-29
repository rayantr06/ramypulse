"""Tests TDD pour le journal d'audit SQLite."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.audit_logger import AuditLogger  # noqa: E402
from core.database import DatabaseManager  # noqa: E402


def _make_logger() -> tuple[DatabaseManager, AuditLogger]:
    """Construit un logger d'audit sur une base mémoire initialisée."""
    db = DatabaseManager(":memory:")
    db.create_tables()
    return db, AuditLogger(db)


def test_log_event_insere_un_evenement() -> None:
    """Un événement d'audit doit être inséré dans audit_log."""
    db, logger = _make_logger()

    log_id = logger.log_event("sync", source="source_registry", details={"count": 3})
    rows = logger.list_events()

    assert log_id > 0
    assert len(rows) == 1
    assert rows[0]["event_type"] == "sync"
    db.close()


def test_log_event_serialize_les_details_json() -> None:
    """Les détails doivent être sérialisés et relus comme dict."""
    db, logger = _make_logger()

    logger.log_event("import", details={"batch": "b-001", "rows": 12})
    row = logger.list_events()[0]

    assert row["details"]["batch"] == "b-001"
    assert row["details"]["rows"] == 12
    db.close()


def test_list_events_peut_filtrer_par_event_type() -> None:
    """Le filtre event_type doit restreindre les événements retournés."""
    db, logger = _make_logger()
    logger.log_event("sync", source="registry")
    logger.log_event("import", source="pipeline")

    rows = logger.list_events(event_type="import")

    assert len(rows) == 1
    assert rows[0]["event_type"] == "import"
    db.close()


def test_list_events_respecte_la_limite() -> None:
    """La limite doit tronquer le nombre de lignes retournées."""
    db, logger = _make_logger()
    logger.log_event("sync")
    logger.log_event("import")
    logger.log_event("alert")

    rows = logger.list_events(limit=2)

    assert len(rows) == 2
    db.close()


def test_log_event_accepte_details_absents() -> None:
    """Un événement sans détails explicites doit rester journalisable."""
    db, logger = _make_logger()

    logger.log_event("config_change", source="config")
    row = logger.list_events()[0]

    assert row["details"] == {}
    assert row["source"] == "config"
    db.close()
