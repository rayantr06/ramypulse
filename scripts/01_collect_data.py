"""Script de collecte batch avec fallback dataset local.

Algorithme :
  1. Tenter de charger data/raw/facebook_raw.parquet (si présent).
  2. Tenter de charger data/raw/google_raw.parquet (si présent).
  3. Si aucune source n'est trouvée : charger le dataset fallback Algerian Dialect
     depuis data/demo/ (ou générer un dataset synthétique minimal pour le PoC).
  4. Fusionner et sauvegarder dans data/raw/collected_raw.parquet.
  5. Logger un résumé : sources, volume, colonnes.

Usage :
    python scripts/01_collect_data.py
"""
import logging
import os
import sys

import numpy as np
import pandas as pd

# Ajouter la racine du projet au path pour les imports locaux
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Chemins par défaut (overridables via les paramètres de main() pour les tests)
RAW_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
DEMO_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "demo"))

COLONNES_STANDARD = [
    "text", "sentiment_label", "channel", "aspect",
    "source_url", "timestamp", "confidence",
]


def _charger_parquet(chemin: str) -> pd.DataFrame | None:
    """Charge un fichier Parquet si le chemin existe.

    Args:
        chemin: Chemin absolu vers le fichier Parquet.

    Returns:
        DataFrame chargé, ou None si le fichier est absent.
    """
    if os.path.exists(chemin):
        logger.info("Source trouvée : %s", chemin)
        return pd.read_parquet(chemin)
    return None


def _charger_fallback_demo(demo_dir: str) -> pd.DataFrame:
    """Charge le dataset fallback depuis demo_dir, ou génère un dataset synthétique.

    Args:
        demo_dir: Répertoire contenant les fichiers Parquet de démo.

    Returns:
        DataFrame avec les colonnes standard RamyPulse.
    """
    if os.path.exists(demo_dir):
        fichiers_demo = sorted(f for f in os.listdir(demo_dir) if f.endswith(".parquet"))
        if fichiers_demo:
            chemin = os.path.join(demo_dir, fichiers_demo[0])
            logger.info("Fallback demo chargé : %s", chemin)
            return pd.read_parquet(chemin)

    logger.warning(
        "Aucun dataset demo trouvé dans '%s' — génération d'un dataset synthétique minimal.",
        demo_dir,
    )
    return _generer_dataset_synthetique()


def _generer_dataset_synthetique(n: int = 100) -> pd.DataFrame:
    """Génère un dataset synthétique minimal pour le PoC.

    Args:
        n: Nombre d'enregistrements à générer.

    Returns:
        DataFrame de n lignes avec les colonnes standard RamyPulse.
    """
    from datetime import datetime

    sentiments = ["très_positif", "positif", "neutre", "négatif", "très_négatif"]
    aspects = ["goût", "emballage", "prix", "disponibilité", "fraîcheur"]
    canaux = ["facebook", "google_maps", "audio", "youtube"]

    rng = np.random.default_rng(42)

    logger.info("Dataset synthétique généré : %d enregistrements.", n)
    return pd.DataFrame(
        {
            "text": [f"Avis synthétique RamyPulse #{i}" for i in range(n)],
            "sentiment_label": rng.choice(sentiments, n).tolist(),
            "channel": rng.choice(canaux, n).tolist(),
            "aspect": rng.choice(aspects, n).tolist(),
            "source_url": [f"http://demo/avis/{i}" for i in range(n)],
            "timestamp": [datetime(2024, 1, 1).isoformat()] * n,
            "confidence": rng.uniform(0.6, 1.0, n).round(3).tolist(),
        }
    )


def _assurer_colonnes(df: pd.DataFrame) -> pd.DataFrame:
    """S'assure que toutes les colonnes standard sont présentes (crée-les à None si manquantes).

    Args:
        df: DataFrame à compléter.

    Returns:
        DataFrame avec les 7 colonnes standard garanties.
    """
    for col in COLONNES_STANDARD:
        if col not in df.columns:
            df[col] = None
    return df


def main(raw_dir: str | None = None, demo_dir: str | None = None) -> None:
    """Point d'entrée principal — collecte et sauvegarde les données.

    Args:
        raw_dir: Répertoire de sortie (défaut : data/raw/). Paramètre optionnel
                 utilisé par les tests pour isoler les entrées/sorties.
        demo_dir: Répertoire des datasets de démo (défaut : data/demo/).
    """
    if raw_dir is None:
        raw_dir = RAW_DIR
    if demo_dir is None:
        demo_dir = DEMO_DIR

    os.makedirs(raw_dir, exist_ok=True)

    frames: list[pd.DataFrame] = []
    sources_chargees: list[str] = []

    # 1. Tenter de charger les sources existantes
    for nom, nom_fichier in [
        ("facebook", "facebook_raw.parquet"),
        ("google", "google_raw.parquet"),
    ]:
        chemin = os.path.join(raw_dir, nom_fichier)
        df = _charger_parquet(chemin)
        if df is not None:
            frames.append(df)
            sources_chargees.append(nom)

    # 2. Fallback local si aucune source trouvée
    if not frames:
        logger.info("Aucune source locale — chargement du fallback demo.")
        df_fallback = _charger_fallback_demo(demo_dir)
        frames.append(df_fallback)
        sources_chargees.append("fallback_demo")

    # 3. Fusionner les sources
    df_final = pd.concat(frames, ignore_index=True)
    df_final = _assurer_colonnes(df_final)

    # 4. Sauvegarder dans data/raw/
    chemin_output = os.path.join(raw_dir, "collected_raw.parquet")
    df_final.to_parquet(chemin_output, index=False)

    # 5. Logger le résumé
    logger.info("=== RÉSUMÉ COLLECTE ===")
    logger.info("Sources    : %s", ", ".join(sources_chargees))
    logger.info("Volume     : %d enregistrements", len(df_final))
    logger.info("Colonnes   : %s", list(df_final.columns))
    logger.info("Sauvegardé : %s", chemin_output)
    logger.info("=======================")


if __name__ == "__main__":
    main()
