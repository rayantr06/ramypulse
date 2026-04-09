from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import config
from core.database import DatabaseManager
from core.security.auth import create_api_key
from core.tenancy.client_manager import create_client


def _import_module(module_name: str):
    return importlib.import_module(module_name)


def _prepare_isolated_db(monkeypatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "watch-runs.sqlite"
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path, raising=False)
    DatabaseManager(str(db_path)).create_tables()
    return db_path


def _prepare_api_auth(monkeypatch, tmp_path: Path) -> dict[str, str]:
    _prepare_isolated_db(monkeypatch, tmp_path)
    client_id = "client-watch"
    create_client(client_name="Watch Tenant", client_id=client_id)
    _, raw_key = create_api_key(client_id=client_id, label="watch_runs")
    return {"X-API-Key": raw_key}


def _doc(external_id: str, text: str, channel: str) -> dict[str, object]:
    return {
        "external_document_id": external_id,
        "raw_text": text,
        "raw_payload": {"text": text},
        "raw_metadata": {
            "channel": channel,
            "source_url": f"https://example.test/{channel}/{external_id}",
        },
        "source_url": f"https://example.test/{channel}/{external_id}",
        "checksum_sha256": f"checksum-{external_id}",
        "collected_at": "2026-04-09T10:00:00Z",
    }


def test_watch_run_manager_tracks_run_and_steps(monkeypatch, tmp_path: Path) -> None:
    _prepare_isolated_db(monkeypatch, tmp_path)
    run_manager = _import_module("core.watch_runs.run_manager")

    run_id = run_manager.create_watch_run(
        client_id="client-a",
        watchlist_id="watchlist-001",
        requested_channels=["facebook", "youtube"],
    )
    run_manager.start_step(
        run_id,
        step_key="collect:facebook",
        stage="collecting",
        collector_key="facebook",
    )
    run_manager.finish_step(
        run_id,
        step_key="collect:facebook",
        status="success",
        records_seen=2,
    )
    run_manager.finish_run(
        run_id,
        status="ready",
        records_collected=2,
    )

    run = run_manager.get_watch_run(run_id)

    assert run is not None
    assert run["run_id"] == run_id
    assert run["client_id"] == "client-a"
    assert run["watchlist_id"] == "watchlist-001"
    assert run["requested_channels"] == ["facebook", "youtube"]
    assert run["status"] == "ready"
    assert run["finished_at"]
    assert set(run["steps"]) == {"collect:facebook"}
    assert run["steps"]["collect:facebook"]["status"] == "success"
    assert run["steps"]["collect:facebook"]["records_seen"] == 2
    assert run["steps"]["collect:facebook"]["collector_key"] == "facebook"


def test_execute_watch_run_handles_partial_collector_failure_and_runs_downstream(
    monkeypatch,
    tmp_path: Path,
) -> None:
    db_path = _prepare_isolated_db(monkeypatch, tmp_path)
    run_service = _import_module("core.watch_runs.run_service")
    run_manager = _import_module("core.watch_runs.run_manager")

    normalization_calls: list[dict[str, object]] = []
    refresh_calls: list[dict[str, object]] = []

    def _collector_ok(**kwargs):
        assert kwargs["client_id"] == "client-a"
        assert kwargs["watchlist_id"] == "watchlist-001"
        return [
            _doc("fb-001", "first post", "facebook"),
            _doc("fb-002", "second post", "facebook"),
        ]

    def _collector_boom(**kwargs):
        raise RuntimeError("collector failed")

    def _fake_normalization(**kwargs):
        normalization_calls.append(kwargs)
        return {"processed_count": 2, "normalizer_version": "test"}

    def _fake_refresh(**kwargs):
        refresh_calls.append(kwargs)
        return {"client_id": kwargs["client_id"], "documents": 2}

    created = run_service.start_watch_run(
        client_id="client-a",
        watchlist_id="watchlist-001",
        requested_channels=["facebook", "youtube"],
        collectors={
            "facebook": _collector_ok,
            "youtube": _collector_boom,
        },
        run_async=False,
        db_path=db_path,
        normalization_fn=_fake_normalization,
        refresh_fn=_fake_refresh,
    )

    run = run_manager.get_watch_run(created["run_id"], db_path=db_path)

    assert run is not None
    assert run["status"] == "partial_success"
    assert run["stage"] == "finished"
    assert run["records_collected"] == 2
    assert run["steps"]["collect:facebook"]["status"] == "success"
    assert run["steps"]["collect:facebook"]["records_seen"] == 2
    assert run["steps"]["collect:youtube"]["status"] == "error"
    assert "collector failed" in run["steps"]["collect:youtube"]["error_message"]
    assert run["steps"]["normalize"]["status"] == "success"
    assert run["steps"]["index"]["status"] == "success"
    assert normalization_calls[0]["client_id"] == "client-a"
    assert normalization_calls[0]["batch_size"] == 2
    assert refresh_calls[0]["client_id"] == "client-a"
    assert refresh_calls[0]["force"] is True

    with sqlite3.connect(db_path) as connection:
        raw_count = connection.execute("SELECT COUNT(*) FROM raw_documents").fetchone()[0]
        source_ids = [
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT source_id FROM raw_documents ORDER BY source_id"
            ).fetchall()
        ]

    assert raw_count == 2
    assert source_ids == ["watch:client-a:facebook"]


