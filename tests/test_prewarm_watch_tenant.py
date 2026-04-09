from __future__ import annotations

from types import SimpleNamespace

import pytest

import config
from scripts import prewarm_watch_tenant


def test_prewarm_watch_tenant_updates_existing_watchlist_and_runs_inline(
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "SAFE_EXPO_CLIENT_ID", "ramy-demo", raising=False)

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        prewarm_watch_tenant,
        "get_or_create_client",
        lambda **kwargs: {"client_id": kwargs["client_id"], "client_name": kwargs["client_name"]},
    )
    monkeypatch.setattr(
        prewarm_watch_tenant,
        "set_active_client",
        lambda client_id: captured.setdefault("active_client_id", client_id),
    )
    monkeypatch.setattr(
        prewarm_watch_tenant,
        "list_watchlists",
        lambda is_active=False: [
            {
                "watchlist_id": "watch-existing",
                "client_id": "ramy-demo",
                "watchlist_name": "Ramy Expo Watch",
            }
        ],
    )

    def _fake_update_watchlist(watchlist_id: str, payload: dict[str, object]) -> bool:
        captured["updated_watchlist"] = {"watchlist_id": watchlist_id, "payload": payload}
        return True

    monkeypatch.setattr(prewarm_watch_tenant, "update_watchlist", _fake_update_watchlist)
    monkeypatch.setattr(
        prewarm_watch_tenant,
        "create_watchlist",
        lambda **kwargs: pytest.fail("create_watchlist should not be called when the watchlist already exists"),
    )

    def _fake_start_watch_run(**kwargs):
        captured["watch_run"] = kwargs
        return {"run_id": "run-001", "status": "ready"}

    monkeypatch.setattr(prewarm_watch_tenant, "start_watch_run", _fake_start_watch_run)
    monkeypatch.setattr(
        prewarm_watch_tenant,
        "load_annotated_from_sqlite",
        lambda **kwargs: [object()] * 64,
    )
    monkeypatch.setattr(
        prewarm_watch_tenant,
        "get_tenant_paths",
        lambda client_id: SimpleNamespace(
            annotated_path=f"data/tenants/{client_id}/processed/annotated.parquet",
            faiss_index_prefix=f"data/tenants/{client_id}/embeddings/faiss_index",
        ),
    )

    summary = prewarm_watch_tenant.prewarm_watch_tenant(
        client_id="ramy-demo",
        client_name="Ramy Demo",
        brand_name="Ramy",
        product_name="Jus",
        keywords=["ramy", "jus"],
        seed_urls=["https://example.com/ramy"],
        channels=["public_url_seed", "web_search"],
        min_docs=50,
    )

    assert captured["active_client_id"] == "ramy-demo"
    assert captured["updated_watchlist"]["watchlist_id"] == "watch-existing"
    assert captured["watch_run"]["client_id"] == "ramy-demo"
    assert captured["watch_run"]["run_async"] is False
    assert captured["watch_run"]["requested_channels"] == ["public_url_seed", "web_search"]
    assert summary["documents"] == 64
    assert summary["watchlist_id"] == "watch-existing"


def test_prewarm_watch_tenant_fails_when_document_threshold_is_not_met(
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "SAFE_EXPO_CLIENT_ID", "ramy-demo", raising=False)
    monkeypatch.setattr(
        prewarm_watch_tenant,
        "get_or_create_client",
        lambda **kwargs: {"client_id": kwargs["client_id"], "client_name": kwargs["client_name"]},
    )
    monkeypatch.setattr(prewarm_watch_tenant, "set_active_client", lambda client_id: None)
    monkeypatch.setattr(prewarm_watch_tenant, "list_watchlists", lambda is_active=False: [])
    monkeypatch.setattr(prewarm_watch_tenant, "create_watchlist", lambda **kwargs: "watch-new")
    monkeypatch.setattr(
        prewarm_watch_tenant,
        "start_watch_run",
        lambda **kwargs: {"run_id": "run-002", "status": "partial_success"},
    )
    monkeypatch.setattr(
        prewarm_watch_tenant,
        "load_annotated_from_sqlite",
        lambda **kwargs: [object()] * 12,
    )
    monkeypatch.setattr(
        prewarm_watch_tenant,
        "get_tenant_paths",
        lambda client_id: SimpleNamespace(
            annotated_path=f"data/tenants/{client_id}/processed/annotated.parquet",
            faiss_index_prefix=f"data/tenants/{client_id}/embeddings/faiss_index",
        ),
    )

    with pytest.raises(RuntimeError, match="at least 50 documents"):
        prewarm_watch_tenant.prewarm_watch_tenant(
            client_id="ramy-demo",
            client_name="Ramy Demo",
            brand_name="Ramy",
            min_docs=50,
        )
