from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from services.v3_api.analytics import OverviewInput, build_overview, priority_score, sentiment_net
from services.v3_api.detection import DetectionWindow, detect_initial_signals
from services.v3_api.domain import (
    ActionCreate,
    ActionTransition,
    CaseCreate,
    MonitorCreate,
    MonitorObjective,
    SignalSeverity,
    SourcePlatform,
    TargetType,
    WorkStatus,
)
from services.v3_api.repository import V3Repository
from services.v3_api.connectors import BudgetExceeded, CollectedDocument, enforce_collection_limits
from services.v3_api.providers import ApifyPublicConnector


def eligible(sentiment: str, *, aspects: list[str] | None = None) -> dict[str, object]:
    return {
        "validation_status": "valid",
        "is_exploitable": True,
        "business_relevance": "directe",
        "requires_parent_context": False,
        "author_role": "consommateur",
        "sentiment": sentiment,
        "aspects": aspects or [],
    }


def monitor_payload() -> MonitorCreate:
    return MonitorCreate(
        name="Reputation Algerie Telecom",
        objective=MonitorObjective.REPUTATION,
        target_type=TargetType.ORGANIZATION,
        target_name="Algerie Telecom",
        aliases=["AT", "Algerie Telecom", "AT"],
        exclusions=["recrutement"],
        sources=[SourcePlatform.FACEBOOK, SourcePlatform.YOUTUBE],
    )


def test_sentiment_net_requires_thirty_qualified_mentions() -> None:
    assert sentiment_net({"positif": 20, "negatif": 9}) is None
    assert sentiment_net({"positif": 20, "negatif": 10}) == pytest.approx(33.3)


def test_overview_excludes_invalid_and_context_dependent_mentions() -> None:
    rows = [eligible("positif", aspects=["service_client_sav"]) for _ in range(20)]
    rows += [eligible("negatif", aspects=["service_client_sav"]) for _ in range(10)]
    rows += [
        {**eligible("negatif"), "validation_status": "failed"},
        {**eligible("negatif"), "requires_parent_context": True},
        {**eligible("negatif"), "author_role": "employe"},
    ]
    overview = build_overview(
        OverviewInput(
            mentions=rows,
            previous_mentions=[eligible("positif") for _ in range(30)],
            collected_documents=40,
            valid_annotations=35,
            open_signals=[{"severity": "high"}],
            ownership_delays_hours=[2.0, 6.0],
            overdue_actions=1,
            source_health=[],
        )
    )
    assert overview["qualified_mentions"] == 30
    assert overview["net_sentiment"] == pytest.approx(33.3)
    assert overview["net_sentiment_delta"] == pytest.approx(-66.7)
    assert overview["analytical_coverage_percent"] == pytest.approx(87.5)
    assert overview["median_time_to_ownership_hours"] == pytest.approx(4.0)


def test_priority_score_renormalizes_missing_reach() -> None:
    score, factors = priority_score(
        severity=100, velocity=80, volume=60, reach=None, confidence=90
    )
    assert score == pytest.approx(85.0)
    assert sum(float(item["weight"]) for item in factors) == pytest.approx(1.0, abs=0.001)
    assert all(item["label"] != "portee" for item in factors)


def test_detection_rules_are_explicit() -> None:
    signals = detect_initial_signals(
        DetectionWindow(
            current_count=42,
            previous_count=18,
            baseline_mean=20,
            baseline_stddev=6,
            current_negative_rate=55,
            previous_negative_rate=30,
            similar_24h=6,
            similar_7d=8,
        ),
        critical_types={"fraud"},
    )
    assert [signal["type"] for signal in signals] == [
        "volume_spike",
        "negative_shift",
        "recurrence",
        "fraud",
    ]
    assert signals[-1]["requires_human_review"] is True


