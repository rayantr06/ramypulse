# Five-Source Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finaliser le socle d'ingestion modulaire pour `facebook`, `google_maps`, `youtube`, `instagram` et `import`, avec onboarding admin, secrets par référence, sync tenant-safe, health snapshots et traçabilité source -> raw -> normalized -> enriched.

**Architecture:** On part du socle déjà présent dans `integration/wave5` et on le durcit au lieu de le réécrire. Le travail est centré sur un helper de config source partagé, un contrat connecteur explicite, l'ajout d'Instagram comme cinquième source, puis l'admin source complète branchée sur l'orchestrateur et le secret manager. La normalisation existante reste la voie unique vers `normalized_records` et `enriched_signals`.

**Tech Stack:** Python 3.11, SQLite, pandas, Streamlit, pytest, logging, local secret manager

---

## File Map

- `core/connectors/base_connector.py`
  - Contrat abstrait commun des connecteurs.
- `core/connectors/source_config.py`
  - Nouveau helper partagé pour parser, valider et enrichir `config_json`.
- `core/connectors/batch_import_connector.py`
  - Connecteur `import` fondé sur `ImportEngine`.
- `core/connectors/platform_snapshot_connector.py`
  - Base concrète pour `facebook`, `google_maps`, `youtube`, `instagram`.
- `core/connectors/facebook_connector.py`
  - Connecteur Facebook.
- `core/connectors/google_maps_connector.py`
  - Connecteur Google Maps.
- `core/connectors/youtube_connector.py`
  - Connecteur YouTube.
- `core/connectors/instagram_connector.py`
  - Nouveau connecteur Instagram.
- `core/ingestion/orchestrator.py`
  - Sélection connecteur, ouverture/fermeture des sync runs, insertion `raw_documents`, déclenchement normalisation.
- `core/ingestion/source_admin_service.py`
  - Vue admin sur `sources`, `source_sync_runs`, `source_health_snapshots` et helpers d'édition.
- `core/ingestion/health_checker.py`
  - Calcul et persistance de la santé source.
- `core/security/secret_manager.py`
  - Stockage et résolution des secrets par référence.
- `pages/09_admin_sources.py`
  - Cockpit admin des cinq sources.
- `ui_helpers/source_admin_helpers.py`
  - Tables et métriques UI pour l'admin sources.
- `tests/test_source_config.py`
  - Nouveau lot unitaire pour la config source partagée.
- `tests/test_source_platform_admin.py`
  - Couverture intégration orchestrateur/service/admin plateforme.
- `tests/test_admin_sources_page.py`
  - Couverture des helpers/tableaux UI admin.
- `tests/test_platform_foundation.py`
  - Régression fondation plateforme et tables SQLite.

### Task 1: Ajouter un helper de config source partagé

**Files:**
- Create: `g:/ramypulse-s0-verify/core/connectors/source_config.py`
- Modify: `g:/ramypulse-s0-verify/core/connectors/base_connector.py`
- Test: `g:/ramypulse-s0-verify/tests/test_source_config.py`

- [ ] **Step 1: Write the failing test**

```python
from core.connectors.source_config import parse_source_config, validate_source_config


def test_validate_source_config_refuse_facebook_sans_page() -> None:
    source = {
        "platform": "facebook",
        "config_json": {"fetch_mode": "snapshot"},
    }

    try:
        validate_source_config(source)
    except ValueError as exc:
        assert "page_id" in str(exc) or "page_url" in str(exc)
    else:
        raise AssertionError("validate_source_config aurait dû lever ValueError")


def test_parse_source_config_retourne_un_dict_normalise() -> None:
    source = {
        "platform": "import",
        "config_json": "{\"snapshot_path\": \"data/raw/import.csv\", \"fetch_mode\": \"snapshot\"}",
    }

    config = parse_source_config(source)

    assert config["snapshot_path"] == "data/raw/import.csv"
    assert config["fetch_mode"] == "snapshot"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_source_config.py -v`
Expected: FAIL with `ModuleNotFoundError` on `core.connectors.source_config`

- [ ] **Step 3: Write minimal implementation**

