#!/usr/bin/env python3
"""Validate the prepared SLM V2 corpus invariants and fail closed on leakage."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from prepare_slm_v2_corpora import (
    EMAIL_RE,
    EVAL_SPLITS,
    HANDLE_RE,
    PHONE_RE,
    URL_RE,
    custom_annotation_errors,
)


DEFAULT_ROOT = Path("data/processed/slm_v2_corpora/v0.1")
DEFAULT_REGISTRY = Path("data/registry/slm_v2_sources_v0.1.json")


class ValidationError(RuntimeError):
    """Raised when prepared data violates a declared invariant."""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValidationError(f"Expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    f"Invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise ValidationError(
                    f"Expected object at {path}:{line_number}"
                )
            rows.append(value)
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_train_eligible(record: dict[str, Any]) -> bool:
    training = record["training"]
    return bool(training["language_eligible"]) or any(
        training["supervised_tasks"].values()
    )


def validate(
    root: Path,
    registry_path: Path,
    repository_root: Path,
) -> dict[str, int]:
    manifest = load_json(root / "preparation_manifest_v0.1.json")
    report = load_json(root / "quality_report_v0.1.json")
    registry = load_json(registry_path)

    for output in manifest["outputs"]:
        path = repository_root / Path(output["path"])
        if not path.is_file():
            raise ValidationError(f"Missing manifested output: {path}")
        actual_hash = sha256_file(path)
        if actual_hash != output["sha256"]:
            raise ValidationError(f"Manifest SHA-256 mismatch: {path}")
        if output["rows"] is not None:
            actual_rows = sum(
                1 for line in path.open(encoding="utf-8") if line.strip()
            )
            if actual_rows != output["rows"]:
                raise ValidationError(
                    f"Manifest row mismatch for {path}: "
                    f"{actual_rows} != {output['rows']}"
                )

    records: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    for dataset in registry["datasets"]:
        dataset_id = dataset["dataset_id"]
        dataset_records = load_jsonl(root / "normalized" / f"{dataset_id}.jsonl")
        dataset_rejects = load_jsonl(root / "rejects" / f"{dataset_id}.jsonl")
        if len(dataset_records) + len(dataset_rejects) != int(dataset["declared_rows"]):
            raise ValidationError(
                f"Source row conservation failed for {dataset_id}: "
                f"{len(dataset_records)} accepted + {len(dataset_rejects)} rejected "
                f"!= {dataset['declared_rows']} declared"
            )
        records.extend(dataset_records)
        rejects.extend(dataset_rejects)

    record_ids = [record["record_id"] for record in records]
    if len(record_ids) != len(set(record_ids)):
        raise ValidationError("record_id is not globally unique")

    video_splits: dict[str, set[str]] = defaultdict(set)
    exact_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        exact_groups[record["dedup_key"]].append(record)
        video_group = record["metadata"].get("video_group_sha256")
        if video_group:
            video_splits[video_group].add(record["split"])
        if record["split"] in EVAL_SPLITS and is_train_eligible(record):
            raise ValidationError(
                f"Protected evaluation record is TRAIN-eligible: {record['record_id']}"
            )
        reasons = record["training"]["exclusion_reasons"]
        if (
            "exact_duplicate_of_protected_eval" in reasons
            or "high_confidence_near_duplicate_of_protected_eval" in reasons
        ) and is_train_eligible(record):
            raise ValidationError(
                f"Evaluation overlap remains TRAIN-eligible: {record['record_id']}"
            )

    leaking_videos = [
        video_group for video_group, splits in video_splits.items() if len(splits) > 1
    ]
    if leaking_videos:
        raise ValidationError(
            f"{len(leaking_videos)} source video groups cross split boundaries"
        )

    for dedup_key, members in exact_groups.items():
        protected = any(member["split"] in EVAL_SPLITS for member in members)
        if protected and any(
            member["split"] == "train" and is_train_eligible(member)
            for member in members
        ):
            raise ValidationError(
                f"Exact protected-evaluation leakage for group {dedup_key[:20]}"
            )

    gold = [
        record
        for record in records
        if record["dataset"]["id"] == "ramypulse_business_gold_candidate"
    ]
    for record in gold:
        if is_train_eligible(record):
            raise ValidationError(
                f"Gold candidate entered TRAIN: {record['record_id']}"
            )
        annotation = record["task_labels"]["business_annotation_full"]
        semantic_errors = custom_annotation_errors(record["text"], annotation)
        if semantic_errors:
            raise ValidationError(
                f"Gold candidate span/reference failure for {record['record_id']}: "
                f"{semantic_errors}"
            )
        if not record["metadata"]["annotation_schema_valid"]:
            raise ValidationError(
                f"Gold candidate schema failure: {record['record_id']}"
            )

    direct_identifier_patterns = {
        "url": URL_RE,
        "email": EMAIL_RE,
        "phone": PHONE_RE,
        "handle": HANDLE_RE,
    }
    view_rows = 0
    for path in sorted((root / "views").glob("language_train_*.jsonl")):
        rows = load_jsonl(path)
        view_rows += len(rows)
        licences = {row["licence"] for row in rows}
        if len(licences) != 1:
            raise ValidationError(f"Mixed licences in view: {path}")
        for row in rows:
            for identifier_name, pattern in direct_identifier_patterns.items():
                if pattern.search(row["text"]):
                    raise ValidationError(
                        f"Unredacted {identifier_name} in {path}: "
                        f"{row['record_id']}"
                    )

    if len(records) != report["accepted_rows"]:
        raise ValidationError("Quality report accepted_rows mismatch")
    if len(rejects) != report["rejected_rows"]:
        raise ValidationError("Quality report rejected_rows mismatch")

    return {
        "records": len(records),
        "rejects": len(rejects),
        "unique_exact_keys": len(exact_groups),
        "video_groups": len(video_splits),
        "gold_candidates": len(gold),
        "language_view_rows": view_rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path.cwd(),
        help="Base directory used to resolve manifest paths.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = validate(args.root, args.registry, args.repository_root)
    except (ValidationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    print("VALIDATION PASSED")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
