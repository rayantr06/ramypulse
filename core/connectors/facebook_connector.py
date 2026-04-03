"""Connecteur Facebook Pages Wave 5.1."""

from __future__ import annotations

from core.connectors.platform_snapshot_connector import SnapshotPlatformConnector


class FacebookConnector(SnapshotPlatformConnector):
    """Connecteur Facebook via snapshot local ou collecteur optionnel."""

    def __init__(self) -> None:
        super().__init__(
            platform="facebook",
            default_snapshot_names=("facebook_raw.parquet",),
            scraper_modules=("core.ingestion.scraper_facebook",),
        )