```python
import json


_REQUIRED_FIELDS = {
    "facebook": (("page_id", "page_url"),),
    "google_maps": (("place_id", "place_url"),),
    "youtube": (("channel_id", "video_ids"),),
    "instagram": (("profile_id", "profile_url"),),
    "import": (("snapshot_path",),),
}


def parse_source_config(source: dict) -> dict:
    raw_config = source.get("config_json") or {}
    if isinstance(raw_config, dict):
        return dict(raw_config)
    if isinstance(raw_config, str) and raw_config.strip():
        parsed = json.loads(raw_config)
        return parsed if isinstance(parsed, dict) else {}
    return {}


def validate_source_config(source: dict) -> dict:
    config = parse_source_config(source)
    platform = str(source.get("platform") or "").strip()
    required_groups = _REQUIRED_FIELDS.get(platform, ())

    for group in required_groups:
        if not any(config.get(field) for field in group):
            raise ValueError(f"Configuration {platform} invalide: un de {group} est requis")

    fetch_mode = str(config.get("fetch_mode") or "snapshot")
    if fetch_mode not in {"snapshot", "collector", "api"}:
        raise ValueError(f"fetch_mode non supporté: {fetch_mode}")

    config["fetch_mode"] = fetch_mode
    return config
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_source_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/connectors/source_config.py core/connectors/base_connector.py tests/test_source_config.py
git commit -m "feat(ingestion): add shared source config validation"
```

### Task 2: Durcir le contrat connecteur et brancher Instagram

**Files:**
- Create: `g:/ramypulse-s0-verify/core/connectors/instagram_connector.py`
- Modify: `g:/ramypulse-s0-verify/core/connectors/base_connector.py`
- Modify: `g:/ramypulse-s0-verify/core/connectors/platform_snapshot_connector.py`
- Modify: `g:/ramypulse-s0-verify/core/connectors/batch_import_connector.py`
- Test: `g:/ramypulse-s0-verify/tests/test_source_platform_admin.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

import pandas as pd

from core.connectors.instagram_connector import InstagramConnector
from core.connectors.facebook_connector import FacebookConnector


def test_instagram_connector_charge_un_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "instagram.parquet"
    pd.DataFrame(
        [
            {
                "review": "ramy instagram tres bon",
                "channel": "instagram",
                "timestamp": "2026-04-03T10:00:00",
                "source_url": "https://example.test/instagram/1",
            }
        ]
    ).to_parquet(snapshot)

    connector = InstagramConnector()
    source = {
        "source_id": "src-instagram-001",
        "client_id": "client-instagram",
        "source_name": "Instagram Ramy",
        "platform": "instagram",
        "source_type": "instagram_profile",
        "owner_type": "owned",
        "config_json": {"snapshot_path": str(snapshot), "profile_url": "https://instagram.com/ramy"},
    }

    documents = connector.fetch_documents(source)

    assert len(documents) == 1
    assert documents[0]["raw_metadata"]["channel"] == "instagram"


def test_facebook_connector_utilise_le_mode_collector(monkeypatch) -> None:
    connector = FacebookConnector()
    source = {
        "source_id": "src-facebook-collector",
        "client_id": "client-facebook",
        "source_name": "Facebook Ramy",
        "platform": "facebook",
        "source_type": "facebook_page",
        "owner_type": "owned",
        "config_json": {"page_url": "https://facebook.com/ramy", "fetch_mode": "collector"},
    }

    monkeypatch.setattr(
        connector,
        "_load_from_snapshots",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        connector,
        "_load_from_scraper",
        lambda *args, **kwargs: [
            {
                "external_document_id": "fb-1",
                "raw_text": "ramy collector",
                "raw_payload": {"text": "ramy collector"},
                "raw_metadata": {"channel": "facebook", "source_id": "src-facebook-collector"},
                "collected_at": "2026-04-03T10:00:00",
                "checksum_sha256": "abc",
            }
        ],
    )

    documents = connector.fetch_documents(source)

    assert len(documents) == 1
    assert documents[0]["external_document_id"] == "fb-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_source_platform_admin.py::test_instagram_connector_charge_un_snapshot -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` on `instagram_connector`

- [ ] **Step 3: Write minimal implementation**

```python
from core.connectors.platform_snapshot_connector import SnapshotPlatformConnector


class InstagramConnector(SnapshotPlatformConnector):
    """Connecteur Instagram via snapshot local ou collecteur optionnel."""

    def __init__(self) -> None:
        super().__init__(
            platform="instagram",
            default_snapshot_names=("instagram_raw.parquet",),
            scraper_modules=("core.ingestion.scraper_instagram",),
        )
```

