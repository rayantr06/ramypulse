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

    assert "$nodeVersion -notmatch '^v(20|22)\\.'" in installer
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
    assert "$nodeVersion -notmatch '^v(20|22)\\.'" in launcher
    assert "$serverReady = $true" in launcher
    assert "Stop-Process -Id $viteProcess.Id" in launcher
    assert "Stop-Process -Name" not in launcher
    assert "taskkill" not in launcher.lower()


def test_scripts_explain_missing_prerequisites_and_recovery_in_french():
    installer = read_script(INSTALLER)
    launcher = read_script(LAUNCHER)
    reset = read_script(RESET)

    for script in (installer, launcher, reset):
        assert "Le dossier frontend est introuvable" in script
        assert "Verifiez que le dossier du projet est complet" in script

    assert "Node.js est introuvable" in installer
    assert "npm.cmd est introuvable" in installer
    assert "Installez Node.js 20 ou 22" in installer
    assert "Node.js est introuvable" in launcher
    assert "Installez Node.js 20 ou 22" in launcher
    assert "Vite n'est pas installe" in launcher
    assert "Executez d'abord INSTALLER_DEMO_LETICIA.ps1" in launcher
    assert "Le port 5173 est deja utilise" in launcher
    assert "Fermez l'application qui utilise ce port" in launcher
    assert "Le serveur Vite n'est pas disponible" in launcher


def test_scripts_use_ascii_french_messages_for_windows_powershell_compatibility():
    for script in (INSTALLER, LAUNCHER, RESET):
        assert read_script(script).isascii()


def test_reset_opens_only_the_demo_reset_route():
    reset = read_script(RESET)

    assert "http://127.0.0.1:5173/#/demo/reset" in reset
    assert "Start-Process" in reset
    assert "Set-Content" not in reset
    assert "Remove-Item" not in reset
