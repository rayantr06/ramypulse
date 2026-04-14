"""Strict launcher for the Ramy expo demo."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.demo.ramy_seed import (
    RAMY_FACEBOOK_PAGE_URL,
    RAMY_INSTAGRAM_PROFILE_URL,
    issue_demo_api_key,
    resolve_ramy_seed_dataset_path,
    seed_ramy_demo,
    write_frontend_env_file,
)
from core.demo.runtime import build_frontend_runtime_env, choose_available_port, terminate_subprocess
from core.runtime.env_doctor import assert_startup_ready, collect_startup_validation


def _npm_executable(name: str) -> str:
    return f"{name}.cmd" if os.name == "nt" else name


def _wait_http(url: str, timeout: float) -> None:
    import requests

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the strict Ramy expo demo runtime.")
    parser.add_argument("--client-id", default="ramy-demo")
    parser.add_argument("--client-name", default="Ramy Demo")
    parser.add_argument("--csv-path", default=str(resolve_ramy_seed_dataset_path()))
    parser.add_argument("--frontend-env-path", default=str(PROJECT_ROOT / "frontend" / ".env.local"))
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--frontend-mode", choices=("dev", "preview"), default="dev")
    parser.add_argument("--skip-seed", action="store_true")
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    backend_port = choose_available_port(args.backend_port)
    frontend_port = int(args.frontend_port)

    report = collect_startup_validation(
        public_urls=[RAMY_FACEBOOK_PAGE_URL, RAMY_INSTAGRAM_PROFILE_URL],
        timeout=10.0,
    )
    assert_startup_ready(report)

    if not args.skip_seed:
        seed_ramy_demo(
            csv_path=Path(args.csv_path),
            client_id=args.client_id,
            client_name=args.client_name,
            reset=True,
        )

    api_key_info = issue_demo_api_key(client_id=args.client_id)
    env_path = write_frontend_env_file(
        api_key=api_key_info["api_key"],
        client_id=args.client_id,
        env_path=Path(args.frontend_env_path),
    )

    frontend_env = build_frontend_runtime_env(
        os.environ.copy(),
        api_key=api_key_info["api_key"],
        client_id=args.client_id,
        backend_port=backend_port,
        frontend_port=frontend_port,
    )

    frontend_dir = PROJECT_ROOT / "frontend"
    if args.frontend_mode == "preview":
        subprocess.run([_npm_executable("npm"), "run", "build"], cwd=frontend_dir, check=True, env=frontend_env)

    backend_process: subprocess.Popen[bytes] | None = None
    frontend_process: subprocess.Popen[bytes] | None = None
    try:
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
        _wait_http(f"http://127.0.0.1:{backend_port}/api/health", args.timeout)

        if args.frontend_mode == "preview":
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
        else:
            frontend_process = subprocess.Popen(
                [
                    _npm_executable("npm"),
                    "run",
                    "dev",
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

        _wait_http(f"http://localhost:{frontend_port}", args.timeout)
        print(f"backend_url=http://127.0.0.1:{backend_port}")
        print(f"frontend_url=http://localhost:{frontend_port}")
        print(f"frontend_env_path={env_path}")
        print(f"tenant_id={args.client_id}")
        print(f"api_key={api_key_info['api_key']}")

        while True:
            if backend_process.poll() is not None:
                raise RuntimeError("Backend process exited unexpectedly")
            if frontend_process.poll() is not None:
                raise RuntimeError("Frontend process exited unexpectedly")
            time.sleep(2)
    finally:
        terminate_subprocess(frontend_process)
        terminate_subprocess(backend_process)


if __name__ == "__main__":
    main()