def test_execute_watch_run_marks_run_error_when_downstream_stage_raises(
    monkeypatch,
    tmp_path: Path,
) -> None:
    db_path = _prepare_isolated_db(monkeypatch, tmp_path)
    run_service = _import_module("core.watch_runs.run_service")
    run_manager = _import_module("core.watch_runs.run_manager")

    def _collector_ok(**kwargs):
        return [_doc("fb-001", "first post", "facebook")]

    def _fake_normalization(**kwargs):
        return {"processed_count": 1, "normalizer_version": "test"}

    def _boom_refresh(**kwargs):
        raise RuntimeError("index refresh crashed")

    created = run_service.start_watch_run(
        client_id="client-a",
        watchlist_id="watchlist-001",
        requested_channels=["facebook"],
        collectors={"facebook": _collector_ok},
        run_async=False,
        db_path=db_path,
        normalization_fn=_fake_normalization,
        refresh_fn=_boom_refresh,
    )

    run = run_manager.get_watch_run(created["run_id"], db_path=db_path)

    assert run is not None
    assert run["status"] == "error"
    assert run["finished_at"]
    assert run["steps"]["index"]["status"] == "error"
    assert "index refresh crashed" in run["steps"]["index"]["error_message"]


def test_start_watch_run_dedupes_requested_channels_before_execution(
    monkeypatch,
    tmp_path: Path,
) -> None:
    db_path = _prepare_isolated_db(monkeypatch, tmp_path)
    run_service = _import_module("core.watch_runs.run_service")
    run_manager = _import_module("core.watch_runs.run_manager")

    collector_calls: list[str] = []

    def _collector_factory(channel: str):
        def _collector(**kwargs):
            collector_calls.append(channel)
            return [_doc(f"{channel}-001", f"{channel} post", channel)]

        return _collector

    created = run_service.start_watch_run(
        client_id="client-a",
        watchlist_id="watchlist-001",
        requested_channels=["facebook", "facebook", "youtube", "facebook"],
        collectors={
            "facebook": _collector_factory("facebook"),
            "youtube": _collector_factory("youtube"),
        },
        run_async=False,
        db_path=db_path,
        normalization_fn=lambda **kwargs: {"processed_count": 2, "normalizer_version": "test"},
        refresh_fn=lambda **kwargs: {"client_id": kwargs["client_id"], "documents": 2},
    )

    run = run_manager.get_watch_run(created["run_id"], db_path=db_path)

    assert run is not None
    assert collector_calls == ["facebook", "youtube"]
    assert run["requested_channels"] == ["facebook", "youtube"]

    collect_steps = {
        step_key: step
        for step_key, step in run["steps"].items()
        if step_key.startswith("collect:")
    }

    assert set(collect_steps) == {"collect:facebook", "collect:youtube"}
    assert [step_key.removeprefix("collect:") for step_key in collect_steps] == run["requested_channels"]
    assert run["records_collected"] == sum(step["records_seen"] for step in collect_steps.values()) == 2


