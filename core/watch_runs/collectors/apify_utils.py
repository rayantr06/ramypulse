"""Compatibilité commune avec les clients Apify Python v1 à v3."""

from __future__ import annotations

from typing import Any


def default_dataset_id(run: Any) -> str:
    """Retourne l'identifiant du dataset pour une réponse dict ou Pydantic."""

    if run is None:
        raise RuntimeError("Apify actor did not return a run")
    if isinstance(run, dict):
        value = run.get("defaultDatasetId") or run.get("default_dataset_id")
    else:
        value = getattr(run, "default_dataset_id", None) or getattr(
            run,
            "defaultDatasetId",
            None,
        )
    dataset_id = str(value or "").strip()
    if not dataset_id:
        raise RuntimeError("Apify actor run has no default dataset")
    return dataset_id
