#!/usr/bin/env python3
"""Acquire and verify the immutable raw corpora declared in the SLM V2 registry.

The command is intentionally limited to acquisition. It does not normalize,
merge, split, or delete any data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


DEFAULT_REGISTRY = Path("data/registry/slm_v2_sources_v0.1.json")
DEFAULT_RAW_ROOT = Path("data/raw/slm_v2")
CHUNK_SIZE = 1024 * 1024
USER_AGENT = "RamyPulse-SLM-V2-Data-Acquisition/0.1"


class AcquisitionError(RuntimeError):
    """Raised when a source cannot be acquired without violating invariants."""


def _load_registry(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        registry = json.load(handle)
    if registry.get("registry_version") != "slm_v2_sources_v0.1":
        raise AcquisitionError(f"Unsupported registry version in {path}")
    if not isinstance(registry.get("datasets"), list):
        raise AcquisitionError(f"Missing datasets list in {path}")
    return registry


def _git_blob_sha1(path: Path) -> str:
    size = path.stat().st_size
    digest = hashlib.sha1()  # noqa: S324 - Git blob identity requires SHA-1.
    digest.update(f"blob {size}\0".encode("ascii"))
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_file(path: Path, algorithm: str) -> str:
    if algorithm == "git_blob_sha1":
        return _git_blob_sha1(path)
    try:
        digest = hashlib.new(algorithm)
    except ValueError as exc:
        raise AcquisitionError(f"Unsupported checksum algorithm: {algorithm}") from exc
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify(path: Path, file_spec: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        raise AcquisitionError(f"Missing file: {path}")

    actual_size = path.stat().st_size
    expected_size = int(file_spec["expected_size"])
    if actual_size != expected_size:
        raise AcquisitionError(
            f"Size mismatch for {path}: expected {expected_size}, got {actual_size}"
        )

    source_checksum = file_spec["source_checksum"]
    algorithm = source_checksum["algorithm"].lower()
    expected_checksum = source_checksum["value"].lower()
    actual_checksum = _hash_file(path, algorithm)
    if actual_checksum != expected_checksum:
        raise AcquisitionError(
            f"{algorithm} mismatch for {path}: "
            f"expected {expected_checksum}, got {actual_checksum}"
        )

    return {
        "size": actual_size,
        "source_checksum": {
            "algorithm": algorithm,
            "value": actual_checksum,
        },
        "sha256": _hash_file(path, "sha256"),
    }


def _stream_download(
    url: str, target: Path, file_spec: dict[str, Any]
) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    part_path = target.with_name(f"{target.name}.part")
    if part_path.exists():
        raise AcquisitionError(
            f"Partial file already exists; inspect it before retrying: {part_path}"
        )

    try:
        with requests.get(
            url,
            stream=True,
            timeout=(20, 180),
            headers={"User-Agent": USER_AGENT},
        ) as response:
            response.raise_for_status()
            with part_path.open("xb") as handle:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        handle.write(chunk)
        verified = _verify(part_path, file_spec)
        os.replace(part_path, target)
        return verified
    except Exception:
        if part_path.exists():
            part_path.unlink()
        raise


def _dataset_dir(raw_root: Path, dataset: dict[str, Any]) -> Path:
    return raw_root / dataset["dataset_id"] / str(dataset["version"])


def _select_datasets(
    registry: dict[str, Any], selected_ids: set[str]
) -> list[dict[str, Any]]:
    datasets = registry["datasets"]
    known = {dataset["dataset_id"] for dataset in datasets}
    unknown = selected_ids - known
    if unknown:
        raise AcquisitionError(f"Unknown dataset id(s): {', '.join(sorted(unknown))}")
    if not selected_ids:
        return datasets
    return [dataset for dataset in datasets if dataset["dataset_id"] in selected_ids]


def acquire(
    registry_path: Path,
    raw_root: Path,
    selected_ids: set[str],
    verify_only: bool,
) -> dict[str, Any]:
    registry = _load_registry(registry_path)
    datasets = _select_datasets(registry, selected_ids)
    lock_entries: list[dict[str, Any]] = []

    for dataset in datasets:
        dataset_id = dataset["dataset_id"]
        print(f"[{dataset_id}]")
        for file_spec in dataset["files"]:
            local_source = file_spec.get("local_path")
            if local_source:
                target = Path(local_source)
                action = "verify-local"
            else:
                target = _dataset_dir(raw_root, dataset) / file_spec["filename"]
                action = "verify"
                if not target.exists():
                    if verify_only:
                        raise AcquisitionError(
                            f"Cannot verify missing remote file without downloading: {target}"
                        )
                    print(f"  download {file_spec['filename']}")
                    _stream_download(file_spec["url"], target, file_spec)
                    action = "download"

            verified = _verify(target, file_spec)
            print(
                f"  {action}: {file_spec['filename']} "
                f"({verified['size']} bytes, sha256={verified['sha256'][:12]}...)"
            )
            lock_entries.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_version": str(dataset["version"]),
                    "filename": file_spec["filename"],
                    "path": target.as_posix(),
                    "intended_use": file_spec["intended_use"],
                    "published_split": file_spec.get("published_split"),
                    **verified,
                }
            )

    return {
        "lock_version": "slm_v2_acquisition_lock_v0.1",
        "registry_version": registry["registry_version"],
        "registry_sha256": _hash_file(registry_path, "sha256"),
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "files": lock_entries,
    }


def _write_lock(raw_root: Path, lock: dict[str, Any]) -> Path:
    raw_root.mkdir(parents=True, exist_ok=True)
    lock_path = raw_root / "acquisition_lock_v0.1.json"
    temp_path = raw_root / "acquisition_lock_v0.1.json.part"
    if temp_path.exists():
        raise AcquisitionError(f"Unexpected partial lock file: {temp_path}")
    with temp_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(lock, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(temp_path, lock_path)
    return lock_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument(
        "--dataset",
        action="append",
        default=[],
        help="Dataset id to acquire; repeat to select more than one. Default: all.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify existing files and fail if a remote file is absent.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        lock = acquire(
            registry_path=args.registry,
            raw_root=args.raw_root,
            selected_ids=set(args.dataset),
            verify_only=args.verify_only,
        )
        lock_path = _write_lock(args.raw_root, lock)
    except (AcquisitionError, OSError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Verified {len(lock['files'])} files.")
    print(f"Acquisition lock: {lock_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