```python
class BaseConnector(ABC):
    def validate_source_config(self, source: dict) -> dict:
        return validate_source_config(source)

    def resolve_runtime_inputs(self, source: dict, *, credentials: dict | None = None, **kwargs) -> dict:
        return {"config": parse_source_config(source), "credentials": credentials or {}, **kwargs}

    def health_hints(self, source: dict, *, last_run: dict | None = None) -> dict:
        return {"platform": source.get("platform"), "last_run_status": (last_run or {}).get("status")}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_source_platform_admin.py -k \"instagram or collector\" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/connectors/base_connector.py core/connectors/platform_snapshot_connector.py core/connectors/batch_import_connector.py core/connectors/instagram_connector.py tests/test_source_platform_admin.py
git commit -m "feat(ingestion): add instagram connector and explicit connector contract"
```

### Task 3: Brancher les secrets par référence dans l'onboarding et les syncs

**Files:**
- Modify: `g:/ramypulse-s0-verify/core/connectors/source_config.py`
- Modify: `g:/ramypulse-s0-verify/core/ingestion/orchestrator.py`
- Modify: `g:/ramypulse-s0-verify/core/security/secret_manager.py`
- Modify: `g:/ramypulse-s0-verify/tests/test_source_platform_admin.py`
- Modify: `g:/ramypulse-s0-verify/tests/test_platform_foundation.py`

- [ ] **Step 1: Write the failing test**

```python
from core.connectors.source_config import materialize_secret_reference
from core.security.secret_manager import resolve_secret


def test_materialize_secret_reference_ne_stocke_pas_le_secret_brut() -> None:
    config = {"fetch_mode": "collector"}

    updated = materialize_secret_reference(config, secret_value="super-secret-token", label="facebook-collector")

    assert "super-secret-token" not in str(updated)
    assert updated["credential_ref"].startswith("secret://")
    assert resolve_secret(updated["credential_ref"]) == "super-secret-token"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_source_platform_admin.py -k secret_reference -v`
Expected: FAIL with `ImportError` on `materialize_secret_reference`

- [ ] **Step 3: Write minimal implementation**

```python
from core.security.secret_manager import store_secret, resolve_secret


def materialize_secret_reference(config: dict, *, secret_value: str | None, label: str | None) -> dict:
    updated = dict(config)
    reference = store_secret(secret_value, label=label)
    if reference:
        updated["credential_ref"] = reference
    return updated


def resolve_credentials(config: dict) -> dict:
    credential_ref = config.get("credential_ref")
    token = resolve_secret(credential_ref)
    return {"token": token} if token else {}
```

```python
credentials_payload = credentials or resolve_credentials(parse_source_config(source))
documents = connector.fetch_documents(
    source,
    credentials=credentials_payload,
    file_path=manual_file_path,
    column_mapping=column_mapping,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_source_platform_admin.py tests/test_platform_foundation.py -k secret -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/connectors/source_config.py core/ingestion/orchestrator.py core/security/secret_manager.py tests/test_source_platform_admin.py tests/test_platform_foundation.py
git commit -m "feat(ingestion): resolve source credentials via secret references"
```

### Task 4: Finaliser l'orchestrateur tenant-safe et la trace de run

**Files:**
- Modify: `g:/ramypulse-s0-verify/core/ingestion/orchestrator.py`
- Modify: `g:/ramypulse-s0-verify/core/normalization/normalizer_pipeline.py`
- Modify: `g:/ramypulse-s0-verify/core/ingestion/health_checker.py`
- Test: `g:/ramypulse-s0-verify/tests/test_platform_foundation.py`
- Test: `g:/ramypulse-s0-verify/tests/test_source_platform_admin.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_source_sync_preserve_raw_documents_si_normalization_echoue(
    monkeypatch,
    platform_db,
    tmp_path,
) -> None:
    from core.ingestion.orchestrator import IngestionOrchestrator

    csv_path = tmp_path / "import_single.csv"
    csv_path.write_text("text,channel,timestamp\nramy tres bon,import,2026-04-03T10:00:00\n", encoding="utf-8")

    orchestrator = IngestionOrchestrator(db_path=str(platform_db))
    source = orchestrator.create_source(
        {
            "client_id": "client-preserve",
            "source_name": "Import preserve",
            "platform": "import",
            "source_type": "batch_import",
            "owner_type": "owned",
            "config_json": {"snapshot_path": str(csv_path)},
        }
    )

    monkeypatch.setattr(
        "core.ingestion.orchestrator.run_normalization_job",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("normalization down")),
    )

    result = orchestrator.run_source_sync(source["source_id"], manual_file_path=str(csv_path), client_id="client-preserve")

    assert result["status"] == "failed_downstream"
    assert result["records_inserted"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_platform_foundation.py -k preserve_raw_documents -v`
