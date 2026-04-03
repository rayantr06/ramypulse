"""Connecteur Google Maps / Business Profile Wave 5.1."""

from __future__ import annotations

from core.connectors.platform_snapshot_connector import SnapshotPlatformConnector


class GoogleMapsConnector(SnapshotPlatformConnector):
    """Connecteur Google Maps via snapshot local ou collecteur optionnel."""

    def __init__(self) -> None:
        super().__init__(
            platform="google_maps",
            default_snapshot_names=("google_raw.parquet", "google_maps_raw.parquet"),
            scraper_modules=("core.ingestion.scraper_google",),
        )
