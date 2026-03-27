"""Tests TDD pour scripts/05_run_demo.py.

Teste: vérification des prérequis, résumé système, lancement conditionnel.
Tout est mocké (pas de vrai Ollama ni Streamlit lancé).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Tests vérification prérequis
# ---------------------------------------------------------------------------

def test_check_data_detecte_fichier_absent(tmp_path: Path) -> None:
    """check_prerequisites doit signaler un fichier annotated.parquet manquant."""
    from scripts.run_demo_05 import check_prerequisites

    status = check_prerequisites(
        data_dir=tmp_path,
        embeddings_dir=tmp_path / "embeddings",
    )

    assert status["annotated_parquet"] is False


def test_check_data_detecte_fichier_present(tmp_path: Path) -> None:
    """check_prerequisites doit détecter un annotated.parquet présent."""
    from scripts.run_demo_05 import check_prerequisites
    import pandas as pd

    processed = tmp_path / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"text": ["a"]}).to_parquet(processed / "annotated.parquet")

    emb = tmp_path / "embeddings"
    emb.mkdir(parents=True, exist_ok=True)
    (emb / "faiss_index.faiss").touch()
    (emb / "faiss_index.json").touch()

    status = check_prerequisites(data_dir=tmp_path, embeddings_dir=emb)

    assert status["annotated_parquet"] is True


def test_check_faiss_detecte_index_absent(tmp_path: Path) -> None:
    """check_prerequisites doit signaler un index FAISS manquant."""
    from scripts.run_demo_05 import check_prerequisites

    status = check_prerequisites(
        data_dir=tmp_path,
        embeddings_dir=tmp_path / "embeddings",
    )

    assert status["faiss_index"] is False


def test_check_faiss_detecte_index_present(tmp_path: Path) -> None:
    """check_prerequisites doit détecter un index FAISS présent."""
    from scripts.run_demo_05 import check_prerequisites
    import pandas as pd

    processed = tmp_path / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"text": ["a"]}).to_parquet(processed / "annotated.parquet")

    emb = tmp_path / "embeddings"
    emb.mkdir(parents=True, exist_ok=True)
    (emb / "faiss_index.faiss").touch()
    (emb / "faiss_index.json").touch()

    status = check_prerequisites(data_dir=tmp_path, embeddings_dir=emb)

    assert status["faiss_index"] is True


def test_check_ollama_retourne_bool() -> None:
    """check_prerequisites doit inclure une clé ollama_running (bool)."""
    from scripts.run_demo_05 import check_prerequisites
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        status = check_prerequisites(
            data_dir=Path(tmp),
            embeddings_dir=Path(tmp) / "embeddings",
        )
    assert isinstance(status["ollama_running"], bool)


def test_format_status_retourne_string() -> None:
    """format_status doit retourner une chaîne lisible."""
    from scripts.run_demo_05 import format_status

    status = {
        "annotated_parquet": True,
        "faiss_index": False,
        "ollama_running": True,
    }

    output = format_status(status)
    assert isinstance(output, str)
    assert len(output) > 0
