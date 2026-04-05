# Automation Alert Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** make RamyPulse automation actually runnable without manual button-click dependence, while closing the `source health -> alert` and `alert -> notification` gaps.

**Architecture:** add a backend one-shot runtime orchestrator that can be invoked by an external scheduler (cron, Task Scheduler, CI runner) instead of hard-coding APScheduler into FastAPI. Reuse the existing `run_due_syncs`, `run_normalization_job`, `compute_source_health`, `run_alert_detection`, and notification primitives, but add the missing glue and safety around them.

**Tech Stack:** Python, FastAPI, SQLite, existing core runtime/alerts/notifications modules, pytest

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `core/runtime/automation_runtime.py` | Create | One-shot orchestration entrypoint for the automation cycle |
| `scripts/run_automation_cycle.py` | Create | CLI/script entrypoint for external schedulers |
| `core/ingestion/health_checker.py` | Modify | Optional alert emission when source health drops below threshold |
| `core/alerts/alert_manager.py` | Modify | Auto-notification trigger after alert creation |
| `config.py` | Modify | Minimal runtime notification config knobs |
| `tests/test_runtime_automation.py` | Create | Runtime orchestration tests |
| `tests/test_alerts.py` | Modify | Health alert and notification auto-trigger tests |
| `tests/test_api.py` | Modify | Admin runtime endpoint tests if a new endpoint is added |

---

### Task 1: Add the automation runtime orchestrator

**Files:**
- Create: `core/runtime/automation_runtime.py`
- Create: `scripts/run_automation_cycle.py`
- Test: `tests/test_runtime_automation.py`

- [ ] **Step 1: Write failing tests for the runtime orchestrator**

Add tests covering:
- one full cycle runs due syncs, normalization, health checks, and alert detection in order
- disabled steps can be skipped explicitly
- runtime returns a structured summary, not raw tuples/side effects

Test sketch:

```python
def test_run_automation_cycle_executes_enabled_steps(monkeypatch):
    import core.runtime.automation_runtime as runtime

    monkeypatch.setattr(runtime, "run_due_syncs", lambda **kwargs: {"sources_scheduled": 2})
    monkeypatch.setattr(runtime, "run_normalization_job", lambda **kwargs: {"processed_count": 5})
    monkeypatch.setattr(runtime, "run_source_health_cycle", lambda **kwargs: {"sources_checked": 3, "alerts_created": 1})
    monkeypatch.setattr(runtime, "run_alert_detection_cycle", lambda **kwargs: {"alerts_created": 4})

    result = runtime.run_automation_cycle(client_id="ramy_client_001")

    assert result["client_id"] == "ramy_client_001"
    assert result["sync"]["sources_scheduled"] == 2
    assert result["normalization"]["processed_count"] == 5
    assert result["health"]["alerts_created"] == 1
    assert result["alerts"]["alerts_created"] == 4
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```bash
python -m pytest tests/test_runtime_automation.py -q --tb=no
```

Expected:
- failure because `core.runtime.automation_runtime` does not exist yet

- [ ] **Step 3: Implement `core/runtime/automation_runtime.py`**

Create a one-shot orchestrator with:
- `run_source_health_cycle(...)`
- `run_alert_detection_cycle(...)`
- `run_automation_cycle(...)`

Responsibilities:
- call `run_due_syncs(...)`
- call `run_normalization_job(...)`
- compute health for all active sources
- load annotated data and run alert detection if data exists
- return one structured dict with per-step summaries

Implementation shape:

```python
def run_automation_cycle(
    *,
    client_id: str = config.DEFAULT_CLIENT_ID,
    run_sync: bool = True,
    run_normalization: bool = True,
    run_health: bool = True,
    run_alerts: bool = True,
    batch_size: int = 200,
    now: str | datetime | None = None,
    db_path=None,
) -> dict:
    ...
```

- [ ] **Step 4: Implement the script entrypoint**

Create `scripts/run_automation_cycle.py` that:
- imports `run_automation_cycle`
- prints JSON summary to stdout
- returns non-zero only on unrecoverable errors

Minimal shape:

```python
def main() -> int:
    result = run_automation_cycle()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
```

- [ ] **Step 5: Run runtime tests again**

Run:

```bash
python -m pytest tests/test_runtime_automation.py -q --tb=no
```

Expected:
- PASS

---

### Task 2: Close the `source health -> alert` chain

**Files:**
- Modify: `core/ingestion/health_checker.py`
- Test: `tests/test_alerts.py`

- [ ] **Step 1: Write failing tests for source health alerts**

Add tests covering:
- health score below `SOURCE_HEALTH_THRESHOLD` creates one alert
- dedup key prevents repeated active duplicates
- healthy source does not create alert

Test sketch:

```python
def test_compute_source_health_creates_alert_when_below_threshold(monkeypatch, tmp_path):
    from core.ingestion.health_checker import compute_source_health

    created = []
    monkeypatch.setattr(
        "core.ingestion.health_checker.create_alert",
        lambda **kwargs: created.append(kwargs) or "alert-1",
    )

    # seed source + failing runs in tmp DB
    ...

    result = compute_source_health(source_id, db_path=tmp_db, emit_alert=True)

    assert result["health_score"] < 60
    assert result["alert_id"] == "alert-1"
    assert created[0]["severity"] in {"medium", "high", "critical"}
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run:

```bash
python -m pytest tests/test_alerts.py -q --tb=no -k "source_health"
```

