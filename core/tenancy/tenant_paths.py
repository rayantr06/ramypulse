"""Tenant-scoped artifact paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import config


@dataclass(frozen=True)
class TenantPaths:
    """Resolved paths for a tenant."""

    tenant_root: Path
    processed_dir: Path
    embeddings_dir: Path
    annotated_path: Path
    faiss_index_prefix: Path
    bm25_path: Path


def get_tenant_paths(client_id: str) -> TenantPaths:
    """Build tenant-scoped paths from a client identifier."""
    tenant_root = Path(config.DATA_DIR) / "tenants" / client_id
    processed_dir = tenant_root / "processed"
    embeddings_dir = tenant_root / "embeddings"
    return TenantPaths(
        tenant_root=tenant_root,
        processed_dir=processed_dir,
        embeddings_dir=embeddings_dir,
        annotated_path=processed_dir / "annotated.parquet",
        faiss_index_prefix=embeddings_dir / "faiss_index",
        bm25_path=embeddings_dir / "bm25.pkl",
    )

