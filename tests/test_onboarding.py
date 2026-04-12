from __future__ import annotations

import importlib
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import config
from api.main import app
from core.database import DatabaseManager
from core.security.auth import create_api_key
from core.tenancy.client_manager import create_client


def _prepare_isolated_db(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> dict[str, object]:
    db_path = tmp_path / "onboarding.sqlite"
    operator_client_id = "ramy-demo"

    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path, raising=False)
    monkeypatch.setattr(config, "SAFE_EXPO_CLIENT_ID", operator_client_id, raising=False)
    monkeypatch.setattr(config, "SERPAPI_API_KEY", "", raising=False)
    monkeypatch.setattr(config, "OPENAI_API_KEY", "", raising=False)

    DatabaseManager(str(db_path)).create_tables()
    create_client(client_name="Safe Expo", client_id=operator_client_id)
    _, raw_key = create_api_key(client_id=operator_client_id, label="onboarding_operator")

    return {
        "db_path": db_path,
        "headers": {"X-API-Key": raw_key},
        "operator_client_id": operator_client_id,
        "client": TestClient(app),
    }


def _seed_watchlists_payload() -> list[dict[str, object]]:
    return [
        {
            "name": "Yaghurt Plus watch seed",
            "description": "Seed watchlist",
            "scope_type": "watch_seed",
            "role": "seed",
            "filters": {
                "brand_name": "Yaghurt Plus",
                "keywords": ["yaghurt plus", "yaghurt"],
                "seed_urls": [],
                "channels": ["public_url_seed", "web_search", "facebook", "instagram"],
            },
        },
        {
            "name": "Yaghurt Plus produit",
            "description": "Product watchlist",
            "scope_type": "product",
            "role": "analysis",
            "filters": {
                "product": "yaourt",
                "period_days": 7,
                "min_volume": 10,
            },
        },
        {
            "name": "Yaghurt Plus facebook",
            "description": "Channel watchlist",
            "scope_type": "channel",
            "role": "analysis",
            "filters": {
                "channel": "facebook",
                "period_days": 7,
                "min_volume": 10,
            },
        },
    ]


def test_analyze_endpoint_returns_contract_and_watchlist_guardrails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)

    response = ctx["client"].post(
        "/api/onboarding/analyze",
        json={
            "brand_name": "Yaghurt Plus",
            "product_name": "Yaourt",
            "country": "dz",
        },
        headers=ctx["headers"],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_setup"]["client_name"] == "Yaghurt Plus"
    assert payload["tenant_setup"]["country"] == "DZ"
    assert isinstance(payload["suggested_sources"], list)
    assert isinstance(payload["required_credentials"], list)
    assert isinstance(payload["recommended_channels"], list)
    assert isinstance(payload["suggested_alert_profiles"], list)
    assert isinstance(payload["deferred_agent_config"], list)
    assert isinstance(payload["warnings"], list)
    assert payload["fallback_used"] is True

    watch_seed = [
        watchlist for watchlist in payload["suggested_watchlists"] if watchlist["scope_type"] == "watch_seed"
    ]
    analysis_watchlists = [
        watchlist for watchlist in payload["suggested_watchlists"] if watchlist["scope_type"] != "watch_seed"
    ]

    assert len(watch_seed) == 1
    assert 2 <= len(analysis_watchlists) <= 4
    assert all(watchlist["scope_type"] != "manual" for watchlist in payload["suggested_watchlists"])
    assert all(source["channel"] != "web" for source in payload["suggested_sources"])


def test_confirm_endpoint_requires_explicit_review_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)

    response = ctx["client"].post(
        "/api/onboarding/confirm",
        json={
            "tenant_setup": {
                "client_name": "Yaghurt Plus",
                "client_slug": "yaghurt-plus",
                "country": "DZ",
            },
            "brand_name": "Yaghurt Plus",
            "selected_sources": [],
            "selected_channels": ["public_url_seed", "web_search"],
            "selected_watchlists": _seed_watchlists_payload(),
            "selected_alert_profiles": [],
        },
        headers=ctx["headers"],
    )

    assert response.status_code == 422


def test_confirm_endpoint_rejects_invalid_analysis_watchlist_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)
    selected_watchlists = _seed_watchlists_payload()[:2]

    response = ctx["client"].post(
        "/api/onboarding/confirm",
        json={
            "review_confirmed": True,
            "tenant_setup": {
                "client_name": "Yaghurt Plus",
                "client_slug": "yaghurt-plus",
                "country": "DZ",
            },
            "brand_name": "Yaghurt Plus",
            "selected_sources": [],
            "selected_channels": ["public_url_seed", "web_search"],
            "selected_watchlists": selected_watchlists,
            "selected_alert_profiles": [],
        },
        headers=ctx["headers"],
    )

    assert response.status_code == 422


