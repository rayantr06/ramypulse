"""Tests TDD pour core/rag/generator.py.

ollama est entièrement mocké — aucun service local requis.
Teste : clés de sortie, confidence valide, chunks vides, sources mappées, fallback JSON invalide.
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.rag.generator import Generator  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CHUNKS = [
    {"text": "Le jus Ramy est délicieux", "channel": "facebook", "url": "http://fb/1", "timestamp": "2024-01-01", "score": 0.9},
    {"text": "L'emballage est parfois abîmé", "channel": "google_maps", "url": "http://gm/2", "timestamp": "2024-01-02", "score": 0.7},
]


def _ollama_resp(answer: str, sources: list, confidence: str) -> dict:
    """Construit une réponse Ollama simulée contenant du JSON valide."""
    return {
        "message": {
            "content": json.dumps(
                {"answer": answer, "sources": sources, "confidence": confidence},
                ensure_ascii=False,
            )
        }
    }


# ---------------------------------------------------------------------------
# Tests clés de sortie
# ---------------------------------------------------------------------------

@patch("core.rag.generator.ollama")
def test_generate_retourne_cles_answer_sources_confidence(mock_ollama: MagicMock) -> None:
    """generate() doit retourner un dict avec les 3 clés obligatoires."""
    mock_ollama.chat.return_value = _ollama_resp("Analyse [Source 1].", [1], "high")
    result = Generator().generate("Comment est le goût ?", CHUNKS)
    assert "answer" in result
    assert "sources" in result
    assert "confidence" in result


@patch("core.rag.generator.ollama")
def test_confidence_est_une_valeur_valide(mock_ollama: MagicMock) -> None:
    """confidence doit être 'high', 'medium' ou 'low'."""
    mock_ollama.chat.return_value = _ollama_resp("Réponse.", [1], "medium")
    result = Generator().generate("question", CHUNKS)
    assert result["confidence"] in ("high", "medium", "low")


# ---------------------------------------------------------------------------
# Tests chunks vides → je ne sais pas
# ---------------------------------------------------------------------------

@patch("core.rag.generator.ollama")
def test_chunks_vides_retourne_reponse_sans_info(mock_ollama: MagicMock) -> None:
    """Quand chunks=[], ollama ne doit PAS être appelé et confidence='low'."""
    result = Generator().generate("question impossible", [])
    mock_ollama.chat.assert_not_called()
    assert result["confidence"] == "low"
    assert result["sources"] == []
    assert len(result["answer"]) > 0


# ---------------------------------------------------------------------------
# Tests sources mappées aux chunks
# ---------------------------------------------------------------------------

@patch("core.rag.generator.ollama")
def test_sources_sont_des_dicts_avec_metadata(mock_ollama: MagicMock) -> None:
    """Les sources retournées doivent être des dicts avec channel, url, timestamp."""
    mock_ollama.chat.return_value = _ollama_resp("Analyse [Source 1].", [1], "high")
    result = Generator().generate("question", CHUNKS)
    assert isinstance(result["sources"], list)
    for src in result["sources"]:
        assert isinstance(src, dict)
        assert "channel" in src
        assert "url" in src
        assert "timestamp" in src


@patch("core.rag.generator.ollama")
def test_source_indice_hors_borne_ignoree(mock_ollama: MagicMock) -> None:
    """Un indice source hors bornes (ex: 99) doit être ignoré silencieusement."""
    mock_ollama.chat.return_value = _ollama_resp("Analyse.", [99], "low")
    result = Generator().generate("question", CHUNKS)
    assert result["sources"] == []


# ---------------------------------------------------------------------------
# Test résilience JSON invalide
# ---------------------------------------------------------------------------

@patch("core.rag.generator.ollama")
def test_reponse_ollama_non_json_retourne_fallback(mock_ollama: MagicMock) -> None:
    """Si Ollama retourne du texte brut (non JSON), le générateur ne doit pas crasher."""
    mock_ollama.chat.return_value = {
        "message": {"content": "Désolé, je n'ai pas d'information sur ce sujet."}
    }
    result = Generator().generate("question", CHUNKS)
    assert "answer" in result
    assert "confidence" in result
    assert result["confidence"] in ("high", "medium", "low")


# ---------------------------------------------------------------------------
# Test résilience exception Ollama
# ---------------------------------------------------------------------------

@patch("core.rag.generator.ollama")
def test_exception_ollama_retourne_fallback(mock_ollama: MagicMock) -> None:
    """Si ollama.chat lève une exception, generate() doit retourner un fallback."""
    mock_ollama.chat.side_effect = ConnectionError("Ollama non disponible")
    result = Generator().generate("question", CHUNKS)
    assert "answer" in result
    assert result["confidence"] == "low"
