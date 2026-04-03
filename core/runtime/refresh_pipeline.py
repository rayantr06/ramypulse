"""Local batch refresh orchestration for the RamyPulse pipeline."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Callable

import config


def _load_script_module(filename: str) -> ModuleType:
    """Load a script module by filename from the scripts directory."""
    scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
    script_path = scripts_dir / filename
    module_name = f"runtime_loader_{script_path.stem.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _default_collect_fn() -> Callable[..., Path]:
    """Return the default collect step callable."""
    return _load_script_module("01_collect_data.py").main


def _default_process_fn() -> Callable[..., object]:
    """Return the default process step callable."""
    return _load_script_module("process_data_02.py").process_data


def _default_classify_fn() -> Callable[..., object]:
    """Return the default classify step callable."""
    return _load_script_module("classify_sentiment_03.py").classify_sentiment


def _default_build_index_fn() -> Callable[..., object]:
    """Return the default build-index step callable."""
    return _load_script_module("build_index_04.py").build_index


def run_local_refresh_pipeline(
    *,
    collect_fn: Callable[..., Path] | None = None,
    process_fn: Callable[..., object] | None = None,
    classify_fn: Callable[..., object] | None = None,
    build_index_fn: Callable[..., object] | None = None,
    raw_dir: Path | None = None,
    demo_dir: Path | None = None,
    processed_dir: Path | None = None,
    embeddings_dir: Path | None = None,
    catalog_db_path: Path | None = None,
) -> dict:
    """Run the 4-stage local refresh pipeline and return a structured summary."""
    raw_dir = Path(raw_dir) if raw_dir is not None else config.RAW_DATA_DIR
    demo_dir = Path(demo_dir) if demo_dir is not None else config.DEMO_DATA_DIR
    processed_dir = Path(processed_dir) if processed_dir is not None else config.PROCESSED_DATA_DIR
    embeddings_dir = Path(embeddings_dir) if embeddings_dir is not None else config.EMBEDDINGS_DIR
    catalog_db_path = Path(catalog_db_path) if catalog_db_path is not None else Path(config.SQLITE_DB_PATH)

    clean_path = processed_dir / "clean.parquet"
    annotated_path = processed_dir / "annotated.parquet"

    collect = collect_fn or _default_collect_fn()
    process = process_fn or _default_process_fn()
    classify = classify_fn or _default_classify_fn()
    build_index = build_index_fn or _default_build_index_fn()

    raw_path = Path(collect(raw_dir=raw_dir, demo_dir=demo_dir))
    clean_df = process(raw_dir=raw_dir, output_path=clean_path)
    annotated_df = classify(input_path=clean_path, output_path=annotated_path, catalog_db_path=catalog_db_path)
    maybe_index_path = build_index(input_path=annotated_path, embeddings_dir=embeddings_dir)
    index_path = Path(maybe_index_path) if maybe_index_path else embeddings_dir / "faiss_index.faiss"

    return {
        "artifacts": {
            "raw": raw_path,
            "clean": clean_path,
            "annotated": annotated_path,
            "index": index_path,
        },
        "rows": {
            "clean": int(len(clean_df)) if hasattr(clean_df, "__len__") else 0,
            "annotated": int(len(annotated_df)) if hasattr(annotated_df, "__len__") else 0,
        },
    }