def test_repository_isolates_organizations_and_audits_lifecycle(tmp_path) -> None:
    repository = V3Repository(tmp_path / "v3.sqlite3")
    monitor_a = repository.create_monitor("org-a", monitor_payload())
    repository.create_monitor("org-b", monitor_payload())

    assert [row["organization_id"] for row in repository.list_rows("monitors", "org-a", order_by="created_at")] == ["org-a"]
    assert [row["organization_id"] for row in repository.list_rows("monitors", "org-b", order_by="created_at")] == ["org-b"]

    now = datetime.now(UTC).isoformat()
    with repository.connection() as connection:
        connection.execute(
            """
            INSERT INTO signals (id, organization_id, monitor_id, title, summary, severity,
              status, signal_type, detected_at, mention_count, velocity_percent, confidence,
              territory, observation_ids_json, evidence_ids_json, explanation,
              priority_score, priority_factors_json)
            VALUES ('sig-a', 'org-a', ?, 'Pic negatif', 'Service client', 'high', 'confirmed',
              'negative_shift', ?, 24, 30, .88, 'Alger', '[]', '["m1"]',
              'Hausse de 20 points', 82, '[]')
            """,
            (monitor_a["id"], now),
        )

    case = repository.create_case(
        "org-a",
        CaseCreate(
            signal_id="sig-a",
            title="Verifier le service client",
            priority=SignalSeverity.HIGH,
            owner_id="user-a",
            owner_name="Nadia",
            due_at=datetime.now(UTC) + timedelta(days=2),
        ),
        "user-a",
    )
    action = repository.create_action(
        "org-a",
        ActionCreate(
            case_id=case["id"],
            title="Auditer les reponses",
            description="Verifier vingt conversations et documenter les motifs.",
            owner_id="user-a",
            owner_name="Nadia",
        ),
        "user-a",
    )
    transitioned = repository.transition_action(
        "org-a",
        action["id"],
        ActionTransition(status=WorkStatus.IN_PROGRESS, comment="Audit demarre"),
        "user-a",
    )
    assert transitioned is not None
    assert transitioned["status"] == "in_progress"
    events = repository.list_rows("timeline_events", "org-a", order_by="created_at")
    assert [event["event_type"] for event in events][-3:] == ["created", "created", "status_changed"]


def test_evidence_and_impact_invariants_are_enforced(tmp_path) -> None:
    repository = V3Repository(tmp_path / "invariants.sqlite3")
    monitor = repository.create_monitor("org-a", monitor_payload())
    now = datetime.now(UTC).isoformat()

    with repository.connection() as connection:
        connection.execute(
            """
            INSERT INTO signals (id, organization_id, monitor_id, title, summary, severity,
              status, signal_type, detected_at, mention_count, velocity_percent, confidence,
              territory, observation_ids_json, evidence_ids_json, explanation,
              priority_score, priority_factors_json)
            VALUES ('sig-empty', 'org-a', ?, 'Signal sans preuve', 'A confirmer', 'medium', 'new',
              'recurrence', ?, 7, 20, .74, 'Oran', '[]', '[]',
              'Regroupement provisoire', 58, '[]')
            """,
            (monitor["id"], now),
        )
        connection.execute(
            """
            INSERT INTO signals (id, organization_id, monitor_id, title, summary, severity,
              status, signal_type, detected_at, mention_count, velocity_percent, confidence,
              territory, observation_ids_json, evidence_ids_json, explanation,
              priority_score, priority_factors_json)
            VALUES ('sig-new', 'org-a', ?, 'Signal non confirme', 'Preuves disponibles', 'high', 'new',
              'negative_shift', ?, 21, 30, .86, 'Alger', '[]', '["mention-1"]',
              'Bascule negative', 79, '[]')
            """,
            (monitor["id"], now),
        )

    with pytest.raises(ValueError, match="preuve"):
        repository.transition_signal(
            "org-a",
            "sig-empty",
            "confirmed",
            "Controle humain termine",
            "user-a",
        )

    with pytest.raises(ValueError, match="confirme"):
        repository.create_case(
            "org-a",
            CaseCreate(
                signal_id="sig-new",
                title="Dossier premature",
                priority=SignalSeverity.HIGH,
                owner_name="Nadia",
                due_at=datetime.now(UTC) + timedelta(days=2),
            ),
            "user-a",
        )

    with pytest.raises(ValueError, match="result_value"):
        ActionTransition(status=WorkStatus.RESOLVED, comment="Action terminee")


