"""Aides partagees pour parser et valider la configuration d'une source."""

from __future__ import annotations

import json

_VALID_FETCH_MODES = {"snapshot", "collector", "api"}
_REQUIRED_FIELDS = {
    "facebook": (("page_id", "page_url"),),
    "google_maps": (("place_id", "place_url"),),
    "youtube": (("channel_id", "video_ids"),),
    "instagram": (("profile_id", "profile_url"),),
}


def _has_value(value: object) -> bool:
    """Indique si une valeur de configuration contient quelque chose d'utilisable."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def parse_source_config(source: dict) -> dict:
    """Normalise config_json en dictionnaire sans modifier la source d'origine."""
    raw_config = source.get("config_json") or {}
    if isinstance(raw_config, dict):
        return dict(raw_config)
    if isinstance(raw_config, str) and raw_config.strip():
        try:
            parsed = json.loads(raw_config)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def validate_source_config(
    source: dict,
    *,
    require_platform_fields: bool = True,
) -> dict:
    """Valide la configuration d'une source et applique les valeurs par defaut."""
    config = parse_source_config(source)
    fetch_mode = str(config.get("fetch_mode") or "snapshot").strip().lower() or "snapshot"
    if fetch_mode not in _VALID_FETCH_MODES:
        raise ValueError("Configuration source invalide: fetch_mode doit etre snapshot, collector ou api")
    config["fetch_mode"] = fetch_mode

    if require_platform_fields:
        platform = str(source.get("platform") or "").strip()
        required_groups = _REQUIRED_FIELDS.get(platform, ())
        for group in required_groups:
            if not any(_has_value(config.get(field)) for field in group):
                fields = " ou ".join(group)
                raise ValueError(f"Configuration {platform} invalide: un de {fields} est requis")
    return config
