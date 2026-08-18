"""Repository SQLite de reference pour le pilote V3.

Le domaine ne depend d'aucune primitive SQLite. La migration PostgreSQL dans
``supabase/migrations`` porte le meme contrat pour la production.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from services.v3_api.domain import (
    ActionCreate,
    ActionTransition,
    CaseCreate,
    MonitorCreate,
    ReportCreate,
)


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS organizations (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS organization_memberships (
  organization_id TEXT NOT NULL, user_id TEXT NOT NULL, role TEXT NOT NULL,
  created_at TEXT NOT NULL, PRIMARY KEY (organization_id, user_id)
);
CREATE TABLE IF NOT EXISTS monitors (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL,
  objective TEXT NOT NULL, target_type TEXT NOT NULL, target_name TEXT NOT NULL,
  aliases_json TEXT NOT NULL, exclusions_json TEXT NOT NULL, languages_json TEXT NOT NULL,
  territories_json TEXT NOT NULL, sources_json TEXT NOT NULL, competitors_json TEXT NOT NULL,
  frequency_minutes INTEGER NOT NULL, max_monthly_documents INTEGER NOT NULL,
  max_monthly_cost_dzd INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1,
  last_collected_at TEXT, coverage_note TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mentions (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, monitor_id TEXT NOT NULL,
  external_id TEXT, canonical_url TEXT, content_hash TEXT NOT NULL, text TEXT NOT NULL,
  source TEXT NOT NULL, source_url TEXT, published_at TEXT NOT NULL, collected_at TEXT NOT NULL,
  language TEXT NOT NULL, territory TEXT, validation_status TEXT NOT NULL,
  is_exploitable INTEGER NOT NULL, business_relevance TEXT NOT NULL,
  requires_parent_context INTEGER NOT NULL, author_role TEXT NOT NULL,
  sentiment TEXT, aspects_json TEXT NOT NULL DEFAULT '[]', annotation_json TEXT,
  UNIQUE (organization_id, source, content_hash)
);
CREATE TABLE IF NOT EXISTS observations (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, monitor_id TEXT NOT NULL,
  title TEXT NOT NULL, summary TEXT NOT NULL, mention_count INTEGER NOT NULL,
  sentiment TEXT NOT NULL, aspects_json TEXT NOT NULL, evidence_ids_json TEXT NOT NULL,
  first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS signals (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, monitor_id TEXT NOT NULL,
  title TEXT NOT NULL, summary TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL,
  signal_type TEXT NOT NULL, detected_at TEXT NOT NULL, mention_count INTEGER NOT NULL,
  velocity_percent REAL, confidence REAL NOT NULL, territory TEXT,
  observation_ids_json TEXT NOT NULL, evidence_ids_json TEXT NOT NULL,
  explanation TEXT NOT NULL, priority_score REAL NOT NULL, priority_factors_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS signal_mentions (
  organization_id TEXT NOT NULL, signal_id TEXT NOT NULL, mention_id TEXT NOT NULL,
  PRIMARY KEY (signal_id, mention_id)
);
CREATE TABLE IF NOT EXISTS cases (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, signal_id TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL, status TEXT NOT NULL, priority TEXT NOT NULL,
  owner_id TEXT, owner_name TEXT, due_at TEXT, expected_outcome TEXT,
  opened_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS case_comments (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, case_id TEXT NOT NULL,
  author_id TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS action_items (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, case_id TEXT NOT NULL,
  title TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL,
  owner_id TEXT, owner_name TEXT, due_at TEXT, expected_impact TEXT, metric_id TEXT,
  baseline_value REAL, result_value REAL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS timeline_events (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL, event_type TEXT NOT NULL, actor_id TEXT NOT NULL,
  payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metric_snapshots (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, monitor_id TEXT,
  metric_key TEXT NOT NULL, value REAL, numerator REAL, denominator REAL,
  period_start TEXT NOT NULL, period_end TEXT NOT NULL, dimensions_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, title TEXT NOT NULL,
  report_type TEXT NOT NULL, period_start TEXT NOT NULL, period_end TEXT NOT NULL,
  status TEXT NOT NULL, generated_at TEXT, download_url TEXT, evidence_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications_v3 (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, user_id TEXT,
  title TEXT NOT NULL, body TEXT NOT NULL, kind TEXT NOT NULL, read INTEGER NOT NULL,
  href TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_health_v3 (
  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, monitor_id TEXT,
  source TEXT NOT NULL, status TEXT NOT NULL, success_rate_percent REAL NOT NULL,
  freshness_minutes REAL, collected_documents INTEGER NOT NULL,
  analytical_coverage_percent REAL NOT NULL, measured_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS idempotency_keys (
  organization_id TEXT NOT NULL, key TEXT NOT NULL, operation TEXT NOT NULL,
  response_json TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (organization_id, key)
);
CREATE INDEX IF NOT EXISTS idx_mentions_org_monitor_published
  ON mentions (organization_id, monitor_id, published_at);
CREATE INDEX IF NOT EXISTS idx_signals_org_status_detected
  ON signals (organization_id, status, detected_at);
CREATE INDEX IF NOT EXISTS idx_actions_org_status_due
  ON action_items (organization_id, status, due_at);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode_row(row: sqlite3.Row) -> dict[str, Any]:
    value = dict(row)
    for key in tuple(value):
        if key.endswith("_json"):
            decoded_key = key.removesuffix("_json")
            value[decoded_key] = json.loads(value.pop(key) or "null")
    for key in ("active", "read", "is_exploitable", "requires_parent_context"):
        if key in value:
            value[key] = bool(value[key])
    return value


class V3Repository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def ensure_organization(self, organization_id: str, name: str | None = None) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO organizations (id, name, created_at) VALUES (?, ?, ?)",
                (organization_id, name or organization_id, _now()),
            )

    def list_rows(self, table: str, organization_id: str, *, order_by: str) -> list[dict[str, Any]]:
        allowed = {
            "monitors", "mentions", "observations", "signals", "cases", "action_items",
            "reports", "notifications_v3", "source_health_v3", "timeline_events",
        }
        if table not in allowed:
            raise ValueError(f"table non autorisee: {table}")
        with self.connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM {table} WHERE organization_id = ? ORDER BY {order_by}",
                (organization_id,),
            ).fetchall()
        return [_decode_row(row) for row in rows]

    def get_row(self, table: str, organization_id: str, row_id: str) -> dict[str, Any] | None:
        allowed = {"mentions", "observations", "metric_snapshots", "signals", "cases", "action_items"}
        if table not in allowed:
            raise ValueError("table non autorisee")
        with self.connection() as connection:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE id = ? AND organization_id = ?",
                (row_id, organization_id),
            ).fetchone()
        return _decode_row(row) if row else None

    def create_monitor(self, organization_id: str, payload: MonitorCreate) -> dict[str, Any]:
        self.ensure_organization(organization_id)
        monitor_id = _id("mon")
        now = _now()
        record = payload.model_dump(mode="json")
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO monitors (
                  id, organization_id, name, objective, target_type, target_name,
                  aliases_json, exclusions_json, languages_json, territories_json,
                  sources_json, competitors_json, frequency_minutes,
                  max_monthly_documents, max_monthly_cost_dzd, active,
                  last_collected_at, coverage_note, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, ?, ?, ?)
                """,
                (
                    monitor_id, organization_id, record["name"], record["objective"],
                    record["target_type"], record["target_name"], _json(record["aliases"]),
                    _json(record["exclusions"]), _json(record["languages"]),
                    _json(record["territories"]), _json(record["sources"]),
                    _json(record["competitors"]), record["frequency_minutes"],
                    record["max_monthly_documents"], record["max_monthly_cost_dzd"],
                    "Couverture initiale; la disponibilite varie selon chaque source.", now, now,
                ),
            )
            self._timeline(connection, organization_id, "monitor", monitor_id, "created", "system", record)
            row = connection.execute("SELECT * FROM monitors WHERE id = ?", (monitor_id,)).fetchone()
        if row is None:
            raise RuntimeError("surveillance non creee")
        return _decode_row(row)

    def transition_signal(
        self, organization_id: str, signal_id: str, status: str, reason: str, actor_id: str
    ) -> dict[str, Any] | None:
        with self.connection() as connection:
            current = connection.execute(
                "SELECT * FROM signals WHERE id = ? AND organization_id = ?",
                (signal_id, organization_id),
            ).fetchone()
            if current is None:
                return None
            if status == "confirmed" and not json.loads(current["evidence_ids_json"] or "[]"):
                raise ValueError("un signal sans preuve ne peut pas etre confirme")
            updated = connection.execute(
                "UPDATE signals SET status = ? WHERE id = ? AND organization_id = ?",
                (status, signal_id, organization_id),
            ).rowcount
            if not updated:
                return None
            self._timeline(
                connection, organization_id, "signal", signal_id, "status_changed", actor_id,
                {"status": status, "reason": reason},
            )
            row = connection.execute(
                "SELECT * FROM signals WHERE id = ? AND organization_id = ?",
                (signal_id, organization_id),
            ).fetchone()
        return _decode_row(row) if row else None

    def create_case(self, organization_id: str, payload: CaseCreate, actor_id: str) -> dict[str, Any]:
        case_id = _id("case")
        now = _now()
        with self.connection() as connection:
            signal = connection.execute(
                "SELECT id, status, evidence_ids_json FROM signals WHERE id = ? AND organization_id = ?",
                (payload.signal_id, organization_id),
            ).fetchone()
            if signal is None:
                raise LookupError("signal introuvable")
            if signal["status"] != "confirmed":
                raise ValueError("le signal doit etre confirme avant ouverture du dossier")
            if not json.loads(signal["evidence_ids_json"] or "[]"):
                raise ValueError("un dossier exige au moins une preuve reliee")
            connection.execute(
                """
                INSERT INTO cases (id, organization_id, signal_id, title, status, priority,
                  owner_id, owner_name, due_at, expected_outcome, opened_at, updated_at)
                VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id, organization_id, payload.signal_id, payload.title,
                    payload.priority.value, payload.owner_id, payload.owner_name,
                    payload.due_at.isoformat() if payload.due_at else None,
                    payload.expected_outcome, now, now,
                ),
            )
            connection.execute(
                "UPDATE signals SET status = 'converted' WHERE id = ? AND organization_id = ?",
                (payload.signal_id, organization_id),
            )
            self._timeline(
                connection, organization_id, "case", case_id, "created", actor_id,
                payload.model_dump(mode="json"),
            )
            row = connection.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if row is None:
            raise RuntimeError("dossier non cree")
        return _decode_row(row)

    def create_action(self, organization_id: str, payload: ActionCreate, actor_id: str) -> dict[str, Any]:
        action_id = _id("act")
        now = _now()
        with self.connection() as connection:
            case = connection.execute(
                "SELECT id FROM cases WHERE id = ? AND organization_id = ?",
                (payload.case_id, organization_id),
            ).fetchone()
            if case is None:
                raise LookupError("dossier introuvable")
            connection.execute(
                """
                INSERT INTO action_items (id, organization_id, case_id, title, description,
                  status, owner_id, owner_name, due_at, expected_impact, metric_id,
                  baseline_value, result_value, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                """,
                (
                    action_id, organization_id, payload.case_id, payload.title,
                    payload.description, payload.owner_id, payload.owner_name,
                    payload.due_at.isoformat() if payload.due_at else None,
                    payload.expected_impact, payload.metric_id, now, now,
                ),
            )
            self._timeline(
                connection, organization_id, "action", action_id, "created", actor_id,
                payload.model_dump(mode="json"),
            )
            row = connection.execute(
                "SELECT * FROM action_items WHERE id = ? AND organization_id = ?",
                (action_id, organization_id),
            ).fetchone()
        if row is None:
            raise RuntimeError("action non creee")
        return _decode_row(row)

    def transition_action(
        self,
        organization_id: str,
        action_id: str,
        payload: ActionTransition,
        actor_id: str,
    ) -> dict[str, Any] | None:
        now = _now()
        with self.connection() as connection:
            updated = connection.execute(
                """
                UPDATE action_items SET status = ?, result_value = COALESCE(?, result_value),
                  updated_at = ? WHERE id = ? AND organization_id = ?
                """,
                (payload.status.value, payload.result_value, now, action_id, organization_id),
            ).rowcount
            if not updated:
                return None
            self._timeline(
                connection, organization_id, "action", action_id, "status_changed", actor_id,
                payload.model_dump(mode="json"),
            )
            row = connection.execute("SELECT * FROM action_items WHERE id = ?", (action_id,)).fetchone()
        return _decode_row(row) if row else None

    def get_idempotent(self, organization_id: str, key: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT response_json FROM idempotency_keys WHERE organization_id = ? AND key = ?",
                (organization_id, key),
            ).fetchone()
        return json.loads(row["response_json"]) if row else None

    def remember_idempotent(
        self, organization_id: str, key: str, operation: str, response: dict[str, Any]
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO idempotency_keys
                  (organization_id, key, operation, response_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (organization_id, key, operation, _json(response), _now()),
            )

    def create_report(self, organization_id: str, payload: ReportCreate, actor_id: str) -> dict[str, Any]:
        report_id = _id("rpt")
        now = _now()
        with self.connection() as connection:
            evidence_count = connection.execute(
                """
                SELECT COUNT(*) AS count FROM mentions
                WHERE organization_id = ? AND published_at >= ? AND published_at < ?
                  AND validation_status = 'valid'
                """,
                (organization_id, payload.period_start.isoformat(), payload.period_end.isoformat()),
            ).fetchone()["count"]
            connection.execute(
                """
                INSERT INTO reports (id, organization_id, title, report_type, period_start,
                  period_end, status, generated_at, download_url, evidence_count)
                VALUES (?, ?, ?, ?, ?, ?, 'draft', NULL, NULL, ?)
                """,
                (
                    report_id, organization_id, payload.title, payload.report_type,
                    payload.period_start.isoformat(), payload.period_end.isoformat(), evidence_count,
                ),
            )
            self._timeline(
                connection, organization_id, "report", report_id, "draft_created", actor_id,
                payload.model_dump(mode="json"),
            )
            row = connection.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if row is None:
            raise RuntimeError("rapport non cree")
        return _decode_row(row)

    def mark_notification_read(
        self, organization_id: str, notification_id: str, actor_id: str
    ) -> dict[str, Any] | None:
        with self.connection() as connection:
            updated = connection.execute(
                "UPDATE notifications_v3 SET read = 1 WHERE id = ? AND organization_id = ?",
                (notification_id, organization_id),
            ).rowcount
            if not updated:
                return None
            self._timeline(
                connection, organization_id, "notification", notification_id, "read", actor_id, {},
            )
            row = connection.execute(
                "SELECT * FROM notifications_v3 WHERE id = ?", (notification_id,)
            ).fetchone()
        return _decode_row(row) if row else None

    @staticmethod
    def _timeline(
        connection: sqlite3.Connection,
        organization_id: str,
        entity_type: str,
        entity_id: str,
        event_type: str,
        actor_id: str,
        payload: object,
    ) -> None:
        connection.execute(
            """
            INSERT INTO timeline_events
              (id, organization_id, entity_type, entity_id, event_type, actor_id,
               payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (_id("evt"), organization_id, entity_type, entity_id, event_type, actor_id, _json(payload), _now()),
        )
