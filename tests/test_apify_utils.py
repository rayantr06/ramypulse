"""Compatibilité des enveloppes de runs Apify."""

from __future__ import annotations

import pytest

from core.watch_runs.collectors.apify_utils import default_dataset_id


def test_default_dataset_id_supports_legacy_and_v3_objects() -> None:
    class _Run:
        default_dataset_id = "typed-dataset"

    assert default_dataset_id({"defaultDatasetId": "legacy-dataset"}) == "legacy-dataset"
    assert default_dataset_id({"default_dataset_id": "snake-dataset"}) == "snake-dataset"
    assert default_dataset_id(_Run()) == "typed-dataset"


def test_default_dataset_id_rejects_missing_value() -> None:
    with pytest.raises(RuntimeError, match="dataset"):
        default_dataset_id(object())
