from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.runtime.env_doctor import assert_startup_ready, collect_startup_validation


def test_collect_startup_validation_reports_missing_keys(tmp_path: Path) -> None:
    db_path = tmp_path / "ramypulse.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE heartbeat (id INTEGER)")
        connection.commit()

    report = collect_startup_validation(
        required_env=["OPENAI_API_KEY", "SERPAPI_API_KEY"],
        env={
            "OPENAI_API_KEY": "",
            "SERPAPI_API_KEY": "serp-ok",
        },
        service_checks=[],
        db_path=db_path,
    )

    assert report["ok"] is False
    assert report["required_env"][0]["ok"] is False
    assert report["required_env"][1]["ok"] is True
    assert report["database"]["ok"] is True


def test_collect_startup_validation_runs_service_probes_and_db_check(tmp_path: Path) -> None:
    db_path = tmp_path / "ramypulse.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE heartbeat (id INTEGER)")
        connection.commit()

    report = collect_startup_validation(
        required_env=["GOOGLE_API_KEY"],
        env={"GOOGLE_API_KEY": "google-ok"},
        service_checks=[
            {"id": "openai", "url": "https://api.openai.com/v1/models"},
            {"id": "tavily", "url": "https://api.tavily.com"},
        ],
        db_path=db_path,
        service_probe=lambda service_id, url, timeout: {
            "ok": service_id == "openai",
            "status_code": 200 if service_id == "openai" else 503,
            "detail": url,
        },
    )

    assert report["required_env"][0]["ok"] is True
    assert report["services"][0]["ok"] is True
    assert report["services"][1]["ok"] is False
    assert report["database"]["ok"] is True
    assert report["ok"] is False


def test_collect_startup_validation_checks_public_urls(tmp_path: Path) -> None:
    db_path = tmp_path / "ramypulse.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE heartbeat (id INTEGER)")
        connection.commit()

    from core.runtime import env_doctor

    def _fake_public_url_check(url: str, timeout: float) -> dict[str, object]:
        return {
            "ok": url.endswith("/ok"),
            "status_code": 200 if url.endswith("/ok") else 503,
            "detail": "reachable" if url.endswith("/ok") else "down",
        }

    original_check = env_doctor._public_url_check
    env_doctor._public_url_check = _fake_public_url_check
    try:
        report = collect_startup_validation(
            required_env=[],
            service_checks=[],
            public_urls=["https://example.test/ok", "https://example.test/down"],
            db_path=db_path,
            service_probe=lambda service_id, url, timeout: {"ok": True, "status_code": 200, "detail": "ok"},
        )
    finally:
        env_doctor._public_url_check = original_check

    assert len(report["urls"]) == 2
    assert report["urls"][0]["ok"] is True
    assert report["urls"][1]["ok"] is False
    assert report["ok"] is False


def test_collect_startup_validation_checks_python_dependencies(tmp_path: Path) -> None:
    db_path = tmp_path / "ramypulse.sqlite"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE heartbeat (id INTEGER)")
        connection.commit()

    report = collect_startup_validation(
        required_env=[],
        service_checks=[],
        db_path=db_path,
        dependency_checks=[
            {"id": "serpapi", "module": "serpapi"},
            {"id": "tavily", "module": "tavily"},
        ],
        dependency_probe=lambda dependency_id, module_name: {
            "ok": dependency_id == "serpapi",
            "detail": module_name,
        },
    )

    assert report["dependencies"][0]["ok"] is True
    assert report["dependencies"][1]["ok"] is False
    assert report["ok"] is False


def test_assert_startup_ready_raises_clear_error_message() -> None:
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        assert_startup_ready(
            {
                "ok": False,
                "required_env": [
                    {"key": "OPENAI_API_KEY", "ok": False, "detail": "missing"},
                ],
                "services": [],
                "dependencies": [
                    {"id": "tavily", "ok": False, "detail": "missing_dependency"},
                ],
                "urls": [{"url": "https://example.test/down", "ok": False, "detail": "unreachable"}],
                "database": {"ok": True, "detail": "connected"},
            }
        )
