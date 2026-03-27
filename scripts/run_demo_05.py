"""Script de lancement one-click pour la démo RamyPulse.

Vérifie les prérequis (données, index FAISS, Ollama), affiche un résumé
de l'état du système, et lance l'application Streamlit.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _check_ollama() -> bool:
    """Vérifie si Ollama est en cours d'exécution."""
    try:
        import requests
        response = requests.get(
            f"{config.OLLAMA_BASE_URL}/api/tags",
            timeout=3,
        )
        return response.status_code == 200
    except Exception:
        return False


def check_prerequisites(
    data_dir: Path | None = None,
    embeddings_dir: Path | None = None,
) -> dict[str, bool]:
    """Vérifie que tous les prérequis sont en place pour la démo.

    Args:
        data_dir: Répertoire racine des données (contient processed/).
        embeddings_dir: Répertoire des index FAISS.

    Returns:
        Dict avec l'état de chaque prérequis.
    """
    data_dir = Path(data_dir) if data_dir is not None else config.DATA_DIR
    embeddings_dir = Path(embeddings_dir) if embeddings_dir is not None else config.EMBEDDINGS_DIR

    annotated = (data_dir / "processed" / "annotated.parquet").exists()
    faiss_exists = (
        (embeddings_dir / "faiss_index.faiss").exists()
        and (embeddings_dir / "faiss_index.json").exists()
    )
    ollama = _check_ollama()

    return {
        "annotated_parquet": annotated,
        "faiss_index": faiss_exists,
        "ollama_running": ollama,
    }


def format_status(status: dict[str, bool]) -> str:
    """Formate l'état des prérequis en texte lisible.

    Args:
        status: Dict retourné par check_prerequisites.

    Returns:
        Chaîne formatée pour affichage.
    """
    lines = ["=== ÉTAT DU SYSTÈME RAMYPULSE ==="]
    icons = {True: "OK", False: "MANQUANT"}

    labels = {
        "annotated_parquet": "Données annotées (annotated.parquet)",
        "faiss_index": "Index FAISS (faiss_index.faiss)",
        "ollama_running": "Ollama LLM (API locale)",
    }

    for key, label in labels.items():
        state = icons.get(status.get(key, False), "?")
        lines.append(f"  [{state:>8}] {label}")

    all_ok = all(status.values())
    if all_ok:
        lines.append("\nTous les prérequis sont satisfaits.")
    else:
        missing = [labels[k] for k, v in status.items() if not v]
        lines.append(f"\nPrérequis manquants: {', '.join(missing)}")

    lines.append("================================")
    return "\n".join(lines)


def main() -> None:
    """Point d'entrée principal: vérifie les prérequis et lance Streamlit."""
    status = check_prerequisites()

    summary = format_status(status)
    logger.info("\n%s", summary)

    if not status["annotated_parquet"]:
        logger.error("Données annotées manquantes. Exécutez d'abord:")
        logger.error("  python scripts/02_process_data.py")
        logger.error("  python scripts/03_classify_sentiment.py")
        sys.exit(1)

    if not status["faiss_index"]:
        logger.error("Index FAISS manquant. Exécutez d'abord:")
        logger.error("  python scripts/04_build_index.py")
        sys.exit(1)

    if not status["ollama_running"]:
        logger.warning("Ollama non détecté. Le Q&A RAG ne sera pas disponible.")
        logger.warning("Lancez Ollama: ollama serve")

    app_path = PROJECT_ROOT / "app.py"
    logger.info("Lancement de Streamlit: %s", app_path)

    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run",
            str(app_path),
            "--server.port", "8501",
        ],
        cwd=str(PROJECT_ROOT),
        check=True,
    )


if __name__ == "__main__":
    main()
