"""Application FastAPI additive de LIDAL Pulse V3."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from services.v3_api.analytics import OverviewInput, build_overview
from services.v3_api.domain import (
    ActionCreate,
    ActionTransition,
    AgentDraftRequest,
    CaseCreate,
    MonitorCreate,
    ReportCreate,
    SignalTransition,
)
from services.v3_api.repository import V3Repository
from services.v3_api.security import RequestIdentity, resolve_identity


def _database_path() -> Path:
    return Path(os.getenv("LIDAL_V3_DB_PATH", "data/lidal_v3.sqlite3"))


repository = V3Repository(_database_path())
app = FastAPI(title="LIDAL Pulse V3", version="3.0.0", docs_url="/api/v3/docs")
origins = [value.strip() for value in os.getenv("LIDAL_V3_CORS_ORIGINS", "http://localhost:5173").split(",") if value.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Organization-Id"],
)

Identity = Annotated[RequestIdentity, Depends(resolve_identity)]
WRITE_ROLES = frozenset({"owner", "admin", "analyst", "operator"})


def _require_role(identity: RequestIdentity, allowed: frozenset[str] = WRITE_ROLES) -> None:
    if identity.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="role insuffisant pour cette operation",
        )


def _idempotency_key(value: str | None) -> str:
    if not value or len(value.strip()) < 8:
        raise HTTPException(status_code=400, detail="Idempotency-Key (8 caracteres minimum) requis")
    return value.strip()


def _idempotent(
    identity: RequestIdentity,
    raw_key: str | None,
    operation: str,
    factory,
) -> dict[str, Any]:
    key = _idempotency_key(raw_key)
    existing = repository.get_idempotent(identity.organization_id, key)
    if existing is not None:
        return existing
    response = factory()
    repository.remember_idempotent(identity.organization_id, key, operation, response)
    return response


@app.get("/api/v3/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "lidal-pulse-v3"}


@app.get("/api/v3/monitors")
def list_monitors(identity: Identity) -> list[dict[str, Any]]:
    return repository.list_rows("monitors", identity.organization_id, order_by="updated_at DESC")


@app.post("/api/v3/monitors", status_code=status.HTTP_201_CREATED)
def create_monitor(
    payload: MonitorCreate,
    identity: Identity,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _require_role(identity)
    return _idempotent(
        identity, idempotency_key, "create_monitor",
        lambda: repository.create_monitor(identity.organization_id, payload),
    )


@app.get("/api/v3/mentions")
def list_mentions(
    identity: Identity,
    monitor_id: str | None = None,
    sentiment: str | None = None,
    source: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    rows = repository.list_rows("mentions", identity.organization_id, order_by="published_at DESC")
    if monitor_id:
        rows = [row for row in rows if row["monitor_id"] == monitor_id]
    if sentiment:
        rows = [row for row in rows if row["sentiment"] == sentiment]
    if source:
        rows = [row for row in rows if row["source"] == source]
    return rows[:limit]


@app.get("/api/v3/observations")
def list_observations(identity: Identity, monitor_id: str | None = None) -> list[dict[str, Any]]:
    rows = repository.list_rows("observations", identity.organization_id, order_by="last_seen_at DESC")
    return [row for row in rows if not monitor_id or row["monitor_id"] == monitor_id]


@app.get("/api/v3/signals")
def list_signals(
    identity: Identity,
    signal_status: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
) -> list[dict[str, Any]]:
    rows = repository.list_rows("signals", identity.organization_id, order_by="detected_at DESC")
    if signal_status:
        rows = [row for row in rows if row["status"] == signal_status]
    if severity:
        rows = [row for row in rows if row["severity"] == severity]
    return rows


@app.patch("/api/v3/signals/{signal_id}")
def transition_signal(
    signal_id: str,
    payload: SignalTransition,
    identity: Identity,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _require_role(identity)
    def perform() -> dict[str, Any]:
        try:
            value = repository.transition_signal(
                identity.organization_id, signal_id, payload.status.value, payload.reason, identity.user_id
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if value is None:
            raise HTTPException(status_code=404, detail="signal introuvable")
        return value

    return _idempotent(identity, idempotency_key, "transition_signal", perform)


@app.get("/api/v3/cases")
def list_cases(identity: Identity) -> list[dict[str, Any]]:
    cases = repository.list_rows("cases", identity.organization_id, order_by="updated_at DESC")
    actions = repository.list_rows("action_items", identity.organization_id, order_by="updated_at DESC")
    today = datetime.now(UTC)
    for case in cases:
        linked = [action for action in actions if action["case_id"] == case["id"]]
        case["action_count"] = len(linked)
        case["overdue_action_count"] = sum(
            1
            for action in linked
            if action.get("due_at")
            and datetime.fromisoformat(str(action["due_at"]).replace("Z", "+00:00")) < today
            and action["status"] not in {"resolved", "closed"}
        )
    return cases


@app.post("/api/v3/cases", status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    identity: Identity,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _require_role(identity)
    def perform() -> dict[str, Any]:
        try:
            return repository.create_case(identity.organization_id, payload, identity.user_id)
        except (LookupError, ValueError) as exc:
            code = 404 if isinstance(exc, LookupError) else 409
            raise HTTPException(status_code=code, detail=str(exc)) from exc

    return _idempotent(identity, idempotency_key, "create_case", perform)


@app.get("/api/v3/actions")
def list_actions(identity: Identity) -> list[dict[str, Any]]:
    return repository.list_rows("action_items", identity.organization_id, order_by="updated_at DESC")


@app.post("/api/v3/actions", status_code=status.HTTP_201_CREATED)
def create_action(
    payload: ActionCreate,
    identity: Identity,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _require_role(identity)
    def perform() -> dict[str, Any]:
        try:
            return repository.create_action(identity.organization_id, payload, identity.user_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _idempotent(identity, idempotency_key, "create_action", perform)


@app.patch("/api/v3/actions/{action_id}")
def transition_action(
    action_id: str,
    payload: ActionTransition,
    identity: Identity,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _require_role(identity)
    def perform() -> dict[str, Any]:
        value = repository.transition_action(
            identity.organization_id, action_id, payload, identity.user_id
        )
        if value is None:
            raise HTTPException(status_code=404, detail="action introuvable")
        return value

    return _idempotent(identity, idempotency_key, "transition_action", perform)


@app.get("/api/v3/analytics/overview")
def analytics_overview(identity: Identity, monitor_id: str | None = None) -> dict[str, Any]:
    now = datetime.now(UTC)
    current_start = now - timedelta(days=30)
    previous_start = current_start - timedelta(days=30)
    mentions = repository.list_rows("mentions", identity.organization_id, order_by="published_at DESC")
    if monitor_id:
        mentions = [row for row in mentions if row["monitor_id"] == monitor_id]
    current = [row for row in mentions if datetime.fromisoformat(row["published_at"].replace("Z", "+00:00")) >= current_start]
    previous = [
        row for row in mentions
        if previous_start <= datetime.fromisoformat(row["published_at"].replace("Z", "+00:00")) < current_start
    ]
    signals = repository.list_rows("signals", identity.organization_id, order_by="detected_at DESC")
    open_signals = [row for row in signals if row["status"] not in {"dismissed", "converted"}]
    actions = repository.list_rows("action_items", identity.organization_id, order_by="updated_at DESC")
    overdue = sum(
        1
        for row in actions
        if row.get("due_at")
        and datetime.fromisoformat(str(row["due_at"]).replace("Z", "+00:00")) < now
        and row["status"] not in {"resolved", "closed"}
    )
    source_health = repository.list_rows(
        "source_health_v3", identity.organization_id, order_by="measured_at DESC"
    )
    overview = build_overview(
        OverviewInput(
            mentions=current,
            previous_mentions=previous,
            collected_documents=len(current),
            valid_annotations=sum(1 for row in current if row["validation_status"] == "valid"),
            open_signals=open_signals,
            ownership_delays_hours=[],
            overdue_actions=overdue,
            source_health=source_health,
        )
    )
    overview["period"] = {
        "start": current_start.isoformat(), "end": now.isoformat(),
        "comparison_start": previous_start.isoformat(), "comparison_end": current_start.isoformat(),
    }
    return overview


@app.get("/api/v3/reports")
def list_reports(identity: Identity) -> list[dict[str, Any]]:
    return repository.list_rows("reports", identity.organization_id, order_by="period_end DESC")


@app.post("/api/v3/reports", status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    identity: Identity,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _require_role(identity)
    return _idempotent(
        identity, idempotency_key, "create_report",
        lambda: repository.create_report(identity.organization_id, payload, identity.user_id),
    )


@app.get("/api/v3/notifications")
def list_notifications(identity: Identity) -> list[dict[str, Any]]:
    return repository.list_rows("notifications_v3", identity.organization_id, order_by="created_at DESC")


@app.patch("/api/v3/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    identity: Identity,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _require_role(identity)
    def perform() -> dict[str, Any]:
        value = repository.mark_notification_read(
            identity.organization_id, notification_id, identity.user_id
        )
        if value is None:
            raise HTTPException(status_code=404, detail="notification introuvable")
        return value

    return _idempotent(identity, idempotency_key, "read_notification", perform)


@app.post("/api/v3/agent/drafts", status_code=status.HTTP_201_CREATED)
def create_agent_draft(
    payload: AgentDraftRequest,
    identity: Identity,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _require_role(identity)
    def perform() -> dict[str, Any]:
        generated_at = datetime.now(UTC).isoformat()
        table_by_kind = {
            "mention": "mentions",
            "observation": "observations",
            "metric": "metric_snapshots",
        }
        citations = []
        for reference in payload.references:
            table = table_by_kind[reference.kind]
            if repository.get_row(table, identity.organization_id, reference.id) is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"reference {reference.kind}:{reference.id} introuvable",
                )
            citations.append(reference.model_dump())
        return {
            "id": f"draft_{uuid.uuid4().hex}",
            "draft_type": payload.draft_type,
            "title": "Brouillon LIDAL a verifier",
            "content": (
                f"Brouillon prepare a partir de {len(citations)} reference(s). "
                "Chaque affirmation doit etre controlee avant diffusion. "
                f"Instruction: {payload.instruction}"
            ),
            "citations": citations,
            "generated_at": generated_at,
            "model": "deterministic-draft-v1",
            "latency_ms": 0,
            "estimated_cost_usd": 0,
            "requires_human_confirmation": True,
        }

    return _idempotent(identity, idempotency_key, "create_agent_draft", perform)
