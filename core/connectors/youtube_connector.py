"""Connecteur YouTube Wave 5.1."""

from __future__ import annotations

from core.connectors.platform_snapshot_connector import SnapshotPlatformConnector


class YouTubeConnector(SnapshotPlatformConnector):
    """Connecteur YouTube via snapshot local ou collecteur optionnel."""

    def __init__(self) -> None:
        super().__init__(
            platform="youtube",
            default_snapshot_names=("youtube_raw.parquet",),
            scraper_modules=("core.ingestion.scraper_youtube",),
        )
