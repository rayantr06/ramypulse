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
