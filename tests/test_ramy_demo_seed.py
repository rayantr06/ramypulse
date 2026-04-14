from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

import config

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tenancy.tenant_paths import get_tenant_paths
from core.tenancy.client_manager import get_active_client
from core.demo.ramy_seed import (
    issue_demo_api_key,
    load_ramy_seed_dataset,
    seed_ramy_demo,
    write_frontend_env_file,
)


def _write_seed_csv(path: Path) -> Path:
    rows = [
        {
            "text": "لقاوها تسقي المزرعة بمياه الصرف الصحي",
            "sentiment": "negative",
            "confidence": 0.95,
            "prob_positive": 0.01,
            "prob_negative": 0.95,
            "prob_neutral": 0.02,
            "prob_mixed": 0.02,
            "brand": "Ramy",
            "platform": "facebook",
            "date": "2026-03-01T21:50:17.000Z",
            "likes": 2,
            "author": "Auteur 1",
            "post_url": "https://www.facebook.com/reel/ramy-001/",
            "is_reply": False,
        },
        {
            "text": "الطعم زوين بصح السعر غالي",
            "sentiment": "negative",
            "confidence": 0.91,
            "prob_positive": 0.03,
            "prob_negative": 0.88,
            "prob_neutral": 0.06,
            "prob_mixed": 0.03,
            "brand": "Ramy",
            "platform": "facebook",
            "date": "2026-03-12T10:00:00.000Z",
            "likes": 8,
            "author": "Auteur 2",
            "post_url": "https://www.facebook.com/reel/ramy-002/",
            "is_reply": False,
        },
        {
            "text": "Ramy dispo partout aujourd'hui",
            "sentiment": "neutral",
            "confidence": 0.83,
            "prob_positive": 0.1,
            "prob_negative": 0.07,
            "prob_neutral": 0.79,
            "prob_mixed": 0.04,
            "brand": "Ramy",
            "platform": "facebook",
            "date": "2026-03-25T09:10:00.000Z",
            "likes": 1,
            "author": "Auteur 3",
            "post_url": "https://www.facebook.com/ramy.jus/posts/ramy-003/",
            "is_reply": False,
        },
        {
            "text": "Ramy est revenu, tres bon jus",
            "sentiment": "positive",
            "confidence": 0.89,
            "prob_positive": 0.9,
            "prob_negative": 0.03,
            "prob_neutral": 0.05,
            "prob_mixed": 0.02,
            "brand": "Ramy",
            "platform": "facebook",
            "date": "2026-04-03T11:30:00.000Z",
            "likes": 11,
            "author": "Auteur 4",
            "post_url": "https://www.facebook.com/ramy.jus/posts/ramy-004/",
            "is_reply": False,
        },
        {
            "text": "Hamoud est meilleur",
            "sentiment": "positive",
            "confidence": 0.77,
            "prob_positive": 0.7,
            "prob_negative": 0.1,
            "prob_neutral": 0.15,
            "prob_mixed": 0.05,
            "brand": "Hamoud Boualem",
            "platform": "facebook",
            "date": "2026-04-03T11:35:00.000Z",
            "likes": 7,
            "author": "Auteur 5",
            "post_url": "https://www.facebook.com/reel/hamoud-001/",
            "is_reply": False,
        },
    ]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_load_ramy_seed_dataset_filters_brand_and_parses_dates(tmp_path: Path) -> None:
    csv_path = _write_seed_csv(tmp_path / "dataset.csv")

    dataframe = load_ramy_seed_dataset(csv_path)

    assert len(dataframe) == 4
    assert dataframe["brand"].str.lower().unique().tolist() == ["ramy"]
    assert "timestamp" in dataframe.columns
    assert dataframe["timestamp"].notna().all()


