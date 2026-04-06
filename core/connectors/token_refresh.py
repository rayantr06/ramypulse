"""Meta token refresh for long-lived Facebook/Instagram tokens."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from core.connectors.meta_graph_client import meta_graph_get
from core.social_metrics.credential_manager import get_credential, update_credential_token

logger = logging.getLogger(__name__)

_REFRESH_THRESHOLD_DAYS = 5


def refresh_if_needed(credential_id: str) -> bool:
    """Refresh a Meta long-lived token if it expires within the threshold.

    Args:
        credential_id: The credential to check and potentially refresh.

    Returns:
        True if the token was refreshed, False otherwise.
    """
    cred = get_credential(credential_id)
    if not cred:
        logger.warning("Token refresh: credential %s not found", credential_id)
        return False

    extra_config = cred.get("extra_config") or {}
    expires_at_str = extra_config.get("expires_at")
    if not expires_at_str:
        logger.debug("Token refresh: no expires_at for credential %s, skipping", credential_id)
        return False

    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        logger.warning("Token refresh: invalid expires_at '%s' for %s", expires_at_str, credential_id)
        return False

    now = datetime.now(timezone.utc)
    remaining = expires_at - now
    if remaining > timedelta(days=_REFRESH_THRESHOLD_DAYS):
        logger.debug(
            "Token refresh: credential %s has %d days remaining, no refresh needed",
            credential_id,
            remaining.days,
        )
        return False

    access_token = cred.get("access_token")
    app_id = cred.get("app_id")
    app_secret = cred.get("app_secret")

    if not access_token or not app_id or not app_secret:
        logger.warning(
            "Token refresh: credential %s missing access_token, app_id, or app_secret",
            credential_id,
        )
        return False

    try:
        response = meta_graph_get(
            "oauth/access_token",
            access_token=access_token,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": access_token,
            },
        )
    except Exception:
        logger.exception("Token refresh failed for credential %s", credential_id)
        return False

    new_token = response.get("access_token")
    if not new_token:
        logger.warning("Token refresh: Meta response missing access_token for %s", credential_id)
        return False

    expires_in = int(response.get("expires_in", 5184000))
    new_expires_at = (now + timedelta(seconds=expires_in)).isoformat()

    update_credential_token(
        credential_id,
        new_access_token=new_token,
        extra_config_updates={
            "expires_at": new_expires_at,
            "last_refreshed_at": now.isoformat(),
        },
    )

    logger.info("Token refreshed for credential %s — new expiry: %s", credential_id, new_expires_at)
    return True
