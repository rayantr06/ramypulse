"""Minimal tenant artifact refresh helper."""

from __future__ import annotations

from typing import Callable

from api.data_loader import load_annotated_from_sqlite
from core.tenancy.tenant_paths import get_tenant_paths
from scripts.build_index_04 import build_index


def _clear_tenant_artifacts(paths) -> None:
    """Remove tenant index and parquet artifacts after an empty forced refresh."""
    for candidate in (
        paths.annotated_path,
        paths.faiss_index_prefix.with_suffix(".faiss"),
        paths.faiss_index_prefix.with_suffix(".json"),
        paths.bm25_path,
    ):
        if candidate.exists():
            candidate.unlink()


def refresh_tenant_artifacts(
    client_id: str,
    force: bool = False,
    build_index_fn: Callable[..., object] | None = None,
) -> dict[str, object]:
    """Refresh tenant artifacts and return a small summary."""
    paths = get_tenant_paths(client_id)
    paths.processed_dir.mkdir(parents=True, exist_ok=True)
    paths.embeddings_dir.mkdir(parents=True, exist_ok=True)
    resolved_build_index = build_index_fn or build_index

    dataframe = load_annotated_from_sqlite(client_id=client_id)
    annotated_path = paths.annotated_path

    if dataframe.empty:
        if force:
            _clear_tenant_artifacts(paths)
    else:
        dataframe.to_parquet(annotated_path, index=False)
        resolved_build_index(input_path=annotated_path, embeddings_dir=paths.embeddings_dir)

    return {
        "client_id": client_id,
        "documents": int(len(dataframe)),
        "annotated_path": annotated_path,
        "index_path": paths.faiss_index_prefix,
        "bm25_path": paths.bm25_path,
    }