Expected: FAIL because current orchestrator returns generic `success` or raises

- [ ] **Step 3: Write minimal implementation**

```python
try:
    normalization_result = run_normalization_job(
        db_path=self.db_path,
        client_id=source.get("client_id"),
    )
except Exception as exc:
    self._finish_sync_run(
        sync_run_id,
        status="failed_downstream",
        records_fetched=len(documents),
        records_inserted=inserted,
        records_failed=0,
        error_message=str(exc),
    )
    return {
        "sync_run_id": sync_run_id,
        "status": "failed_downstream",
        "records_fetched": len(documents),
        "records_inserted": inserted,
        "records_failed": 0,
        "normalization_error": str(exc),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_platform_foundation.py tests/test_source_platform_admin.py -k \"preserve_raw_documents or client_id_etranger\" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/ingestion/orchestrator.py core/normalization/normalizer_pipeline.py core/ingestion/health_checker.py tests/test_platform_foundation.py tests/test_source_platform_admin.py
git commit -m "fix(ingestion): preserve raw documents and explicit downstream failure states"
```

### Task 5: Finaliser l'admin sources pour les cinq plateformes

**Files:**
- Modify: `g:/ramypulse-s0-verify/core/ingestion/source_admin_service.py`
- Modify: `g:/ramypulse-s0-verify/pages/09_admin_sources.py`
- Modify: `g:/ramypulse-s0-verify/ui_helpers/source_admin_helpers.py`
- Test: `g:/ramypulse-s0-verify/tests/test_admin_sources_page.py`

- [ ] **Step 1: Write the failing test**

```python
from ui_helpers.source_admin_helpers import build_sources_frame


def test_build_sources_frame_affiche_fetch_mode_et_credential_ref() -> None:
    rows = [
        {
            "source_id": "src-instagram-001",
            "source_name": "Instagram Ramy",
            "platform": "instagram",
            "owner_type": "owned",
            "is_active": 1,
            "config_json": {"fetch_mode": "collector", "credential_ref": "secret://instagram-001"},
            "last_sync_status": "success",
            "latest_health_score": 92.0,
            "raw_document_count": 12,
            "normalized_count": 12,
            "enriched_count": 12,
        }
    ]

    frame = build_sources_frame(rows)

    assert "fetch_mode" in frame.columns
    assert "credential_ref" in frame.columns
    assert frame.iloc[0]["fetch_mode"] == "collector"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_admin_sources_page.py -k fetch_mode -v`
Expected: FAIL because helper does not yet expose these columns

- [ ] **Step 3: Write minimal implementation**

```python
def build_sources_frame(records: list[dict]) -> pd.DataFrame:
    rows = []
    for record in records:
        config = record.get("config_json") or {}
        rows.append(
            {
                "source_name": record.get("source_name"),
                "platform": record.get("platform"),
                "owner_type": record.get("owner_type"),
                "is_active": bool(record.get("is_active")),
                "fetch_mode": config.get("fetch_mode", "snapshot"),
                "credential_ref": config.get("credential_ref"),
                "last_sync_status": record.get("last_sync_status"),
                "latest_health_score": record.get("latest_health_score"),
                "raw_document_count": record.get("raw_document_count", 0),
                "normalized_count": record.get("normalized_count", 0),
                "enriched_count": record.get("enriched_count", 0),
            }
        )
    return pd.DataFrame(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_admin_sources_page.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/ingestion/source_admin_service.py pages/09_admin_sources.py ui_helpers/source_admin_helpers.py tests/test_admin_sources_page.py
git commit -m "feat(admin): finalize five-source onboarding and source observability"
```

### Task 6: Vérification bout en bout des cinq sources

