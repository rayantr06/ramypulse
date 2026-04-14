from __future__ import annotations

import sys
from pathlib import Path

import config

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.recommendation import context_builder
from core.tenancy.tenant_paths import get_tenant_paths


def test_rag_index_prefix_uses_tenant_artifacts_when_client_id_is_provided(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "TENANTS_DIR", tmp_path / "tenants")

    prefix = context_builder._rag_index_prefix("ramy-demo")

    assert prefix == get_tenant_paths("ramy-demo").faiss_index_prefix


def test_rag_index_prefix_falls_back_to_global_when_client_id_is_missing() -> None:
    assert context_builder._rag_index_prefix(None) == Path(config.FAISS_INDEX_PATH)
