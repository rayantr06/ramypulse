"""Post-deployment smoke test for the Ramy expo demo."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.demo.ramy_seed import (
    issue_demo_api_key,
    resolve_ramy_seed_dataset_path,
    seed_ramy_demo,
    write_frontend_env_file,
)
from core.demo.runtime import build_frontend_runtime_env, choose_available_port, terminate_subprocess
from core.runtime.env_doctor import assert_startup_ready, collect_startup_validation


def _npm_executable(name: str) -> str:
    return f"{name}.cmd" if os.name == "nt" else name


def _wait_for_http(url: str, *, timeout: float) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=3)
            if response.ok:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for {url}")


def _api_get(base_url: str, path: str, *, headers: dict[str, str]) -> object:
    response = requests.get(f"{base_url}{path}", headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def _run_api_smoke(*, base_url: str, headers: dict[str, str]) -> None:
    health = _api_get(base_url, "/api/health", headers={})
    if health.get("status") != "ok":
        raise RuntimeError(f"health check failed: {health}")

    summary = _api_get(base_url, "/api/dashboard/summary", headers=headers)
    if int(summary.get("total_mentions") or 0) <= 0:
        raise RuntimeError(f"dashboard summary has no mentions: {summary}")

    critical_alerts = _api_get(base_url, "/api/dashboard/alerts-critical", headers=headers)
    if not list(critical_alerts.get("critical_alerts") or []):
        raise RuntimeError("dashboard critical alerts is empty")

    watchlists = _api_get(base_url, "/api/watchlists?is_active=true", headers=headers)
    if len(watchlists) < 3:
        raise RuntimeError(f"expected at least 3 watchlists, got {len(watchlists)}")

    watchlist_id = str(watchlists[0]["watchlist_id"])
    watchlist_metrics = _api_get(base_url, f"/api/watchlists/{watchlist_id}/metrics", headers=headers)
    if int(watchlist_metrics.get("volume_total") or watchlist_metrics.get("volume_current") or 0) <= 0:
        raise RuntimeError(f"watchlist metrics look empty: {watchlist_metrics}")

    alerts = _api_get(base_url, "/api/alerts?limit=5", headers=headers)
    if not alerts:
        raise RuntimeError("alerts list is empty")

    recommendations = _api_get(base_url, "/api/recommendations?limit=5", headers=headers)
    if not recommendations:
        raise RuntimeError("recommendations list is empty")

    context_preview = _api_get(base_url, "/api/recommendations/context-preview?client_id=ramy-demo", headers=headers)
    if int(context_preview.get("active_watchlists_count") or 0) < 3:
        raise RuntimeError(f"recommendation context preview is incomplete: {context_preview}")

    campaigns = _api_get(base_url, "/api/campaigns", headers=headers)
    if len(campaigns) < 2:
        raise RuntimeError(f"expected at least 2 campaigns, got {len(campaigns)}")

    campaigns_overview = _api_get(base_url, "/api/campaigns/overview", headers=headers)
    if int(campaigns_overview.get("active_campaigns_count") or 0) < 1:
        raise RuntimeError(f"campaign overview is incomplete: {campaigns_overview}")

    sources = _api_get(base_url, "/api/admin/sources", headers=headers)
    if len(sources) < 3:
        raise RuntimeError(f"expected at least 3 sources, got {len(sources)}")

    source_id = str(sources[0]["source_id"])
    source_trace = _api_get(base_url, f"/api/admin/sources/{source_id}", headers=headers)
    if int(source_trace.get("raw_document_count") or 0) <= 0:
        raise RuntimeError(f"source trace is missing raw counts: {source_trace}")

    source_snapshots = _api_get(base_url, f"/api/admin/sources/{source_id}/snapshots", headers=headers)
    if not source_snapshots:
        raise RuntimeError(f"source snapshots are empty for {source_id}")

    verbatims = _api_get(base_url, "/api/explorer/verbatims?page=1&page_size=5", headers=headers)
    if int(verbatims.get("total") or 0) <= 0:
        raise RuntimeError(f"explorer verbatims are empty: {verbatims}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the seeded Ramy demo smoke test.")
    parser.add_argument("--client-id", default="ramy-demo")
    parser.add_argument("--csv-path", default=str(resolve_ramy_seed_dataset_path()))
    parser.add_argument("--frontend-env-path", default=str(PROJECT_ROOT / "frontend" / ".env.local"))
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--skip-ui", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    backend_port = choose_available_port(args.backend_port)
    frontend_port = int(args.frontend_port)

    report = collect_startup_validation(timeout=5.0)
    assert_startup_ready(report)

    seed_ramy_demo(
        csv_path=Path(args.csv_path),
        client_id=args.client_id,
        client_name="Ramy Demo",
        reset=True,
    )
    api_key_info = issue_demo_api_key(client_id=args.client_id)
    write_frontend_env_file(
        api_key=api_key_info["api_key"],
        client_id=args.client_id,
        env_path=Path(args.frontend_env_path),
    )

    backend_process: subprocess.Popen[bytes] | None = None
    frontend_process: subprocess.Popen[bytes] | None = None
    try:
        frontend_env = build_frontend_runtime_env(
            os.environ.copy(),
            api_key=api_key_info["api_key"],
            client_id=args.client_id,
            backend_port=backend_port,
            frontend_port=frontend_port,
        )
        backend_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(backend_port),
            ],
            cwd=PROJECT_ROOT,
        )
        _wait_for_http(f"http://127.0.0.1:{backend_port}/api/health", timeout=args.timeout)

        headers = {
            "X-API-Key": api_key_info["api_key"],
            "X-Ramy-Client-Id": args.client_id,
        }
        _run_api_smoke(base_url=f"http://127.0.0.1:{backend_port}", headers=headers)

        if args.skip_ui:
            print("api_smoke=ok")
            return

        frontend_dir = PROJECT_ROOT / "frontend"
        if not args.skip_build:
            subprocess.run([_npm_executable("npm"), "run", "build"], cwd=frontend_dir, check=True, env=frontend_env)

        frontend_process = subprocess.Popen(
            [
                _npm_executable("npm"),
                "run",
                "preview",
                "--",
                "--host",
                "localhost",
                "--port",
                str(frontend_port),
                "--strictPort",
            ],
            cwd=frontend_dir,
            env=frontend_env,
        )
        _wait_for_http(f"http://localhost:{frontend_port}", timeout=args.timeout)
        subprocess.run(
            [_npm_executable("npx"), "playwright", "test", "tests/e2e/ramyDemoSmoke.spec.ts"],
            cwd=frontend_dir,
            check=True,
            env=frontend_env,
        )
        print("api_smoke=ok")
        print("ui_smoke=ok")
    finally:
        terminate_subprocess(frontend_process)
        terminate_subprocess(backend_process)


if __name__ == "__main__":
    main()
