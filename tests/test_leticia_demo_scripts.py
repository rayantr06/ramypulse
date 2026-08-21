import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIRECTORY = REPOSITORY_ROOT / "scripts" / "leticia"
INSTALLER = SCRIPTS_DIRECTORY / "INSTALLER_DEMO_LETICIA.ps1"
LAUNCHER = SCRIPTS_DIRECTORY / "LANCER_DEMO_LETICIA.ps1"
RESET = SCRIPTS_DIRECTORY / "REINITIALISER_DEMO.ps1"
NODE_VERSION_RULES = SCRIPTS_DIRECTORY / "NODE_VERSION_DEMO.ps1"


def read_script(script: Path) -> str:
    return script.read_text(encoding="utf-8")


def port_is_listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("v20.19.0", "SUPPORTED"),
        ("v20.19.1", "SUPPORTED"),
        ("v22.12.0", "SUPPORTED"),
        ("v22.16.0", "SUPPORTED"),
        ("v20.18.9", "UNSUPPORTED"),
        ("v22.11.9", "UNSUPPORTED"),
        ("v18.20.8", "UNSUPPORTED"),
        ("v21.7.3", "UNSUPPORTED"),
        ("v23.0.0", "UNSUPPORTED"),
        ("v24.0.0", "UNSUPPORTED"),
        ("v20.19", "UNSUPPORTED"),
        ("v20.19.0-rc.1", "UNSUPPORTED"),
    ],
)
def test_node_version_matches_vite_7_engine_boundaries(version: str, expected: str):
    rules_path = str(NODE_VERSION_RULES).replace("'", "''")
    command = (
        "$ErrorActionPreference = 'Stop'; "
        f". '{rules_path}'; "
        f"if (Test-LeticiaNodeVersion -Version '{version}') {{ 'SUPPORTED' }} else {{ 'UNSUPPORTED' }}"
    )

    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


def test_leticia_scripts_are_path_safe_and_frontend_only():
    installer = read_script(INSTALLER)
    launcher = read_script(LAUNCHER)
    reset = read_script(RESET)

    assert "$PSScriptRoot" in installer
    assert "$PSScriptRoot" in launcher
    assert "$PSScriptRoot" in reset
    assert "npm ci" in installer
    assert "npm.cmd" in installer
    assert "uvicorn" not in installer + launcher + reset
    assert "python" not in installer.lower() + launcher.lower() + reset.lower()


def test_installer_requires_supported_node_and_preserves_existing_environment_file():
    installer = read_script(INSTALLER)

    assert "Test-LeticiaNodeVersion -Version $nodeVersion" in installer
    assert "$clientRoot = Join-Path $frontendRoot 'client'" in installer
    assert "$environmentFile = Join-Path $clientRoot '.env.local'" in installer
    assert "$environmentFile = Join-Path $frontendRoot '.env.local'" not in installer
    assert "Test-Path $environmentFile" in installer
    assert "VITE_RAMYPULSE_DEMO_MODE=true" in installer
    assert "VITE_RAMYPULSE_DEFAULT_TENANT_ID=demo-expo-2026" in installer
    assert "VITE_LIDAL_V3_API_ENABLED=false" in installer


def test_launcher_owns_only_the_vite_process_it_creates():
    launcher = read_script(LAUNCHER)

    assert "GetActiveTcpListeners" in launcher
    assert "5173" in launcher
    assert "node_modules/vite/bin/vite.js" in launcher
    assert "Start-Process" in launcher
    assert "-WindowStyle Hidden" in launcher
    assert "-PassThru" in launcher
    assert "Test-LeticiaNodeVersion -Version $nodeVersion" in launcher
    assert "$serverReady = $true" in launcher
    assert "Stop-Process -Id $viteProcess.Id" in launcher
    assert "Stop-Process -Name" not in launcher
    assert "taskkill" not in launcher.lower()


def test_launcher_starts_from_a_path_with_spaces_and_stops_only_its_vite_process(tmp_path: Path):
    if port_is_listening(5173):
        pytest.skip("Port 5173 is already occupied; the safety test never stops an unknown listener.")

    repository = tmp_path / "ramypulse demo path with spaces"
    shutil.copytree(SCRIPTS_DIRECTORY, repository / "scripts" / "leticia")
    vite_script = repository / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    vite_script.parent.mkdir(parents=True)
    vite_script.write_text(
        """
const http = require("node:http");
const server = http.createServer((_request, response) => {
  response.writeHead(200, { "content-type": "text/plain" });
  response.end("ready");
});
server.listen(5173, "127.0.0.1");
""".strip(),
        encoding="utf-8",
    )

    sentinel = subprocess.Popen(
        ["node", "-e", "setInterval(() => {}, 1000)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(repository / "scripts" / "leticia" / LAUNCHER.name),
                "-SmokeTest",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert "Test de lancement Vite reussi" in result.stdout
        assert sentinel.poll() is None

        deadline = time.monotonic() + 5
        while port_is_listening(5173) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not port_is_listening(5173)
    finally:
        if sentinel.poll() is None:
            sentinel.terminate()
            try:
                sentinel.wait(timeout=5)
            except subprocess.TimeoutExpired:
                sentinel.kill()
                sentinel.wait(timeout=5)


def test_scripts_explain_missing_prerequisites_and_recovery_in_french():
    installer = read_script(INSTALLER)
    launcher = read_script(LAUNCHER)
    reset = read_script(RESET)

    for script in (installer, launcher, reset):
        assert "Le dossier frontend est introuvable" in script
        assert "Verifiez que le dossier du projet est complet" in script

    assert "Node.js est introuvable" in installer
    assert "npm.cmd est introuvable" in installer
    assert "Installez Node.js 20.19.0 minimum ou Node.js 22.12.0 minimum" in installer
    assert "Node.js est introuvable" in launcher
    assert "Installez Node.js 20.19.0 minimum ou Node.js 22.12.0 minimum" in launcher
    assert "Vite n'est pas installe" in launcher
    assert "Executez d'abord INSTALLER_DEMO_LETICIA.ps1" in launcher
    assert "Le port 5173 est deja utilise" in launcher
    assert "Fermez l'application qui utilise ce port" in launcher
    assert "Le serveur Vite n'est pas disponible" in launcher


def test_scripts_use_ascii_french_messages_for_windows_powershell_compatibility():
    for script in (INSTALLER, LAUNCHER, RESET, NODE_VERSION_RULES):
        assert read_script(script).isascii()


def test_reset_opens_only_the_demo_reset_route():
    reset = read_script(RESET)

    assert "http://127.0.0.1:5173/#/demo/reset" in reset
    assert "Start-Process" in reset
    assert "Set-Content" not in reset
    assert "Remove-Item" not in reset