def test_refresh_tenant_artifacts_writes_parquet_and_uses_builder_override(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(config, "DATA_DIR", tmp_path, raising=False)
    artifact_refresh = _import_module("core.tenancy.artifact_refresh")

    dataframe = pd.DataFrame([{"text": "tenant sqlite text", "channel": "web_search"}])
    captured: dict[str, Path] = {}

    monkeypatch.setattr(
        artifact_refresh,
        "load_annotated_from_sqlite",
        lambda client_id: dataframe,
    )

    def _fake_builder(*, input_path, embeddings_dir):
        captured["input_path"] = Path(input_path)
        captured["embeddings_dir"] = Path(embeddings_dir)

    summary = artifact_refresh.refresh_tenant_artifacts(
        client_id="tenant-a",
        force=True,
        build_index_fn=_fake_builder,
    )

    assert summary["documents"] == 1
    assert summary["annotated_path"].exists()
    assert pd.read_parquet(summary["annotated_path"]).iloc[0]["text"] == "tenant sqlite text"
    assert captured["input_path"] == summary["annotated_path"]
    assert captured["embeddings_dir"] == summary["index_path"].parent


def test_watch_runs_api_creates_and_fetches_runs(monkeypatch, tmp_path: Path) -> None:
    headers = _prepare_api_auth(monkeypatch, tmp_path)
    app = _import_module("api.main").app
    client = TestClient(app)

    captured: list[dict[str, object]] = []

    def _fake_start_watch_run(**kwargs):
        captured.append(kwargs)
        return {
            "run_id": "run-001",
            "client_id": kwargs["client_id"],
            "watchlist_id": kwargs["watchlist_id"],
            "requested_channels": kwargs["requested_channels"],
            "stage": "queued",
            "status": "queued",
            "records_collected": 0,
            "error_message": None,
            "created_at": "2026-04-09T10:00:00Z",
            "updated_at": "2026-04-09T10:00:00Z",
            "started_at": None,
            "finished_at": None,
            "steps": {},
        }

    def _fake_get_watch_run(run_id: str, **kwargs):
        if run_id != "run-001":
            return None
        return {
            "run_id": "run-001",
            "client_id": "client-watch",
            "watchlist_id": "watchlist-001",
            "requested_channels": ["facebook", "youtube"],
            "stage": "finished",
            "status": "ready",
            "records_collected": 3,
            "error_message": None,
            "created_at": "2026-04-09T10:00:00Z",
            "updated_at": "2026-04-09T10:02:00Z",
            "started_at": "2026-04-09T10:00:01Z",
            "finished_at": "2026-04-09T10:02:00Z",
            "steps": {
                "collect:facebook": {
                    "step_key": "collect:facebook",
                    "stage": "collecting",
                    "collector_key": "facebook",
                    "status": "success",
                    "records_seen": 3,
                    "error_message": None,
                    "started_at": "2026-04-09T10:00:01Z",
                    "finished_at": "2026-04-09T10:00:30Z",
                }
            },
        }

    watch_runs_router = _import_module("api.routers.watch_runs")
    monkeypatch.setattr(watch_runs_router, "start_watch_run", _fake_start_watch_run)
    monkeypatch.setattr(watch_runs_router, "get_watch_run", _fake_get_watch_run)

    created = client.post(
        "/api/watch-runs",
        json={
            "watchlist_id": "watchlist-001",
            "requested_channels": ["facebook", "youtube"],
        },
        headers=headers,
    )
    fetched = client.get("/api/watch-runs/run-001", headers=headers)

    assert created.status_code == 202
    assert fetched.status_code == 200
    assert captured[0]["client_id"] == "client-watch"
    assert captured[0]["watchlist_id"] == "watchlist-001"
    assert captured[0]["requested_channels"] == ["facebook", "youtube"]
    assert fetched.json()["run_id"] == "run-001"
    assert fetched.json()["steps"]["collect:facebook"]["records_seen"] == 3
