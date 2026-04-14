"""Startup validation helpers for the RamyPulse demo runtime."""

from __future__ import annotations

import importlib.util
import os
import sqlite3
from pathlib import Path
from typing import Callable, Mapping

import requests

import config

DEFAULT_REQUIRED_ENV = [
    "OPENAI_API_KEY",
    "GOOGLE_API_KEY",
    "SERPAPI_API_KEY",
    "TAVILY_API_KEY",
    "APIFY_API_KEY",
]

DEFAULT_SERVICE_CHECKS = [
    {"id": "openai", "url": "https://api.openai.com/v1/models"},
    {"id": "google_gemini", "url": "https://generativelanguage.googleapis.com/v1beta/models"},
    {"id": "serpapi", "url": "https://serpapi.com/search.json"},
    {"id": "tavily", "url": "https://api.tavily.com/search"},
    {"id": "apify", "url": "https://api.apify.com/v2/acts"},
]
DEFAULT_PUBLIC_URLS: list[str] = []
DEFAULT_DEPENDENCY_CHECKS = [
    {"id": "serpapi", "module": "serpapi"},
    {"id": "tavily", "module": "tavily"},
    {"id": "apify_client", "module": "apify_client"},
]


def _env_value(key: str, env: Mapping[str, object] | None = None) -> str:
    if env is not None and key in env:
        return str(env.get(key) or "").strip()
    return str(os.getenv(key) or getattr(config, key, "") or "").strip()


def _default_service_probe(service_id: str, url: str, timeout: float) -> dict[str, object]:
    headers = {}
    params = {}
    try:
        if service_id == "openai":
            api_key = _env_value("OPENAI_API_KEY")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        elif service_id == "google_gemini":
            api_key = _env_value("GOOGLE_API_KEY")
            if api_key:
                params["key"] = api_key
        elif service_id == "serpapi":
            api_key = _env_value("SERPAPI_API_KEY")
            if api_key:
                params.update({"engine": "google", "q": "ramy", "api_key": api_key})
        elif service_id == "tavily":
            api_key = _env_value("TAVILY_API_KEY")
            if api_key:
                response = requests.post(
                    url,
                    json={"api_key": api_key, "query": "ramy", "max_results": 1},
                    timeout=timeout,
                )
                return {
                    "ok": response.ok,
                    "status_code": response.status_code,
                    "detail": response.reason,
                }
        elif service_id == "apify":
            api_key = _env_value("APIFY_API_KEY")
            if api_key:
                params["token"] = api_key

        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "detail": response.reason,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status_code": None,
            "detail": str(exc),
        }


def _database_check(db_path: str | Path | None) -> dict[str, object]:
    resolved = Path(db_path or config.SQLITE_DB_PATH)
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(resolved)) as connection:
            connection.execute("SELECT 1")
        return {"ok": True, "detail": f"connected:{resolved}"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def _default_dependency_probe(dependency_id: str, module_name: str) -> dict[str, object]:
    try:
        spec = importlib.util.find_spec(module_name)
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}
    return {
        "ok": spec is not None,
        "detail": "installed" if spec is not None else "missing_dependency",
    }


def _public_url_check(url: str, timeout: float) -> dict[str, object]:
    try:
        response = requests.get(url, timeout=timeout, allow_redirects=True, stream=True)
        try:
            return {
                "ok": response.status_code < 400,
                "status_code": response.status_code,
                "detail": response.reason,
            }
        finally:
            response.close()
    except Exception as exc:
        return {
            "ok": False,
            "status_code": None,
            "detail": str(exc),
        }


def collect_startup_validation(
    *,
    required_env: list[str] | None = None,
    env: Mapping[str, object] | None = None,
    service_checks: list[dict[str, object]] | None = None,
    service_probe: Callable[[str, str, float], dict[str, object]] | None = None,
    dependency_checks: list[dict[str, object]] | None = None,
    dependency_probe: Callable[[str, str], dict[str, object]] | None = None,
    public_urls: list[str] | None = None,
    db_path: str | Path | None = None,
    timeout: float = 5.0,
) -> dict[str, object]:
    """Collect a fail-fast startup report."""
    required_items = []
    for key in required_env or DEFAULT_REQUIRED_ENV:
        value = _env_value(key, env)
        required_items.append(
            {
                "key": key,
                "ok": bool(value),
                "detail": "configured" if value else "missing",
            }
        )

    probe = service_probe or _default_service_probe
    service_items = []
    effective_service_checks = DEFAULT_SERVICE_CHECKS if service_checks is None else service_checks
    for service in effective_service_checks:
        service_id = str(service["id"])
        result = probe(service_id, str(service["url"]), timeout)
        service_items.append(
            {
                "id": service_id,
                "url": str(service["url"]),
                "ok": bool(result.get("ok")),
                "status_code": result.get("status_code"),
                "detail": str(result.get("detail") or ""),
            }
        )

    dependency_items = []
    dependency_checker = dependency_probe or _default_dependency_probe
    effective_dependency_checks = DEFAULT_DEPENDENCY_CHECKS if dependency_checks is None else dependency_checks
    for dependency in effective_dependency_checks:
        dependency_id = str(dependency["id"])
        module_name = str(dependency["module"])
        result = dependency_checker(dependency_id, module_name)
        dependency_items.append(
            {
                "id": dependency_id,
                "module": module_name,
                "ok": bool(result.get("ok")),
                "detail": str(result.get("detail") or ""),
            }
        )

    url_items = []
    for url in DEFAULT_PUBLIC_URLS if public_urls is None else public_urls:
        result = _public_url_check(str(url), timeout)
        url_items.append(
            {
                "url": str(url),
                "ok": bool(result.get("ok")),
                "status_code": result.get("status_code"),
                "detail": str(result.get("detail") or ""),
            }
        )

    database = _database_check(db_path)
    ok = (
        all(item["ok"] for item in required_items)
        and all(item["ok"] for item in service_items)
        and all(item["ok"] for item in dependency_items)
        and all(item["ok"] for item in url_items)
        and bool(database["ok"])
    )
    return {
        "ok": ok,
        "required_env": required_items,
        "services": service_items,
        "dependencies": dependency_items,
        "urls": url_items,
        "database": database,
    }


def assert_startup_ready(report: dict[str, object]) -> None:
    """Raise a clear error when the startup report is not healthy."""
    if report.get("ok"):
        return

    failures: list[str] = []
    for item in report.get("required_env", []):
        if not item.get("ok"):
            failures.append(f"{item.get('key')}: {item.get('detail')}")
    for item in report.get("services", []):
        if not item.get("ok"):
            failures.append(f"service {item.get('id')}: {item.get('detail')}")
    for item in report.get("dependencies", []):
        if not item.get("ok"):
            failures.append(f"dependency {item.get('id')}: {item.get('detail')}")
    for item in report.get("urls", []):
        if not item.get("ok"):
            failures.append(f"url {item.get('url')}: {item.get('detail')}")
    database = report.get("database", {})
    if not database.get("ok"):
        failures.append(f"database: {database.get('detail')}")
    raise RuntimeError("Startup validation failed: " + "; ".join(failures))