def test_confirm_endpoint_creates_v1_objects_and_first_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = _prepare_isolated_db(monkeypatch, tmp_path)
    onboarding_service = importlib.import_module("core.onboarding.onboarding_service")
    captured_runs: list[dict[str, object]] = []

    def _fake_start_watch_run(**kwargs):
        captured_runs.append(kwargs)
        return {
            "run_id": "run-001",
            "client_id": kwargs["client_id"],
            "watchlist_id": kwargs["watchlist_id"],
            "requested_channels": kwargs["requested_channels"],
            "stage": "queued",
            "status": "queued",
            "records_collected": 0,
            "error_message": None,
            "created_at": "2026-04-12T10:00:00Z",
            "updated_at": "2026-04-12T10:00:00Z",
            "started_at": None,
            "finished_at": None,
            "steps": {},
        }

    monkeypatch.setattr(onboarding_service, "start_watch_run", _fake_start_watch_run)

    response = ctx["client"].post(
        "/api/onboarding/confirm",
        json={
            "review_confirmed": True,
            "tenant_setup": {
                "client_name": "Yaghurt Plus",
                "client_slug": "yaghurt-plus",
                "country": "DZ",
            },
            "brand_name": "Yaghurt Plus",
            "industry": "agroalimentaire",
            "selected_sources": [
                {
                    "type": "website",
                    "label": "Site officiel",
                    "url": "https://yaghurt.example",
                    "channel": "public_url_seed",
                },
                {
                    "type": "facebook_page",
                    "label": "Yaghurt Plus DZ",
                    "url": "https://facebook.com/yaghurtplus",
                    "channel": "facebook",
                },
                {
                    "type": "instagram_profile",
                    "label": "@yaghurtplus",
                    "url": "https://instagram.com/yaghurtplus",
                    "channel": "instagram",
                },
            ],
            "selected_channels": ["public_url_seed", "web_search", "facebook", "instagram"],
            "selected_watchlists": _seed_watchlists_payload(),
            "selected_alert_profiles": [
                {
                    "watchlist_ref": "yaghurt-plus-facebook",
                    "profile_name": "Veille Facebook",
                    "enabled_by_default": True,
                    "rules": [
                        {
                            "rule_id": "negative_volume_surge",
                            "threshold_value": 60,
                            "comparator": "gt",
                            "lookback_window": "7d",
                            "severity_level": "high",
                            "reason": "Pic de volume negatif",
                        }
                    ],
                    "reason": "Surveiller les pics negatifs",
                }
            ],
            "deferred_agent_config": [
                {
                    "key": "weekly_digest",
                    "value": True,
                    "reason": "Activer plus tard apres validation humaine",
                }
            ],
        },
        headers=ctx["headers"],
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["client_id"] == "yaghurt-plus"
    assert payload["run_id"] == "run-001"
    assert payload["watch_seed_watchlist_id"]
    assert len(payload["watchlist_ids"]) == 3
    assert payload["pending_alert_profiles"][0]["profile_name"] == "Veille Facebook"
    assert payload["deferred_agent_config"][0]["key"] == "weekly_digest"
    assert {item["platform"] for item in payload["pending_credentials"]} == {"facebook", "instagram"}

    assert captured_runs == [
        {
            "client_id": "yaghurt-plus",
            "watchlist_id": payload["watch_seed_watchlist_id"],
            "requested_channels": ["public_url_seed", "web_search", "facebook", "instagram"],
        }
    ]

    with sqlite3.connect(ctx["db_path"]) as connection:
        connection.row_factory = sqlite3.Row
        watchlist_rows = connection.execute(
            """
            SELECT watchlist_id, scope_type, filters
            FROM watchlists
            WHERE client_id = ?
            ORDER BY created_at ASC
            """,
            (payload["client_id"],),
        ).fetchall()
        source_rows = connection.execute(
            """
            SELECT platform, source_type, config_json
            FROM sources
            WHERE client_id = ?
            ORDER BY created_at ASC
            """,
            (payload["client_id"],),
        ).fetchall()

    assert len(watchlist_rows) == 3
    assert {row["scope_type"] for row in watchlist_rows} == {"watch_seed", "product", "channel"}

    watch_seed_filters = next(
        json.loads(row["filters"])
        for row in watchlist_rows
        if row["watchlist_id"] == payload["watch_seed_watchlist_id"]
    )
    assert watch_seed_filters["seed_urls"] == ["https://yaghurt.example"]
    assert watch_seed_filters["channels"] == ["public_url_seed", "web_search", "facebook", "instagram"]

    assert len(source_rows) == 2
    assert {row["platform"] for row in source_rows} == {"facebook", "instagram"}
    assert all(row["platform"] != "web" for row in source_rows)
    assert "https://facebook.com/yaghurtplus" in json.loads(source_rows[0]["config_json"]).values() or (
        "https://facebook.com/yaghurtplus" in json.loads(source_rows[1]["config_json"]).values()
    )
