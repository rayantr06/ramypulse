"""Client HTTP résilient du service d'inférence LIDAL SLM V0.4."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

import config
from core.analysis.slm_v04_compiler import CompilationResult, compile_slm_output

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SlmAnalysisResult:
    """Enveloppe prête à persister dans ``enriched_signals``."""

    compilation: CompilationResult
    raw_model_output: str
    model_version: str | None
    inference_ms: int | None
    created_at: str | None
    transport_error: str | None = None
    service_metadata: dict[str, Any] = field(default_factory=dict)


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.SLM_V04_API_KEY:
        headers["X-LIDAL-SLM-Key"] = config.SLM_V04_API_KEY
    return headers


def analyze_with_slm(
    text: str,
    *,
    monitoring_target: dict[str, Any],
    topic: str | None = None,
    session: requests.Session | None = None,
) -> SlmAnalysisResult:
    """Appelle le SLM, compile sa sortie et renvoie un résultat auditable."""

    if not config.SLM_V04_BASE_URL:
        raise RuntimeError("SLM_V04_BASE_URL is not configured")

    http = session or requests.Session()
    started = time.perf_counter()
    response = http.post(
        f"{config.SLM_V04_BASE_URL.rstrip('/')}/v1/analyze",
        json={
            "text": text,
            "context": {
                "monitoring_target": monitoring_target,
                "topic": topic,
            },
        },
        headers=_headers(),
        timeout=config.SLM_V04_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    raw_output = str(payload.get("raw_model_output") or payload.get("output") or "")
    compilation = compile_slm_output(
        raw_output,
        text=text,
        monitoring_target=monitoring_target,
    )
    measured_ms = round((time.perf_counter() - started) * 1000)
    inference_ms = payload.get("inference_ms")
    return SlmAnalysisResult(
        compilation=compilation,
        raw_model_output=raw_output,
        model_version=str(payload.get("model_version") or "").strip() or None,
        inference_ms=int(inference_ms) if isinstance(inference_ms, (int, float)) else measured_ms,
        created_at=str(payload.get("created_at") or "").strip() or None,
        service_metadata={
            key: value
            for key, value in payload.items()
            if key not in {"raw_model_output", "output"}
        },
    )
