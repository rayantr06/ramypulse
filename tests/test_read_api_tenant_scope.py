from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import config
from api.main import app
from core.database import DatabaseManager
from core.recommendation.recommendation_manager import save_recommendation
from core.runtime.runtime_settings_manager import set_runtime_setting
from core.security.auth import create_api_key
from core.tenancy.client_manager import create_client


client = TestClient(app)


def _prepare_isolated_db(monkeypatch, tmp_path: Path) -> dict[str, object]:
    db_path = tmp_path / "tenant-scope.sqlite"
    operator_client_id = "ramy-demo"
    other_client_id = "client-other"

    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path, raising=False)
    monkeypatch.setattr(config, "SAFE_EXPO_CLIENT_ID", operator_client_id, raising=False)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path, raising=False)

    DatabaseManager(str(db_path)).create_tables()
    create_client(client_name="Safe Expo", client_id=operator_client_id)
    create_client(client_name="Other Tenant", client_id=other_client_id)

    _, operator_raw_key = create_api_key(client_id=operator_client_id, label="tenant_scope_operator")
    _, non_operator_raw_key = create_api_key(client_id=other_client_id, label="tenant_scope_other")
    return {
        "operator_client_id": operator_client_id,
        "other_client_id": other_client_id,
        "operator_headers": {"X-API-Key": operator_raw_key},
        "non_operator_headers": {"X-API-Key": non_operator_raw_key},
    }


def test_dashboard_summary_uses_header_client_for_annotated_load(monkeypatch, tmp_path: Path) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)
    calls: list[object] = []

    def _fake_load_annotated(*args, **kwargs):
        calls.append(kwargs.get("client_id"))
        return pd.DataFrame()

    monkeypatch.setattr("api.routers.dashboard.load_annotated", _fake_load_annotated)

    response = client.get(
        "/api/dashboard/summary",
        headers={**ctx["operator_headers"], "X-Ramy-Client-Id": ctx["other_client_id"]},
    )

    assert response.status_code == 200
    assert calls == [ctx["other_client_id"]]


def test_recommendations_list_is_scoped_to_header_client(monkeypatch, tmp_path: Path) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)

    save_recommendation(
        result={"analysis_summary": "Operator recommendation"},
        trigger_type="manual",
        trigger_id=None,
        client_id=ctx["operator_client_id"],
    )
    other_id = save_recommendation(
        result={"analysis_summary": "Other tenant recommendation"},
        trigger_type="manual",
        trigger_id=None,
        client_id=ctx["other_client_id"],
    )

    response = client.get(
        "/api/recommendations",
        headers={**ctx["operator_headers"], "X-Ramy-Client-Id": ctx["other_client_id"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["recommendation_id"] for item in payload] == [other_id]
    assert {item["client_id"] for item in payload} == {ctx["other_client_id"]}


def test_dashboard_summary_falls_back_to_active_tenant_then_safe_expo(monkeypatch, tmp_path: Path) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)
    calls: list[object] = []

    def _fake_load_annotated(*args, **kwargs):
        calls.append(kwargs.get("client_id"))
        return pd.DataFrame()

    monkeypatch.setattr("api.routers.dashboard.load_annotated", _fake_load_annotated)

    active_response = client.get("/api/dashboard/summary", headers=ctx["operator_headers"])
    assert active_response.status_code == 200
    assert calls == [ctx["operator_client_id"]]

    calls.clear()
    set_runtime_setting("active_client_id", ctx["other_client_id"])

    persisted_response = client.get("/api/dashboard/summary", headers=ctx["operator_headers"])
    assert persisted_response.status_code == 200
    assert calls == [ctx["other_client_id"]]


def test_dashboard_summary_pins_non_operator_to_authenticated_client(
    monkeypatch,
    tmp_path: Path,
) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)
    calls: list[object] = []

    def _fake_load_annotated(*args, **kwargs):
        calls.append(kwargs.get("client_id"))
        return pd.DataFrame()

    monkeypatch.setattr("api.routers.dashboard.load_annotated", _fake_load_annotated)
    set_runtime_setting("active_client_id", ctx["operator_client_id"])

    response = client.get("/api/dashboard/summary", headers=ctx["non_operator_headers"])

    assert response.status_code == 200
    assert calls == [ctx["other_client_id"]]


def test_dashboard_summary_rejects_non_operator_cross_tenant_override(
    monkeypatch,
    tmp_path: Path,
) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)
    calls: list[object] = []

    def _fake_load_annotated(*args, **kwargs):
        calls.append(kwargs.get("client_id"))
        return pd.DataFrame()

    monkeypatch.setattr("api.routers.dashboard.load_annotated", _fake_load_annotated)

    response = client.get(
        "/api/dashboard/summary",
        headers={
            **ctx["non_operator_headers"],
            "X-Ramy-Client-Id": ctx["operator_client_id"],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant override forbidden"
    assert calls == []


def test_recommendations_context_preview_passes_header_client_to_context_builder(
    monkeypatch,
    tmp_path: Path,
) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)
    calls: list[dict[str, object]] = []

    def _fake_load_annotated(*args, **kwargs):
        return pd.DataFrame({"sentiment_label": [], "channel": [], "aspect": []})

    def _fake_build_recommendation_context(
        *,
        trigger_type: str,
        trigger_id: str | None,
        df_annotated: pd.DataFrame,
        client_id: str,
        max_rag_chunks: int = 8,
    ) -> dict:
        calls.append(
            {
                "trigger_type": trigger_type,
                "trigger_id": trigger_id,
                "client_id": client_id,
                "rows": len(df_annotated),
                "max_rag_chunks": max_rag_chunks,
            }
        )
        return {
            "current_metrics": {"nss_global": None, "volume_total": 0},
            "active_alerts": [],
            "active_watchlists": [],
            "recent_campaigns": [],
            "estimated_tokens": 123,
        }

    monkeypatch.setattr("api.routers.recommendations.load_annotated", _fake_load_annotated)
    monkeypatch.setattr(
        "api.routers.recommendations.context_builder.build_recommendation_context",
        _fake_build_recommendation_context,
    )

    response = client.get(
        "/api/recommendations/context-preview",
        headers={**ctx["operator_headers"], "X-Ramy-Client-Id": ctx["other_client_id"]},
    )

    assert response.status_code == 200
    assert calls == [
        {
            "trigger_type": "manual",
            "trigger_id": None,
            "client_id": ctx["other_client_id"],
            "rows": 0,
            "max_rag_chunks": 8,
        }
    ]
