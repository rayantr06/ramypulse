"""Minimal tenant artifact refresh helper."""

from __future__ import annotations

from api.data_loader import load_annotated
from core.tenancy.tenant_paths import get_tenant_paths
from scripts.build_index_04 import build_index


def refresh_tenant_artifacts(client_id: str, force: bool = False) -> dict[str, object]:
    """Refresh tenant artifacts and return a small summary."""
    del force

    paths = get_tenant_paths(client_id)
    paths.processed_dir.mkdir(parents=True, exist_ok=True)
    paths.embeddings_dir.mkdir(parents=True, exist_ok=True)

    dataframe = load_annotated(client_id=client_id, ttl=0)
    annotated_path = paths.annotated_path

    if not dataframe.empty:
        build_index(input_path=annotated_path, embeddings_dir=paths.embeddings_dir)

    return {
        "client_id": client_id,
        "documents": int(len(dataframe)),
        "annotated_path": annotated_path,
        "index_path": paths.faiss_index_prefix,
        "bm25_path": paths.bm25_path,
    }
