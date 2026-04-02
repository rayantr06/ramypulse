"""Gestionnaire local de secrets hors base de donnees."""

from __future__ import annotations

import base64
import hashlib
import importlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path


def _config_module():
    """Retourne le module config courant, meme apres reload dans les tests."""
    return importlib.import_module("config")


def _store_path() -> Path:
    """Retourne le chemin du store local de secrets."""
    cfg = _config_module()
    return Path(getattr(cfg, "SECRETS_STORE_PATH", cfg.DATA_DIR / "secrets" / "local_secrets.json"))


def _load_store() -> dict:
    """Charge le store local ou retourne une structure vide."""
    path = _store_path()
    if not path.exists():
        return {"version": 1, "secrets": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "secrets": {}}
    if not isinstance(payload, dict):
        return {"version": 1, "secrets": {}}
    payload.setdefault("version", 1)
    payload.setdefault("secrets", {})
    return payload


def _write_store(payload: dict) -> None:
    """Persiste le store local sur disque."""
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _fingerprint(secret_value: str) -> str:
    """Calcule une empreinte stable du secret pour eviter les doublons."""
    return hashlib.sha256(secret_value.encode("utf-8")).hexdigest()


def is_secret_reference(value: str | None) -> bool:
    """Indique si une valeur ressemble a une reference de secret supportee."""
    if not value:
        return False
    return str(value).startswith("env:") or str(value).startswith("local:")


def store_secret(secret_value: str | None, label: str | None = None) -> str | None:
    """Stocke un secret dans le store local et retourne sa reference."""
    if secret_value in (None, ""):
        return None
    value = str(secret_value).strip()
    if not value:
        return None
    if is_secret_reference(value):
        return value

    payload = _load_store()
    fingerprint = _fingerprint(value)
    secrets = payload.setdefault("secrets", {})

    for secret_id, record in secrets.items():
        if record.get("fingerprint") == fingerprint:
            return f"local:{secret_id}"

    secret_id = str(uuid.uuid4())
    secrets[secret_id] = {
        "label": label or "",
        "fingerprint": fingerprint,
        "encoded_value": base64.b64encode(value.encode("utf-8")).decode("ascii"),
        "created_at": datetime.now().isoformat(),
    }
    _write_store(payload)
    return f"local:{secret_id}"


def resolve_secret(reference: str | None) -> str | None:
    """Resout une reference de secret en valeur exploitable."""
    if reference in (None, ""):
        return None
    value = str(reference).strip()
    if not value:
        return None

    if value.startswith("env:"):
        return os.getenv(value[4:]) or None

    if value.startswith("local:"):
        secret_id = value.split(":", 1)[1]
        record = _load_store().get("secrets", {}).get(secret_id)
        if not isinstance(record, dict):
            return None
        encoded = record.get("encoded_value")
        if not encoded:
            return None
        try:
            return base64.b64decode(encoded.encode("ascii")).decode("utf-8")
        except (ValueError, OSError, UnicodeDecodeError):
            return None

    return value
