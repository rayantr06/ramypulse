"""Tests for credential token update and Meta token refresh."""

from __future__ import annotations

import json

import pytest

from core.database import DatabaseManager
from core.social_metrics.credential_manager import (
    create_credential,
    get_credential,
    update_credential_token,
)

_db = DatabaseManager()
_db.create_tables()


class TestUpdateCredentialToken:
    def test_updates_token_and_extra_config(self):
        cred_id = create_credential(
            entity_type="brand",
            entity_name="update_test",
            platform="instagram",
            access_token="old_token",
            extra_config={"expires_at": "2026-04-01T00:00:00Z"},
            client_id="test-token-refresh",
        )

        update_credential_token(
            cred_id,
            new_access_token="new_token_abc",
            extra_config_updates={"expires_at": "2026-06-01T00:00:00Z", "last_refreshed_at": "2026-04-05T00:00:00Z"},
        )

        cred = get_credential(cred_id)
        assert cred["access_token"] == "new_token_abc"
        assert cred["extra_config"]["expires_at"] == "2026-06-01T00:00:00Z"
        assert cred["extra_config"]["last_refreshed_at"] == "2026-04-05T00:00:00Z"

    def test_nonexistent_credential_returns_false(self):
        result = update_credential_token("cred-nonexistent", new_access_token="tok")
        assert result is False


from unittest.mock import patch, MagicMock
from core.connectors.token_refresh import refresh_if_needed


class TestRefreshIfNeeded:
    def test_no_refresh_when_far_from_expiry(self):
        cred_id = create_credential(
            entity_type="brand",
            entity_name="refresh_far",
            platform="instagram",
            access_token="valid_token",
            app_id="app1",
            app_secret="secret1",
            extra_config={"expires_at": "2026-06-01T00:00:00Z"},
            client_id="test-token-refresh",
        )
        # Token expires in ~57 days — no refresh needed
        result = refresh_if_needed(cred_id)
        assert result is False

    def test_refresh_when_near_expiry(self):
        cred_id = create_credential(
            entity_type="brand",
            entity_name="refresh_near",
            platform="instagram",
            access_token="expiring_token",
            app_id="app1",
            app_secret="secret1",
            extra_config={"expires_at": "2026-04-07T00:00:00Z"},  # ~2 days from now (2026-04-05)
            client_id="test-token-refresh",
        )

        new_token_response = {
            "access_token": "refreshed_token_xyz",
            "token_type": "bearer",
            "expires_in": 5184000,
        }

        with patch("core.connectors.token_refresh.meta_graph_get", return_value=new_token_response):
            result = refresh_if_needed(cred_id)

        assert result is True
        cred = get_credential(cred_id)
        assert cred["access_token"] == "refreshed_token_xyz"

    def test_no_refresh_when_expires_at_missing(self):
        cred_id = create_credential(
            entity_type="brand",
            entity_name="refresh_no_expiry",
            platform="instagram",
            access_token="token_no_expiry",
            extra_config={},
            client_id="test-token-refresh",
        )
        result = refresh_if_needed(cred_id)
        assert result is False

    def test_refresh_failure_returns_false(self):
        import urllib.error
        cred_id = create_credential(
            entity_type="brand",
            entity_name="refresh_fail",
            platform="instagram",
            access_token="failing_token",
            app_id="app1",
            app_secret="secret1",
            extra_config={"expires_at": "2026-04-07T00:00:00Z"},
            client_id="test-token-refresh",
        )

        with patch("core.connectors.token_refresh.meta_graph_get") as mock_get:
            mock_get.side_effect = urllib.error.HTTPError("url", 400, "Invalid token", None, None)
            result = refresh_if_needed(cred_id)

        assert result is False
        # Token should NOT have been changed
        cred = get_credential(cred_id)
        assert cred["access_token"] == "failing_token"

    def test_nonexistent_credential_returns_false(self):
        result = refresh_if_needed("cred-nonexistent-xyz")
        assert result is False
