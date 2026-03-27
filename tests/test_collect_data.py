"""Tests TDD pour scripts/01_collect_data.py.

Le script est chargé via importlib pour contourner le nom '01_collect_data.py'
qui n'est pas un identifiant Python valide.

Critères :
  - Produit au moins un fichier Parquet dans raw_dir
  - Le Parquet a les 7 colonnes standard RamyPulse
  - Un résumé est loggé (sources + volume)
  - Le script fonctionne sans aucun service cloud (réseau coupé simulé)
"""
import importlib.util
import io
import logging
import os
import socket
import sys
import types

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SCRIPT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts", "01_collect_data.py")
)
COLONNES_ATTENDUES = [
    "text", "sentiment_label", "channel", "aspect",
    "source_url", "timestamp", "confidence",
]


def _charger_script(raw_dir: str, demo_dir: str) -> types.ModuleType:
    """Charge le script via importlib et surcharge RAW_DIR / DEMO_DIR.

    Args:
        raw_dir: Répertoire de sortie pour les fichiers Parquet raw.
        demo_dir: Répertoire source des datasets demo.

    Returns:
        Module Python chargé avec les chemins patchés.
    """
    spec = importlib.util.spec_from_file_location("collect_data_01", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Patcher les constantes de chemin APRÈS le chargement
    mod.RAW_DIR = raw_dir
    mod.DEMO_DIR = demo_dir
    return mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_script_produit_au_moins_un_fichier_parquet(tmp_path: pytest.TempPathFactory) -> None:
    """Le script doit créer au moins un fichier .parquet dans raw_dir."""
    raw_dir = str(tmp_path / "raw")
    demo_dir = str(tmp_path / "demo")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(demo_dir, exist_ok=True)

    mod = _charger_script(raw_dir, demo_dir)
    mod.main(raw_dir=raw_dir, demo_dir=demo_dir)

    fichiers = [f for f in os.listdir(raw_dir) if f.endswith(".parquet")]
    assert len(fichiers) >= 1, "Aucun fichier Parquet produit dans raw_dir"


def test_parquet_possede_colonnes_standard(tmp_path: pytest.TempPathFactory) -> None:
    """Le fichier Parquet produit doit avoir les 7 colonnes standard RamyPulse."""
    raw_dir = str(tmp_path / "raw")
    demo_dir = str(tmp_path / "demo")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(demo_dir, exist_ok=True)

    mod = _charger_script(raw_dir, demo_dir)
    mod.main(raw_dir=raw_dir, demo_dir=demo_dir)

    chemin_output = os.path.join(raw_dir, "collected_raw.parquet")
    assert os.path.exists(chemin_output), "Le fichier collected_raw.parquet est absent"

    df = pd.read_parquet(chemin_output)
    for col in COLONNES_ATTENDUES:
        assert col in df.columns, f"Colonne manquante dans le Parquet : '{col}'"


def test_parquet_non_vide(tmp_path: pytest.TempPathFactory) -> None:
    """Le fichier Parquet produit ne doit pas être vide."""
    raw_dir = str(tmp_path / "raw")
    demo_dir = str(tmp_path / "demo")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(demo_dir, exist_ok=True)

    mod = _charger_script(raw_dir, demo_dir)
    mod.main(raw_dir=raw_dir, demo_dir=demo_dir)

    df = pd.read_parquet(os.path.join(raw_dir, "collected_raw.parquet"))
    assert len(df) > 0, "Le fichier Parquet est vide"


def test_script_log_resume_sources_et_volume(tmp_path: pytest.TempPathFactory) -> None:
    """main() doit logger un résumé mentionnant les sources et le volume."""
    raw_dir = str(tmp_path / "raw")
    demo_dir = str(tmp_path / "demo")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(demo_dir, exist_ok=True)

    mod = _charger_script(raw_dir, demo_dir)

    # Attacher un handler pour capturer les logs du module
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    mod.logger.addHandler(handler)
    mod.logger.setLevel(logging.INFO)
    mod.logger.propagate = False

    try:
        mod.main(raw_dir=raw_dir, demo_dir=demo_dir)
    finally:
        mod.logger.removeHandler(handler)

    sortie_log = log_capture.getvalue()
    mots_cles = ["RÉSUMÉ", "Volume", "Sources", "enregistrements", "sauvegardé"]
    assert any(mot in sortie_log for mot in mots_cles), (
        f"Aucun mot-clé de résumé trouvé dans les logs.\nLogs capturés:\n{sortie_log}"
    )


def test_script_fonctionne_sans_service_cloud(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le script doit produire un fichier même sans accès réseau (fallback local)."""
    raw_dir = str(tmp_path / "raw")
    demo_dir = str(tmp_path / "demo")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(demo_dir, exist_ok=True)

    # Bloquer toute résolution DNS pour simuler l'absence de réseau
    def _no_network(*args, **kwargs):  # noqa: ANN002, ANN003
        raise OSError("Réseau simulé indisponible — test isolation cloud")

    monkeypatch.setattr(socket, "getaddrinfo", _no_network)
    monkeypatch.setattr(socket, "create_connection", _no_network)

    mod = _charger_script(raw_dir, demo_dir)
    # Ne doit pas lever d'exception malgré l'absence de réseau
    mod.main(raw_dir=raw_dir, demo_dir=demo_dir)

    fichiers = [f for f in os.listdir(raw_dir) if f.endswith(".parquet")]
    assert len(fichiers) >= 1, "Pas de fichier Parquet produit sans réseau"


def test_fallback_charge_fichier_demo_si_present(tmp_path: pytest.TempPathFactory) -> None:
    """Si un Parquet existe dans demo_dir, il doit être chargé comme fallback."""
    raw_dir = str(tmp_path / "raw")
    demo_dir = str(tmp_path / "demo")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(demo_dir, exist_ok=True)

    # Créer un fichier demo minimal
    df_demo = pd.DataFrame(
        {
            "text": ["Avis demo"],
            "sentiment_label": ["positif"],
            "channel": ["facebook"],
            "aspect": ["goût"],
            "source_url": ["http://demo"],
            "timestamp": ["2024-01-01"],
            "confidence": [0.95],
        }
    )
    df_demo.to_parquet(os.path.join(demo_dir, "algerian_45k.parquet"), index=False)

    mod = _charger_script(raw_dir, demo_dir)
    mod.main(raw_dir=raw_dir, demo_dir=demo_dir)

    df_output = pd.read_parquet(os.path.join(raw_dir, "collected_raw.parquet"))
    assert len(df_output) >= 1
    assert "Avis demo" in df_output["text"].values


def test_script_charge_source_existante_si_presente(tmp_path: pytest.TempPathFactory) -> None:
    """Si facebook_raw.parquet existe déjà, il doit être réutilisé sans fallback."""
    raw_dir = str(tmp_path / "raw")
    demo_dir = str(tmp_path / "demo")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(demo_dir, exist_ok=True)

    # Pré-créer un fichier source
    df_fb = pd.DataFrame(
        {
            "text": ["post facebook"],
            "sentiment_label": ["neutre"],
            "channel": ["facebook"],
            "aspect": ["prix"],
            "source_url": ["http://fb/1"],
            "timestamp": ["2024-06-01"],
            "confidence": [0.8],
        }
    )
    df_fb.to_parquet(os.path.join(raw_dir, "facebook_raw.parquet"), index=False)

    mod = _charger_script(raw_dir, demo_dir)
    mod.main(raw_dir=raw_dir, demo_dir=demo_dir)

    df_output = pd.read_parquet(os.path.join(raw_dir, "collected_raw.parquet"))
    assert "post facebook" in df_output["text"].values