**Files:**
- Modify: `g:/ramypulse-s0-verify/tests/test_source_platform_admin.py`
- Modify: `g:/ramypulse-s0-verify/tests/test_platform_foundation.py`
- Modify: `g:/ramypulse-s0-verify/tests/test_database.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest


@pytest.mark.parametrize(
    ("platform", "config_json"),
    [
        ("facebook", {"page_url": "https://facebook.com/ramy", "fetch_mode": "snapshot"}),
        ("google_maps", {"place_url": "https://maps.google.com/?cid=1", "fetch_mode": "snapshot"}),
        ("youtube", {"channel_id": "UC123", "fetch_mode": "snapshot"}),
        ("instagram", {"profile_url": "https://instagram.com/ramy", "fetch_mode": "snapshot"}),
        ("import", {"snapshot_path": None, "fetch_mode": "snapshot"}),
    ],
)
def test_create_source_accepts_les_cinq_plateformes(platform_db, tmp_path, platform, config_json) -> None:
    from core.ingestion.orchestrator import IngestionOrchestrator

    if platform == "import":
        csv_path = tmp_path / "five-sources-import.csv"
        csv_path.write_text("text,channel,timestamp\nramy dispo,import,2026-04-03T11:00:00\n", encoding="utf-8")
        config_json = dict(config_json)
        config_json["snapshot_path"] = str(csv_path)

    orchestrator = IngestionOrchestrator(db_path=str(platform_db))
    source = orchestrator.create_source(
        {
            "client_id": "client-five",
            "source_name": f"{platform} source",
            "platform": platform,
            "source_type": "batch_import" if platform == "import" else f"{platform}_feed",
            "owner_type": "owned",
            "config_json": config_json,
        }
    )

    assert source["platform"] == platform
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_source_platform_admin.py tests/test_platform_foundation.py -k cinq_plateformes -v`
Expected: FAIL until `instagram` and validation paths are fully wired

- [ ] **Step 3: Write minimal implementation**

```python
self._connectors = {
    "import": BatchImportConnector(),
    "facebook": FacebookConnector(),
    "google_maps": GoogleMapsConnector(),
    "youtube": YouTubeConnector(),
    "instagram": InstagramConnector(),
}
```

```python
supported_platforms = {"facebook", "google_maps", "youtube", "instagram", "import"}
if platform not in supported_platforms:
    raise ValueError(f"Plateforme non supportée: {platform}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd g:/ramypulse-s0-verify; python -m pytest tests/test_source_platform_admin.py tests/test_platform_foundation.py tests/test_database.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_source_platform_admin.py tests/test_platform_foundation.py tests/test_database.py core/ingestion/orchestrator.py pages/09_admin_sources.py
git commit -m "test(ingestion): cover five-source end-to-end platform flow"
```

### Task 7: Validation complète et smoke manuel

**Files:**
- Modify: `g:/ramypulse-s0-verify/docs/superpowers/plans/2026-04-03-five-source-ingestion-implementation.md`

- [ ] **Step 1: Run the focused ingestion suite**

Run:

```bash
cd g:/ramypulse-s0-verify
python -m pytest tests/test_source_config.py tests/test_source_platform_admin.py tests/test_admin_sources_page.py tests/test_platform_foundation.py -q --tb=no
```

Expected: all PASS

- [ ] **Step 2: Run the full regression suite**

Run:

```bash
cd g:/ramypulse-s0-verify
python -m pytest tests/ -q --tb=no
```

Expected: all PASS, warnings acceptables seulement si déjà présents avant le lot

- [ ] **Step 3: Smoke the Streamlit admin page**

Run:

```bash
cd g:/ramypulse-s0-verify
python -m streamlit run pages/09_admin_sources.py --server.headless true --server.port 8630
```

Expected:

```text
Local URL: http://localhost:8630
```

Puis vérifier manuellement:

```text
- création source facebook
- création source instagram
- lancement sync import
- affichage sync runs
- affichage health snapshots
- trace raw -> normalized -> enriched
```

- [ ] **Step 4: Push the branch**

Run:

```bash
cd g:/ramypulse-s0-verify
git push origin integration/wave5
```

Expected: push succeeds

- [ ] **Step 5: Commit plan progress note**

```bash
git add docs/superpowers/plans/2026-04-03-five-source-ingestion-implementation.md
git commit -m "docs: mark five-source ingestion plan executed"
```
