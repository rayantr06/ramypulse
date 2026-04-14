"""Runtime helpers for the Ramy expo demo scripts."""

from __future__ import annotations

import os
import socket
import subprocess


def choose_available_port(preferred: int, *, host: str = "127.0.0.1") -> int:
    """Return the preferred port when available, otherwise a free ephemeral port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, preferred))
        except OSError:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as fallback:
                fallback.bind((host, 0))
                return int(fallback.getsockname()[1])
        return preferred


def build_frontend_runtime_env(
    base_env: dict[str, str],
    *,
    api_key: str,
    client_id: str,
    backend_port: int,
    frontend_port: int,
    backend_host: str = "localhost",
    frontend_host: str = "localhost",
) -> dict[str, str]:
    """Build the frontend runtime env for preview/dev and Playwright smoke tests."""
    env = dict(base_env)
    env["VITE_RAMYPULSE_API_KEY"] = api_key
    env["VITE_SAFE_EXPO_CLIENT_ID"] = client_id
    env["VITE_API_BASE_URL"] = f"http://{backend_host}:{backend_port}"
    env["PLAYWRIGHT_BASE_URL"] = f"http://{frontend_host}:{frontend_port}"
    return env


def terminate_subprocess(process: subprocess.Popen[bytes] | None, *, timeout: float = 15) -> None:
    """Terminate a spawned subprocess and its children."""
    if process is None or process.poll() is not None:
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        return

    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
