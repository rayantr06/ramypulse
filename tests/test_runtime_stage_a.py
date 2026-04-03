"""Stage A runtime diagnostics and local refresh tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.runtime.diagnostics import (
    build_runtime_diagnostics,
    detect_annotation_backend,
    resolve_runtime_mode,
)
from core.runtime.refresh_pipeline import run_local_refresh_pipeline


def test_detect_annotation_backend_prefers_local_model(tmp_path):
    """A non-empty DziriBERT directory should be reported as the primary backend."""
    model_dir = tmp_path / "dziribert"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")

    status = detect_annotation_backend(
        model_dir,
        transformers_available=True,
        ollama_available=True,
    )

    assert status["backend_id"] == "dziribert_local"
    assert status["local_model_available"] is True
    assert status["fallback_active"] is False


def test_resolve_runtime_mode_derives_expected_values():
    """The runtime mode should be explicit and deterministic from the active backends."""
    assert resolve_runtime_mode(
        explicit_mode="local_only",
        annotation_local_available=False,
        rag_provider="google_gemini",
        recommendation_provider="openai",
    ) == "local_only"

    assert resolve_runtime_mode(
        explicit_mode="",
        annotation_local_available=True,
        rag_provider="ollama_local",
        recommendation_provider="ollama_local",
    ) == "local_only"

    assert resolve_runtime_mode(
        explicit_mode="",
        annotation_local_available=True,
        rag_provider="google_gemini",
        recommendation_provider="anthropic",
    ) == "hybrid"

    assert resolve_runtime_mode(
        explicit_mode="",
        annotation_local_available=False,
        rag_provider="google_gemini",
        recommendation_provider="openai",
    ) == "api_best"


def test_build_runtime_diagnostics_sets_mode_and_index_flags():
    """The assembled diagnostics should expose mode, index readiness and backend labels."""
    diagnostics = build_runtime_diagnostics(
        annotation_status={
            "backend_id": "dziribert_local",
            "backend_label": "DziriBERT local",
            "local_model_available": True,
            "fallback_active": False,
        },
        rag_status={
            "provider": "google_gemini",
            "model": "gemini-2.5-flash",
            "backend_label": "Google Gemini (gemini-2.5-flash)",
            "index_ready": True,
            "api_configured": True,
        },
        recommendation_status={
            "provider": "google_gemini",
            "model": "gemini-2.5-flash",
            "backend_label": "Recommendation Agent (google_gemini / gemini-2.5-flash)",
            "api_configured": True,
        },
        explicit_mode="",
    )

    assert diagnostics["mode"] == "hybrid"
    assert diagnostics["annotation"]["backend_label"] == "DziriBERT local"
    assert diagnostics["rag"]["index_ready"] is True
    assert diagnostics["recommendation"]["api_configured"] is True


def test_run_local_refresh_pipeline_calls_steps_in_order(tmp_path):
    """The local refresh pipeline should orchestrate the 4 batch stages in order."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    embeddings_dir = tmp_path / "embeddings"
    call_order: list[str] = []

    def collect_fn(*, raw_dir: Path, demo_dir: Path) -> Path:
        call_order.append("collect")
        raw_dir.mkdir(parents=True, exist_ok=True)
        output = raw_dir / "collected_raw.parquet"
        pd.DataFrame([{"text": "raw"}]).to_parquet(output, index=False)
        return output

    def process_fn(*, raw_dir: Path, output_path: Path) -> pd.DataFrame:
        call_order.append("process")
        dataframe = pd.DataFrame([{"text": "clean"}])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_parquet(output_path, index=False)
        return dataframe

    def classify_fn(*, input_path: Path, output_path: Path, catalog_db_path: Path | None) -> pd.DataFrame:
        call_order.append("classify")
        dataframe = pd.DataFrame([{"text": "annotated", "sentiment_label": "positif"}])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_parquet(output_path, index=False)
        return dataframe

    def build_index_fn(*, input_path: Path, embeddings_dir: Path) -> Path:
        call_order.append("index")
        embeddings_dir.mkdir(parents=True, exist_ok=True)
        index_path = embeddings_dir / "faiss_index.faiss"
        index_path.write_text("ok", encoding="utf-8")
        return index_path

    summary = run_local_refresh_pipeline(
        collect_fn=collect_fn,
        process_fn=process_fn,
        classify_fn=classify_fn,
        build_index_fn=build_index_fn,
        raw_dir=raw_dir,
        demo_dir=tmp_path / "demo",
        processed_dir=processed_dir,
        embeddings_dir=embeddings_dir,
        catalog_db_path=tmp_path / "catalog.db",
    )

    assert call_order == ["collect", "process", "classify", "index"]
    assert summary["artifacts"]["raw"].name == "collected_raw.parquet"
    assert summary["artifacts"]["clean"].name == "clean.parquet"
    assert summary["artifacts"]["annotated"].name == "annotated.parquet"
    assert summary["artifacts"]["index"].name == "faiss_index.faiss"
    assert summary["rows"]["clean"] == 1
    assert summary["rows"]["annotated"] == 1