def test_idempotency_is_tenant_scoped(tmp_path) -> None:
    repository = V3Repository(tmp_path / "v3.sqlite3")
    repository.remember_idempotent("org-a", "same-key", "create", {"id": "a"})
    repository.remember_idempotent("org-b", "same-key", "create", {"id": "b"})
    assert repository.get_idempotent("org-a", "same-key") == {"id": "a"}
    assert repository.get_idempotent("org-b", "same-key") == {"id": "b"}


def test_collection_limits_stop_before_budget_overrun() -> None:
    with pytest.raises(BudgetExceeded, match="volume maximal"):
        enforce_collection_limits(collected=100, cost_dzd=10, max_documents=100, max_cost_dzd=500)
    with pytest.raises(BudgetExceeded, match="budget maximal"):
        enforce_collection_limits(collected=20, cost_dzd=500, max_documents=100, max_cost_dzd=500)


def test_apify_adapter_normalizes_without_leaking_provider_into_domain() -> None:
    connector = ApifyPublicConnector(
        platform="facebook", actor_id="actor", token="secret",
        input_builder=lambda target: {"url": target.canonical_url},
    )
    normalized = connector.normalize(
        CollectedDocument(
            external_id="comment-1",
            canonical_url="https://example.invalid/post/1",
            content="service client ma yjawbouch",
            published_at="2026-08-17T12:00:00Z",
            metadata={"provider_field": "preserved-for-audit"},
        )
    )
    assert normalized["source"] == "facebook"
    assert normalized["text"] == "service client ma yjawbouch"
    assert normalized["raw_metadata"] == {"provider_field": "preserved-for-audit"}


def test_v3_api_requires_auth_and_scopes_idempotency_by_organization(tmp_path, monkeypatch) -> None:
    from services.v3_api import main as v3_main

    v3_main.repository = V3Repository(tmp_path / "api.sqlite3")
    monkeypatch.setenv("LIDAL_V3_ALLOW_DEV_AUTH", "true")
    client = TestClient(v3_main.app)
    payload = monitor_payload().model_dump(mode="json")

    assert client.get("/api/v3/monitors").status_code == 401

    headers_a = {"X-Organization-Id": "org-a", "Idempotency-Key": "monitor-key-0001"}
    created_a = client.post("/api/v3/monitors", headers=headers_a, json=payload)
    replay_a = client.post("/api/v3/monitors", headers=headers_a, json=payload)
    assert created_a.status_code == 201
    assert replay_a.json()["id"] == created_a.json()["id"]

    headers_b = {"X-Organization-Id": "org-b", "Idempotency-Key": "monitor-key-0001"}
    created_b = client.post("/api/v3/monitors", headers=headers_b, json=payload)
    assert created_b.status_code == 201
    assert created_b.json()["id"] != created_a.json()["id"]

    list_a = client.get("/api/v3/monitors", headers={"X-Organization-Id": "org-a"})
    assert [row["organization_id"] for row in list_a.json()] == ["org-a"]


def test_verified_identity_rejects_unclaimed_organization_and_read_only_mutation(monkeypatch) -> None:
    from services.v3_api import main as v3_main
    from services.v3_api import security as v3_security

    monkeypatch.setattr(
        v3_security,
        "_verify_supabase_token",
        lambda _token: {
            "sub": "user-a",
            "app_metadata": {
                "organization_id": "org-a",
                "organization_ids": ["org-a", "org-b"],
                "organization_roles": {"org-a": "viewer", "org-b": "analyst"},
            },
        },
    )

    identity_b = v3_security.resolve_identity("Bearer valid", "org-b")
    assert identity_b.organization_id == "org-b"
    assert identity_b.role == "analyst"

    with pytest.raises(HTTPException) as forbidden_org:
        v3_security.resolve_identity("Bearer valid", "org-c")
    assert forbidden_org.value.status_code == 403

    identity_a = v3_security.resolve_identity("Bearer valid", "org-a")
    with pytest.raises(HTTPException) as forbidden_write:
        v3_main._require_role(identity_a)
    assert forbidden_write.value.status_code == 403

    monkeypatch.setattr(
        v3_security,
        "_verify_supabase_token",
        lambda _token: {
            "sub": "user-primary",
            "app_metadata": {"organization_id": "org-primary", "role": "operator"},
        },
    )
    primary_identity = v3_security.resolve_identity("Bearer valid", None)
    assert primary_identity.organization_id == "org-primary"
    assert primary_identity.role == "operator"
