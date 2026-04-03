"""Shared runtime diagnostics for the hybrid/local/API execution modes."""

from __future__ import annotations

import os
from pathlib import Path

import config

from core.rag.generator import _resolve_backend as _resolve_rag_backend
from core.recommendation.recommendation_manager import get_client_agent_config

_VALID_RUNTIME_MODES = {"local_only", "hybrid", "api_best"}


def _path_has_files(path: Path) -> bool:
    """Return True when the directory exists and is not empty."""
    return path.exists() and path.is_dir() and any(path.iterdir())


def detect_annotation_backend(
    model_path: Path | str | None = None,
    *,
    transformers_available: bool | None = None,
    ollama_available: bool | None = None,
) -> dict:
    """Detect the active annotation backend strategy from local availability."""
    from core.analysis import sentiment_classifier as classifier_module

    resolved_model_path = Path(model_path or config.DZIRIBERT_MODEL_PATH)
    local_model_available = _path_has_files(resolved_model_path)
    if transformers_available is None:
        transformers_available = (
            classifier_module.AutoTokenizer is not None
            and classifier_module.AutoModelForSequenceClassification is not None
        )
    if ollama_available is None:
        ollama_available = classifier_module.ollama is not None

    if local_model_available:
        return {
            "backend_id": "dziribert_local",
            "backend_label": "DziriBERT local",
            "local_model_available": True,
            "fallback_active": False,
            "details": f"Modele local present dans {resolved_model_path}",
        }
    if transformers_available:
        return {
            "backend_id": "dziribert_huggingface_fallback",
            "backend_label": "DziriBERT via HuggingFace",
            "local_model_available": False,
            "fallback_active": True,
            "details": f"Fallback Transformers actif car {resolved_model_path} est vide ou absent",
        }
    if ollama_available:
        return {
            "backend_id": "ollama_zero_shot_fallback",
            "backend_label": "Fallback Ollama zero-shot",
            "local_model_available": False,
            "fallback_active": True,
            "details": "Transformers indisponible, repli Ollama zero-shot",
        }
    return {
        "backend_id": "heuristic_local_fallback",
        "backend_label": "Fallback heuristique locale",
        "local_model_available": False,
        "fallback_active": True,
        "details": "Ni modele local, ni Transformers, ni Ollama disponibles",
    }


def resolve_runtime_mode(
    *,
    explicit_mode: str | None,
    annotation_local_available: bool,
    rag_provider: str,
    recommendation_provider: str,
) -> str:
    """Resolve the explicit runtime mode exposed by the product."""
    normalized_explicit = str(explicit_mode or "").strip().lower()
    if normalized_explicit in _VALID_RUNTIME_MODES:
        return normalized_explicit

    all_generation_local = rag_provider == "ollama_local" and recommendation_provider == "ollama_local"
    any_generation_api = not all_generation_local

    if all_generation_local and annotation_local_available:
        return "local_only"
    if any_generation_api and annotation_local_available:
        return "hybrid"
    if any_generation_api and not annotation_local_available:
        return "api_best"
    return "hybrid"


def _recommendation_backend_status() -> dict:
    """Load the recommendation backend status from persisted client config."""
    config_row = get_client_agent_config(client_id=config.DEFAULT_CLIENT_ID)
    provider = config_row.get("provider") or config.DEFAULT_AGENT_PROVIDER
    model = config_row.get("model") or config.DEFAULT_AGENT_MODEL
    api_configured = provider == "ollama_local" or bool(config_row.get("api_key_encrypted"))
    return {
        "provider": provider,
        "model": model,
        "backend_label": f"Recommendation Agent ({provider} / {model})",
        "api_configured": api_configured,
    }


def _rag_backend_status() -> dict:
    """Read the configured RAG backend and index readiness."""
    provider, model, api_key = _resolve_rag_backend()
    index_prefix = Path(config.FAISS_INDEX_PATH)
    faiss_path = index_prefix.with_suffix(".faiss")
    metadata_path = index_prefix.with_suffix(".json")
    return {
        "provider": provider,
        "model": model,
        "backend_label": f"{provider} / {model}",
        "index_ready": faiss_path.exists() and metadata_path.exists(),
        "api_configured": provider == "ollama_local" or bool(api_key),
        "index_path": str(index_prefix),
    }


def build_runtime_diagnostics(
    *,
    annotation_status: dict,
    rag_status: dict,
    recommendation_status: dict,
    explicit_mode: str | None,
) -> dict:
    """Assemble the full runtime diagnostics structure."""
    mode = resolve_runtime_mode(
        explicit_mode=explicit_mode,
        annotation_local_available=bool(annotation_status.get("local_model_available")),
        rag_provider=str(rag_status.get("provider") or ""),
        recommendation_provider=str(recommendation_status.get("provider") or ""),
    )
    return {
        "mode": mode,
        "annotation": annotation_status,
        "rag": rag_status,
        "recommendation": recommendation_status,
    }


def collect_runtime_diagnostics() -> dict:
    """Collect the current product runtime diagnostics for pages and scripts."""
    annotation_status = detect_annotation_backend()
    rag_status = _rag_backend_status()
    recommendation_status = _recommendation_backend_status()
    explicit_mode = os.getenv("RAMYPULSE_RUNTIME_MODE") or getattr(config, "DEFAULT_RUNTIME_MODE", "")
    return build_runtime_diagnostics(
        annotation_status=annotation_status,
        rag_status=rag_status,
        recommendation_status=recommendation_status,
        explicit_mode=explicit_mode,
    )