def test_seed_ramy_demo_populates_core_tables_and_sets_active_client(
    tmp_path: Path,
    monkeypatch,
) -> None:
    csv_path = _write_seed_csv(tmp_path / "dataset.csv")
    db_path = tmp_path / "ramy-demo.sqlite"

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "TENANTS_DIR", tmp_path / "tenants")
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path)
    monkeypatch.setattr(config, "SAFE_EXPO_CLIENT_ID", "ramy-demo", raising=False)

    captured: dict[str, object] = {}

    def _fake_refresh(*, client_id: str, force: bool = False, build_index_fn=None):
        tenant_paths = get_tenant_paths(client_id)
        tenant_paths.annotated_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"text": "snapshot", "channel": "facebook"}]).to_parquet(
            tenant_paths.annotated_path,
            index=False,
        )
        captured["refresh"] = {
            "client_id": client_id,
            "force": force,
        }
        return {
            "client_id": client_id,
            "documents": 4,
            "annotated_path": tenant_paths.annotated_path,
            "index_path": tenant_paths.faiss_index_prefix,
            "bm25_path": tenant_paths.bm25_path,
        }

    summary = seed_ramy_demo(
        csv_path=csv_path,
        client_id="ramy-demo",
        reset=True,
        refresh_artifacts_fn=_fake_refresh,
    )

    assert summary["client_id"] == "ramy-demo"
    assert summary["documents_seeded"] == 4
    assert summary["watchlists_count"] >= 3
    assert summary["sources_count"] >= 3
    assert captured["refresh"] == {"client_id": "ramy-demo", "force": True}
    assert get_active_client()["client_id"] == "ramy-demo"

    with sqlite3.connect(db_path) as connection:
        raw_count = connection.execute(
            "SELECT COUNT(*) FROM raw_documents WHERE client_id = ?",
            ("ramy-demo",),
        ).fetchone()[0]
        normalized_count = connection.execute(
            "SELECT COUNT(*) FROM normalized_records WHERE client_id = ?",
            ("ramy-demo",),
        ).fetchone()[0]
        enriched_count = connection.execute(
            "SELECT COUNT(*) FROM enriched_signals WHERE client_id = ?",
            ("ramy-demo",),
        ).fetchone()[0]
        alerts_count = connection.execute(
            "SELECT COUNT(*) FROM alerts WHERE client_id = ?",
            ("ramy-demo",),
        ).fetchone()[0]
        recommendations_count = connection.execute(
            "SELECT COUNT(*) FROM recommendations WHERE client_id = ?",
            ("ramy-demo",),
        ).fetchone()[0]
        agent_provider, agent_model = connection.execute(
            "SELECT provider, model FROM client_agent_config WHERE client_id = ?",
            ("ramy-demo",),
        ).fetchone()

    assert raw_count == 4
    assert normalized_count == 4
    assert enriched_count == 4
    assert alerts_count == summary["alerts_created"]
    assert recommendations_count == summary["recommendations_created"]
    assert agent_provider == config.DEFAULT_AGENT_PROVIDER
    assert agent_model == config.DEFAULT_AGENT_MODEL


def test_issue_demo_api_key_and_write_frontend_env_file(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "ramy-demo.sqlite"

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "TENANTS_DIR", tmp_path / "tenants")
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path)
    monkeypatch.setattr(config, "SAFE_EXPO_CLIENT_ID", "ramy-demo", raising=False)

    seed_ramy_demo(
        csv_path=_write_seed_csv(tmp_path / "dataset.csv"),
        client_id="ramy-demo",
        reset=True,
        refresh_artifacts_fn=lambda **kwargs: {
            "client_id": "ramy-demo",
            "documents": 4,
            "annotated_path": get_tenant_paths("ramy-demo").annotated_path,
            "index_path": get_tenant_paths("ramy-demo").faiss_index_prefix,
            "bm25_path": get_tenant_paths("ramy-demo").bm25_path,
        },
    )

    first_key = issue_demo_api_key(client_id="ramy-demo")
    second_key = issue_demo_api_key(client_id="ramy-demo")

    assert first_key["api_key"].startswith("rpk_")
    assert second_key["api_key"].startswith("rpk_")
    assert first_key["api_key"] != second_key["api_key"]

    env_path = write_frontend_env_file(
        api_key=second_key["api_key"],
        client_id="ramy-demo",
        env_path=tmp_path / ".env.local",
    )
    content = env_path.read_text(encoding="utf-8")
    assert "VITE_RAMYPULSE_API_KEY=" in content
    assert "VITE_SAFE_EXPO_CLIENT_ID=ramy-demo" in content


def test_seed_ramy_demo_reset_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    csv_path = _write_seed_csv(tmp_path / "dataset.csv")
    db_path = tmp_path / "ramy-demo.sqlite"

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "TENANTS_DIR", tmp_path / "tenants")
    monkeypatch.setattr(config, "SQLITE_DB_PATH", db_path)
    monkeypatch.setattr(config, "SAFE_EXPO_CLIENT_ID", "ramy-demo", raising=False)

    def _fake_refresh(*, client_id: str, force: bool = False, build_index_fn=None):
        return {
            "client_id": client_id,
            "documents": 4,
            "annotated_path": get_tenant_paths(client_id).annotated_path,
            "index_path": get_tenant_paths(client_id).faiss_index_prefix,
            "bm25_path": get_tenant_paths(client_id).bm25_path,
        }

    seed_ramy_demo(
        csv_path=csv_path,
        client_id="ramy-demo",
        reset=True,
        refresh_artifacts_fn=_fake_refresh,
    )
    seed_ramy_demo(
        csv_path=csv_path,
        client_id="ramy-demo",
        reset=True,
        refresh_artifacts_fn=_fake_refresh,
    )

    with sqlite3.connect(db_path) as connection:
        raw_count = connection.execute(
            "SELECT COUNT(*) FROM raw_documents WHERE client_id = ?",
            ("ramy-demo",),
        ).fetchone()[0]
        source_count = connection.execute(
            "SELECT COUNT(*) FROM sources WHERE client_id = ?",
            ("ramy-demo",),
        ).fetchone()[0]

    assert raw_count == 4
    assert source_count >= 3
