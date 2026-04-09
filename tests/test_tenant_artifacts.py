import pandas as pd

from api.data_loader import load_annotated, reset_cache
from core.tenancy.tenant_paths import get_tenant_paths


def test_get_tenant_paths_isolates_processed_and_embeddings(tmp_path, monkeypatch):
    monkeypatch.setattr("config.DATA_DIR", tmp_path)
    paths = get_tenant_paths("tenant-alpha")
    assert paths.annotated_path == tmp_path / "tenants" / "tenant-alpha" / "processed" / "annotated.parquet"
    assert paths.embeddings_dir == tmp_path / "tenants" / "tenant-alpha" / "embeddings"


def test_load_annotated_cache_is_keyed_by_client_id(tmp_path, monkeypatch):
    monkeypatch.setattr("config.SQLITE_DB_PATH", tmp_path / "empty.sqlite")
    monkeypatch.setattr("config.DATA_DIR", tmp_path)
    reset_cache()

    tenant_a = pd.DataFrame([{"text": "alpha", "channel": "web_search"}])
    tenant_b = pd.DataFrame([{"text": "beta", "channel": "youtube"}])

    monkeypatch.setattr(
        "api.data_loader._load_from_sqlite",
        lambda client_id: tenant_a if client_id == "tenant-a" else tenant_b,
    )

    df_a = load_annotated(client_id="tenant-a", ttl=300)
    df_b = load_annotated(client_id="tenant-b", ttl=300)

    assert df_a.iloc[0]["text"] == "alpha"
    assert df_b.iloc[0]["text"] == "beta"

