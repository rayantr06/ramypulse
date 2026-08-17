"""Diagnostic non destructif des intégrations V3 SLM et Apify.

Ce script ne lance aucun acteur et n'affiche jamais les secrets.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import config


def _check_apify() -> dict[str, object]:
    if not config.APIFY_API_KEY:
        return {"configured": False, "reachable": False, "detail": "missing_api_key"}
    try:
        from apify_client import ApifyClient

        user = ApifyClient(config.APIFY_API_KEY).user().get()
        return {
            "configured": True,
            "reachable": user is not None,
            "detail": "authenticated" if user is not None else "empty_user_response",
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "detail": type(exc).__name__,
        }


def _check_slm() -> dict[str, object]:
    if not config.SLM_V04_BASE_URL:
        return {
            "enabled": config.SLM_V04_ENABLED,
            "configured": False,
            "reachable": False,
            "detail": "missing_base_url",
        }
    headers = {}
    if config.SLM_V04_API_KEY:
        headers["X-LIDAL-SLM-Key"] = config.SLM_V04_API_KEY
    try:
        response = requests.get(
            f"{config.SLM_V04_BASE_URL.rstrip('/')}/health",
            headers=headers,
            timeout=min(config.SLM_V04_TIMEOUT_SECONDS, 10),
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "enabled": config.SLM_V04_ENABLED,
            "configured": True,
            "reachable": True,
            "detail": payload.get("status", "unknown"),
            "model_version": payload.get("model_version"),
            "model_loaded": payload.get("model_loaded"),
        }
    except Exception as exc:
        return {
            "enabled": config.SLM_V04_ENABLED,
            "configured": True,
            "reachable": False,
            "detail": type(exc).__name__,
        }


def main() -> int:
    report = {"apify": _check_apify(), "slm_v04": _check_slm()}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    slm_ready = bool(report["slm_v04"]["reachable"]) if config.SLM_V04_ENABLED else True
    return 0 if report["apify"]["reachable"] and slm_ready else 1


if __name__ == "__main__":
    sys.exit(main())