Expected:
- failure because `compute_source_health()` does not emit alerts yet

- [ ] **Step 3: Extend `compute_source_health()` safely**

Add optional parameters:
- `emit_alert: bool = False`
- `threshold: int | None = None`

Behavior:
- keep current snapshot behavior unchanged
- when `emit_alert=True` and score below threshold:
  - create a deduplicated alert
  - include alert metadata in returned payload

Requirements:
- do not create duplicates for still-active incidents
- navigation should point back to the source admin trace

- [ ] **Step 4: Re-run focused tests**

Run:

```bash
python -m pytest tests/test_alerts.py -q --tb=no -k "source_health"
```

Expected:
- PASS

---

### Task 3: Close the `alert -> notification` chain

**Files:**
- Modify: `core/alerts/alert_manager.py`
- Modify: `config.py`
- Test: `tests/test_alerts.py`

- [ ] **Step 1: Write failing tests for auto-notification on alert creation**

Add tests covering:
- no email/slack is sent when config is empty
- email/slack is sent when configured and severity threshold is met
- severity below threshold does not notify

Test sketch:

```python
def test_create_alert_triggers_notifications_when_configured(monkeypatch):
    import core.alerts.alert_manager as alert_manager

    sent_email = []
    sent_slack = []
    monkeypatch.setattr(alert_manager, "send_email_notification", lambda **kwargs: sent_email.append(kwargs) or "n1")
    monkeypatch.setattr(alert_manager, "send_slack_notification", lambda **kwargs: sent_slack.append(kwargs) or "n2")
    monkeypatch.setattr(alert_manager._config_module(), "ALERT_NOTIFICATION_EMAIL_TO", "ops@example.com", raising=False)
    monkeypatch.setattr(alert_manager._config_module(), "ALERT_NOTIFICATION_SLACK_WEBHOOK_REFERENCE", "env:TEST_SLACK", raising=False)
    monkeypatch.setattr(alert_manager._config_module(), "ALERT_NOTIFICATION_MIN_SEVERITY", "high", raising=False)
    monkeypatch.setenv("TEST_SLACK", "https://hooks.slack.test/services/abc")

    alert_id = alert_manager.create_alert(...)

    assert alert_id is not None
    assert sent_email
    assert sent_slack
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run:

```bash
python -m pytest tests/test_alerts.py -q --tb=no -k "notification"
```

Expected:
- failure because `create_alert()` currently triggers recommendations only

- [ ] **Step 3: Add minimal config knobs**

Add to `config.py`:
- `ALERT_NOTIFICATION_EMAIL_TO`
- `ALERT_NOTIFICATION_SLACK_WEBHOOK_REFERENCE`
- `ALERT_NOTIFICATION_MIN_SEVERITY`

Keep them environment-driven and optional.

- [ ] **Step 4: Implement notification auto-trigger in `alert_manager.py`**

Add a helper:

```python
def _run_notification_auto_trigger(alert_id: str, severity: str, title: str, description: str) -> None:
    ...
```

Requirements:
- use config/env only for this phase
- resolve Slack webhook through `resolve_secret`
- respect minimum severity threshold
- never break alert creation if notification delivery fails
- log exceptions and continue

- [ ] **Step 5: Re-run focused tests**

Run:

```bash
python -m pytest tests/test_alerts.py -q --tb=no -k "notification"
```

Expected:
- PASS

---

### Task 4: Expose the runtime cleanly to operators

**Files:**
- Modify: `api/routers/admin.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Add tests for:
- `POST /api/admin/runtime/cycle` returns the structured runtime summary
- runtime endpoint can disable selected steps via payload or query params

Test sketch:

```python
def test_admin_runtime_cycle_endpoint(self):
    with patch("api.routers.admin.run_automation_cycle", return_value={"sync": {}, "normalization": {}, "health": {}, "alerts": {}}):
        r = client.post("/api/admin/runtime/cycle", json={})
    assert r.status_code == 200
    assert "sync" in r.json()
```

- [ ] **Step 2: Run the focused API tests and confirm failure**

Run:

```bash
python -m pytest tests/test_api.py -q --tb=no -k "runtime_cycle"
```

Expected:
- failure because the endpoint does not exist yet

- [ ] **Step 3: Add the admin endpoint**

Expose a manual trigger for operators and scripts:
- `POST /api/admin/runtime/cycle`

Behavior:
- delegates to `run_automation_cycle(...)`
- returns the structured summary
- no hidden background thread here

- [ ] **Step 4: Re-run focused API tests**

Run:

```bash
python -m pytest tests/test_api.py -q --tb=no -k "runtime_cycle"
```

Expected:
- PASS

---

### Task 5: Full regression for Lot B

**Files:**
- Verify only

- [ ] **Step 1: Run all backend tests**

Run:

```bash
python -m pytest tests/ -q --tb=no
```

Expected:
- full backend suite passes

- [ ] **Step 2: Smoke the runtime script**

Run:

```bash
python scripts/run_automation_cycle.py
```

Expected:
- JSON summary printed
- no traceback on a normal local setup

- [ ] **Step 3: Commit the lot**

```bash
git add core/runtime/automation_runtime.py scripts/run_automation_cycle.py core/ingestion/health_checker.py core/alerts/alert_manager.py config.py api/routers/admin.py tests/test_runtime_automation.py tests/test_alerts.py tests/test_api.py docs/superpowers/plans/2026-04-05-automation-alert-runtime.md
git commit -m "feat(runtime): automate health and alert delivery"
```

