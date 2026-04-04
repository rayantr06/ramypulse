"""Connecteur Instagram Wave 5.2."""

from __future__ import annotations

from core.connectors.platform_snapshot_connector import SnapshotPlatformConnector


class InstagramConnector(SnapshotPlatformConnector):
    """Connecteur Instagram via snapshot local ou collecteur optionnel."""

    def __init__(self) -> None:
        super().__init__(
            platform="instagram",
            default_snapshot_names=("instagram_raw.parquet",),
            scraper_modules=("core.ingestion.scraper_instagram",),
        )
