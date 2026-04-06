"""Tests for credential_id resolution in the orchestrator."""

from __future__ import annotations

import json
import sqlite3

import pytest

import config
from core.database import DatabaseManager
from core.ingestion.orchestrator import IngestionOrchestrator
from core.social_metrics.credential_manager import create_credential

_db = DatabaseManager()
_db.create_tables()


def _create_test_credential(access_token: str = "test_token_123") -> str:
    """Create a credential and return its credential_id."""
    return create_credential(
        entity_type="brand",
        entity_name="test_brand",
        platform="instagram",
        account_id="17841400123456789",
        access_token=access_token,
        app_id="app_123",
        app_secret="secret_456",
    )


class TestCredentialIdResolution:
    def test_credential_id_resolves_token(self):
        """When source has credential_id, orchestrator should resolve it."""
        cred_id = _create_test_credential("my_real_token")
        orchestrator = IngestionOrchestrator()

        source = orchestrator.create_source({
            "source_name": "IG API Test",
            "platform": "instagram",
            "source_type": "api",
            "owner_type": "brand",
            "credential_id": cred_id,
            "config_json": json.dumps({"fetch_mode": "api", "profile_id": "17841400123456789"}),
        })

        captured_credentials = {}

        def fake_fetch(src, *, credentials=None, **kw):
            captured_credentials.update(credentials or {})
            return []

        from unittest.mock import patch
        with patch.object(orchestrator._connectors["instagram"], "fetch_documents", side_effect=fake_fetch):
            orchestrator.run_source_sync(source["source_id"])

        assert captured_credentials.get("access_token") == "my_real_token"
        assert captured_credentials.get("account_id") == "17841400123456789"

    def test_null_credential_id_uses_old_path(self):
        """When source has no credential_id, the old credential_ref path still works."""
        orchestrator = IngestionOrchestrator()

        source = orchestrator.create_source({
            "source_name": "IG Snapshot Test",
            "platform": "instagram",
            "source_type": "batch_import",
            "owner_type": "brand",
            "config_json": json.dumps({"fetch_mode": "snapshot"}),
        })

        captured_credentials = {}

        def fake_fetch(src, *, credentials=None, **kw):
            captured_credentials.update(credentials or {})
            return []

        # batch_import sources are routed to _connectors["import"] regardless of platform
        from unittest.mock import patch
        with patch.object(orchestrator._connectors["import"], "fetch_documents", side_effect=fake_fetch):
            orchestrator.run_source_sync(source["source_id"])

        assert "access_token" not in captured_credentials or captured_credentials.get("access_token") is None

    def test_other_platform_unaffected(self):
        """Facebook connector should not be affected by credential_id changes."""
        orchestrator = IngestionOrchestrator()

        source = orchestrator.create_source({
            "source_name": "FB Test",
            "platform": "facebook",
            "source_type": "batch_import",
            "owner_type": "brand",
            "config_json": json.dumps({"fetch_mode": "snapshot"}),
        })

        def fake_fetch(src, *, credentials=None, **kw):
            return []

        # batch_import sources are routed to _connectors["import"] regardless of platform
        from unittest.mock import patch
        with patch.object(orchestrator._connectors["import"], "fetch_documents", side_effect=fake_fetch):
            result = orchestrator.run_source_sync(source["source_id"])

        assert result["status"] == "success"


from unittest.mock import patch


class TestTokenRefreshDuringSync:
    def test_refresh_called_for_source_with_credential_id(self):
        cred_id = _create_test_credential("token_to_refresh")
        orchestrator = IngestionOrchestrator()

        source = orchestrator.create_source({
            "source_name": "IG Refresh Test",
            "platform": "instagram",
            "source_type": "api",
            "owner_type": "brand",
            "credential_id": cred_id,
            "config_json": json.dumps({"fetch_mode": "api", "profile_id": "17841400123456789"}),
        })

        with (
            patch("core.ingestion.orchestrator.refresh_if_needed") as mock_refresh,
            patch.object(orchestrator._connectors["instagram"], "fetch_documents", return_value=[]),
        ):
            mock_refresh.return_value = False
            orchestrator.run_source_sync(source["source_id"])

        mock_refresh.assert_called_once_with(cred_id)

    def test_refresh_not_called_without_credential_id(self):
        orchestrator = IngestionOrchestrator()

        source = orchestrator.create_source({
            "source_name": "IG No Cred Test",
            "platform": "instagram",
            "source_type": "batch_import",
            "owner_type": "brand",
            "config_json": json.dumps({"fetch_mode": "snapshot"}),
        })

        with (
            patch("core.ingestion.orchestrator.refresh_if_needed") as mock_refresh,
            patch.object(orchestrator._connectors["import"], "fetch_documents", return_value=[]),
        ):
            orchestrator.run_source_sync(source["source_id"])

        mock_refresh.assert_not_called()
