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
    assert result["sources"][0]["text"] == CHUNKS[0]["text"]


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
        assert "text" in src
        assert "channel" in src
        assert "url" in src
        assert "timestamp" in src


@patch("core.rag.generator.ollama")
def test_source_indice_hors_borne_ignoree(mock_ollama: MagicMock) -> None:
    """Un indice source hors bornes doit déclencher un fallback avec source valide."""
    mock_ollama.chat.return_value = _ollama_resp("Analyse.", [99], "low")
    result = Generator().generate("question", CHUNKS)
    assert result["confidence"] == "low"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["text"] == CHUNKS[0]["text"]
    assert result["sources"][0]["url"] == CHUNKS[0]["url"]


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
    assert result["confidence"] == "low"
    assert len(result["sources"]) == 1
    assert "pas assez d'informations" in result["answer"].lower()


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
    assert len(result["sources"]) == 1
    assert result["sources"][0]["text"] == CHUNKS[0]["text"]
    assert "pas assez d'informations" in result["answer"].lower()


# ---------------------------------------------------------------------------
# Tests PRD : chaque source doit être cliquable (url non vide)
# ---------------------------------------------------------------------------

@patch("core.rag.generator.ollama")
def test_sources_ont_url_non_vide(mock_ollama: MagicMock) -> None:
    """PRD: toute réponse RAG DOIT inclure au moins 1 source cliquable (url non vide)."""
    mock_ollama.chat.return_value = _ollama_resp("Bonne analyse [Source 1] [Source 2].", [1, 2], "high")
    result = Generator().generate("question", CHUNKS)
    assert len(result["sources"]) >= 1
    for src in result["sources"]:
        assert src["url"] != "", "Chaque source doit avoir une url cliquable"


@patch("core.rag.generator.ollama")
def test_multi_source_mapping_correct(mock_ollama: MagicMock) -> None:
    """Deux indices de sources différents doivent correspondre aux bons chunks."""
    mock_ollama.chat.return_value = _ollama_resp("Analyse.", [1, 2], "high")
    result = Generator().generate("question", CHUNKS)
    assert len(result["sources"]) == 2
    assert result["sources"][0]["channel"] == "facebook"
    assert result["sources"][1]["channel"] == "google_maps"


# ---------------------------------------------------------------------------
# Tests Sprint 0c — JSON robuste
# ---------------------------------------------------------------------------

def test_extract_json_depuis_bloc_markdown_json() -> None:
    """_extract_json() doit parser un JSON wrappé dans ```json...```."""
    raw = '```json\n{"answer": "OK", "sources": [1], "confidence": "high"}\n```'
    result = Generator._extract_json(raw)
    assert result is not None
    assert result["answer"] == "OK"
    assert result["sources"] == [1]


def test_extract_json_depuis_bloc_markdown_sans_tag() -> None:
    """_extract_json() doit parser un JSON wrappé dans ```...``` (sans 'json')."""
    raw = '```\n{"answer": "Test", "sources": [2], "confidence": "medium"}\n```'
    result = Generator._extract_json(raw)
    assert result is not None
    assert result["answer"] == "Test"
    assert result["confidence"] == "medium"


def test_extract_json_avec_texte_autour() -> None:
    """_extract_json() doit extraire le JSON quand du texte l'entoure."""
    raw = 'Voici ma réponse :\n{"answer": "Extrait", "sources": [1], "confidence": "low"}\nFin.'
    result = Generator._extract_json(raw)
    assert result is not None
    assert result["answer"] == "Extrait"


# ---------------------------------------------------------------------------
# Tests Sprint 0c — Retry avec backoff
# ---------------------------------------------------------------------------

@patch("core.rag.generator.time")
@patch("core.rag.generator.ollama")
def test_retry_3_echecs_consecutifs_retourne_fallback(
    mock_ollama: MagicMock, mock_time: MagicMock
) -> None:
    """3 échecs Ollama consécutifs → fallback retourné après MAX_RETRIES tentatives."""
    mock_ollama.chat.side_effect = ConnectionError("Ollama non disponible")
    result = Generator().generate("question", CHUNKS)
    assert mock_ollama.chat.call_count == 3
    assert mock_time.sleep.call_count == 2  # sleep après tentative 1 et 2, pas après 3
    assert result["confidence"] == "low"
    assert "pas assez d'informations" in result["answer"].lower()
    assert len(result["sources"]) == 1


@patch("core.rag.generator.time")
@patch("core.rag.generator.ollama")
def test_retry_1_echec_puis_succes_retourne_reponse(
    mock_ollama: MagicMock, mock_time: MagicMock
) -> None:
    """1 échec suivi d'un succès → réponse valide retournée à la 2e tentative."""
    mock_ollama.chat.side_effect = [
        ConnectionError("Temporairement indisponible"),
        _ollama_resp("Réponse après retry.", [1], "high"),
    ]
    result = Generator().generate("question", CHUNKS)
    assert mock_ollama.chat.call_count == 2
    assert mock_time.sleep.call_count == 1
    assert "answer" in result
    assert len(result["sources"]) >= 1


# ---------------------------------------------------------------------------
# Tests Sprint 0c — Confidence par similarité
# ---------------------------------------------------------------------------

@patch("core.rag.generator.ollama")
def test_confidence_high_quand_scores_eleves(mock_ollama: MagicMock) -> None:
    """Chunks avec score > 0.7 → confidence 'high', même si LLM retourne 'low'."""
    mock_ollama.chat.return_value = _ollama_resp("Bonne réponse.", [1], "low")
    chunks_high = [
        {"text": "super produit", "channel": "facebook", "url": "http://fb/1",
         "timestamp": "2024-01-01", "score": 0.92},
    ]
    result = Generator().generate("question", chunks_high)
    assert result["confidence"] == "high"


@patch("core.rag.generator.ollama")
def test_confidence_low_quand_scores_faibles(mock_ollama: MagicMock) -> None:
    """Chunks avec score < 0.4 → confidence 'low', même si LLM retourne 'high'."""
    mock_ollama.chat.return_value = _ollama_resp("Réponse.", [1], "high")
    chunks_low = [
        {"text": "produit bof", "channel": "google_maps", "url": "http://gm/1",
         "timestamp": "2024-01-01", "score": 0.15},
    ]
    result = Generator().generate("question", chunks_low)
    assert result["confidence"] == "low"


def test_confidence_medium_sans_cle_score() -> None:
    """_compute_confidence retourne 'medium' si aucun chunk n'a de clé 'score'."""
    chunks_no_score = [
        {"text": "texte A", "channel": "facebook", "url": "http://x"},
        {"text": "texte B", "channel": "youtube", "url": "http://y"},
    ]
    assert Generator._compute_confidence(chunks_no_score) == "medium"
