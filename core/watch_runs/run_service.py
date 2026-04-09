"""Watch run orchestration for the expo-safe tracked pipeline."""

from __future__ import annotations

import inspect
import threading
from pathlib import Path
from typing import Callable

from core.normalization.normalizer_pipeline import run_normalization_job
from core.tenancy.artifact_refresh import refresh_tenant_artifacts
from core.watch_runs.collectors.public_url_seed import collect_public_url_seed
from core.watch_runs.collectors.web_keyword import collect_web_keyword_results
from core.watch_runs.collectors.youtube_search import collect_youtube_search_results
from core.watch_runs.raw_ingestion import insert_watch_documents
from core.watch_runs.run_manager import (
    create_watch_run,
    finish_run,
    finish_step,
    get_watch_run,
    set_stage,
    start_step,
)

CollectorFn = Callable[..., list[dict[str, object]]]

DEFAULT_COLLECTORS: dict[str, CollectorFn] = {
    "public_url_seed": collect_public_url_seed,
    "web_search": collect_web_keyword_results,
    "youtube": collect_youtube_search_results,
}


def _normalize_requested_channels(requested_channels: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in requested_channels:
        channel = str(item or "").strip()
        if not channel or channel in seen:
            continue
        seen.add(channel)
        normalized.append(channel)
    return normalized


def validate_requested_channels(
    requested_channels: list[str],
    *,
    collectors: dict[str, CollectorFn] | None = None,
) -> list[str]:
    """Validate requested channels against the currently available collector set."""
    normalized_channels = _normalize_requested_channels(requested_channels)
    if not normalized_channels:
        raise ValueError("requested_channels must include at least one supported channel")

    resolved_collectors = dict(DEFAULT_COLLECTORS)
    if collectors:
        resolved_collectors.update(collectors)

    unsupported_channels = [
        channel
        for channel in normalized_channels
        if channel not in resolved_collectors
    ]
    if unsupported_channels:
        joined = ", ".join(unsupported_channels)
        raise ValueError(f"unsupported requested_channels: {joined}")

    return normalized_channels


def _invoke_with_supported_kwargs(function: Callable[..., object], **kwargs):
    signature = inspect.signature(function)
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
        return function(**kwargs)
    supported_kwargs = {
        name: value
        for name, value in kwargs.items()
        if name in signature.parameters
    }
    return function(**supported_kwargs)


def execute_watch_run(
    run_id: str,
    *,
    client_id: str,
    watchlist_id: str,
    requested_channels: list[str],
    collectors: dict[str, CollectorFn] | None = None,
    db_path: str | Path | None = None,
    normalization_fn: Callable[..., dict[str, object]] = run_normalization_job,
    refresh_fn: Callable[..., dict[str, object]] = refresh_tenant_artifacts,
) -> dict[str, object] | None:
    """Run the watch pipeline end-to-end, protecting the run row from orphaning."""
    resolved_collectors = dict(DEFAULT_COLLECTORS)
    if collectors:
        resolved_collectors.update(collectors)

    collected_total = 0
    collector_error_seen = False

    try:
        set_stage(run_id, "collecting", status="running", db_path=db_path)
        for channel in requested_channels:
            step_key = f"collect:{channel}"
            start_step(
                run_id,
                step_key,
                stage="collecting",
                collector_key=channel,
                db_path=db_path,
            )
            try:
                collector = resolved_collectors.get(channel)
                if collector is None:
                    raise RuntimeError(f"No watch collector configured for channel '{channel}'")

                documents = list(
                    _invoke_with_supported_kwargs(
                        collector,
                        client_id=client_id,
                        watchlist_id=watchlist_id,
                        channel=channel,
                        run_id=run_id,
                    )
                    or []
                )
                inserted = insert_watch_documents(
                    client_id=client_id,
                    collector_key=channel,
                    documents=documents,
                    run_id=run_id,
                    db_path=db_path,
                )
                collected_total += inserted
                finish_step(
                    run_id,
                    step_key,
                    status="success",
                    records_seen=inserted,
                    db_path=db_path,
                )
            except Exception as exc:
                collector_error_seen = True
                finish_step(
                    run_id,
                    step_key,
                    status="error",
                    error_message=str(exc),
                    db_path=db_path,
                )

        set_stage(run_id, "normalizing", status="running", db_path=db_path)
        start_step(run_id, "normalize", stage="normalizing", db_path=db_path)
        try:
            normalization_kwargs = {
                "client_id": client_id,
                "batch_size": max(collected_total, 1),
                "sync_run_id": run_id,
            }
            if db_path is not None:
                normalization_kwargs["db_path"] = db_path
            normalization_result = _invoke_with_supported_kwargs(
                normalization_fn,
                **normalization_kwargs,
            ) or {}
            finish_step(
                run_id,
                "normalize",
                status="success",
                records_seen=int(normalization_result.get("processed_count") or 0),
                db_path=db_path,
            )
        except Exception as exc:
            finish_step(
                run_id,
                "normalize",
                status="error",
                error_message=str(exc),
                db_path=db_path,
            )
            raise

        set_stage(run_id, "indexing", status="running", db_path=db_path)
        start_step(run_id, "index", stage="indexing", db_path=db_path)
        try:
            refresh_result = _invoke_with_supported_kwargs(
                refresh_fn,
                client_id=client_id,
                force=True,
            ) or {}
            finish_step(
                run_id,
                "index",
                status="success",
                records_seen=int(refresh_result.get("documents") or 0),
                db_path=db_path,
            )
        except Exception as exc:
            finish_step(
                run_id,
                "index",
                status="error",
                error_message=str(exc),
                db_path=db_path,
            )
            raise

        finish_run(
            run_id,
            status="partial_success" if collector_error_seen else "ready",
            records_collected=collected_total,
            db_path=db_path,
        )
        return get_watch_run(run_id, db_path=db_path)
    except Exception as exc:
        finish_run(
            run_id,
            status="error",
            records_collected=collected_total,
            error_message=str(exc),
            db_path=db_path,
        )
        return get_watch_run(run_id, db_path=db_path)


def start_watch_run(
    *,
    client_id: str,
    watchlist_id: str,
    requested_channels: list[str],
    collectors: dict[str, CollectorFn] | None = None,
    run_async: bool = True,
    db_path: str | Path | None = None,
    normalization_fn: Callable[..., dict[str, object]] = run_normalization_job,
    refresh_fn: Callable[..., dict[str, object]] = refresh_tenant_artifacts,
) -> dict[str, object] | None:
    """Create a tracked watch run, then execute it either inline or in a daemon thread."""
    normalized_channels = validate_requested_channels(
        requested_channels,
        collectors=collectors,
    )
    run_id = create_watch_run(
        client_id=client_id,
        watchlist_id=watchlist_id,
        requested_channels=normalized_channels,
        db_path=db_path,
    )
    created = get_watch_run(run_id, db_path=db_path)
    persisted_channels = list((created or {}).get("requested_channels") or normalized_channels)

    if not run_async:
        return execute_watch_run(
            run_id,
            client_id=client_id,
            watchlist_id=watchlist_id,
            requested_channels=persisted_channels,
            collectors=collectors,
            db_path=db_path,
            normalization_fn=normalization_fn,
            refresh_fn=refresh_fn,
        )

    # Expo-only caveat: a daemon thread is acceptable here to keep the HTTP path simple,
    # but it is not durable enough for production job execution.
    threading.Thread(
        target=execute_watch_run,
        kwargs={
            "run_id": run_id,
            "client_id": client_id,
            "watchlist_id": watchlist_id,
            "requested_channels": persisted_channels,
            "collectors": collectors,
            "db_path": db_path,
            "normalization_fn": normalization_fn,
            "refresh_fn": refresh_fn,
        },
        daemon=True,
    ).start()
    return created
