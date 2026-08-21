from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIRECTORY = REPOSITORY_ROOT / "scripts" / "leticia"
INSTALLER = SCRIPTS_DIRECTORY / "INSTALLER_DEMO_LETICIA.ps1"
LAUNCHER = SCRIPTS_DIRECTORY / "LANCER_DEMO_LETICIA.ps1"
RESET = SCRIPTS_DIRECTORY / "REINITIALISER_DEMO.ps1"


def read_script(script: Path) -> str:
    return script.read_text(encoding="utf-8")


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

    assert "20" in installer
    assert "22" in installer
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
    assert "$serverReady = $true" in launcher
    assert "Stop-Process -Id $viteProcess.Id" in launcher
    assert "Stop-Process -Name" not in launcher
    assert "taskkill" not in launcher.lower()


def test_reset_opens_only_the_demo_reset_route():
    reset = read_script(RESET)

    assert "http://127.0.0.1:5173/#/demo/reset" in reset
    assert "Start-Process" in reset
    assert "Set-Content" not in reset
    assert "Remove-Item" not in reset
