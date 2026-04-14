from __future__ import annotations

import socket
import subprocess

from core.demo import runtime as runtime_helpers
from core.demo.runtime import build_frontend_runtime_env, choose_available_port, terminate_subprocess


def test_build_frontend_runtime_env_sets_preview_api_and_playwright_urls() -> None:
    env = build_frontend_runtime_env(
        {"PATH": "present"},
        api_key="demo-key",
        client_id="ramy-demo",
        backend_port=8123,
        frontend_port=4319,
    )

    assert env["PATH"] == "present"
    assert env["VITE_RAMYPULSE_API_KEY"] == "demo-key"
    assert env["VITE_SAFE_EXPO_CLIENT_ID"] == "ramy-demo"
    assert env["VITE_API_BASE_URL"] == "http://localhost:8123"
    assert env["PLAYWRIGHT_BASE_URL"] == "http://localhost:4319"


def test_choose_available_port_keeps_the_preferred_port_when_it_is_free() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        preferred = probe.getsockname()[1]

    chosen = choose_available_port(preferred)

    assert chosen == preferred


def test_choose_available_port_falls_back_when_the_preferred_port_is_taken() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        preferred = listener.getsockname()[1]

        chosen = choose_available_port(preferred)

    assert chosen != preferred


class _FakeProcess:
    def __init__(self, pid: int = 123) -> None:
        self.pid = pid
        self.returncode = None
        self.terminate_calls = 0
        self.kill_calls = 0
        self.wait_timeouts: list[float] = []

    def poll(self) -> None:
        return self.returncode

    def terminate(self) -> None:
        self.terminate_calls += 1

    def kill(self) -> None:
        self.kill_calls += 1

    def wait(self, timeout: float) -> None:
        self.wait_timeouts.append(timeout)
        self.returncode = 0


def test_terminate_subprocess_uses_taskkill_tree_on_windows(monkeypatch) -> None:
    process = _FakeProcess(pid=9876)
    calls: list[list[str]] = []

    def _fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(runtime_helpers.os, "name", "nt", raising=False)
    monkeypatch.setattr(runtime_helpers.subprocess, "run", _fake_run)

    terminate_subprocess(process)

    assert calls == [["taskkill", "/PID", "9876", "/T", "/F"]]
    assert process.terminate_calls == 0
