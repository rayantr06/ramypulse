"""Fallback screenshot pour la saisie manuelle de métriques."""

from __future__ import annotations

import uuid
from pathlib import Path

import config
from core.social_metrics.instagram_graph_collector import save_metrics

SCREENSHOTS_DIR: Path = config.DATA_DIR / "uploads" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def save_screenshot(
    post_id: str,
    file_bytes: bytes,
    filename: str,
    *,
    metrics: dict[str, int],
) -> dict:
    """Sauvegarde une capture d'écran et persiste les métriques associées."""
    ext = Path(filename).suffix.lower() or ".png"
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError(f"Format non supporté : {ext}. Utilisez PNG, JPG ou WEBP.")

    screenshot_id = uuid.uuid4().hex[:12]
    dest_name = f"{post_id}_{screenshot_id}{ext}"
    dest_path = SCREENSHOTS_DIR / dest_name
    dest_path.write_bytes(file_bytes)

    metric_id = save_metrics(
        post_id,
        metrics,
        collection_mode="screenshot",
        raw_response={
            "screenshot_path": str(dest_path),
            "source": "manual_upload",
        },
    )

    return {
        "metric_id": metric_id,
        "screenshot_path": str(dest_path),
        "post_id": post_id,
        **metrics,
    }
