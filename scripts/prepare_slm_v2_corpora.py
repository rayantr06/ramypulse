#!/usr/bin/env python3
"""Prepare the registered SLM V2 corpora without mixing licences or eval splits.

The pipeline performs conservative Unicode normalization, direct-identifier
redaction, source-label normalization, deterministic splitting, cross-corpus
exact deduplication, high-confidence near-duplicate leakage checks, and schema
validation of the RamyPulse gold candidates.

Raw files remain immutable. All outputs are reproducible derived artifacts.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

import pandas as pd
from jsonschema import Draft202012Validator


DEFAULT_REGISTRY = Path("data/registry/slm_v2_sources_v0.1.json")
DEFAULT_RAW_ROOT = Path("data/raw/slm_v2")
DEFAULT_OUTPUT_ROOT = Path("data/processed/slm_v2_corpora/v0.1")
DEFAULT_ANNOTATION_SCHEMA = Path(
    "docs/slm_v2/business_comment_annotation_v0.1.schema.json"
)

PIPELINE_VERSION = "slm_v2_preparation_v0.1"
SPLIT_SALT = "ramypulse-slm-v2-split-v0.1"
EVAL_SPLITS = {"dev", "test", "gold_dev", "gold_test", "gold_evaluation"}
TRAINABLE_INTENDED_USES = {"train_candidate"}
MAX_NEAR_BUCKET = 120
NEAR_REPORT_THRESHOLD = 0.94
NEAR_BLOCK_THRESHOLD = 0.98

URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>{}\[\]]+")
EMAIL_RE = re.compile(
    r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])"
)
HANDLE_RE = re.compile(r"(?<![\w@])@[A-Za-z0-9_\u00C0-\u024F]{2,32}\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?213[\s.\-/]?)?(?:0[\s.\-/]?)?"
    r"(?:5|6|7)(?:[\s.\-/]?\d){8}(?!\d)"
)
ZERO_WIDTH_AND_BIDI_RE = re.compile(
    "[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]"
)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WHITESPACE_RE = re.compile(r"\s+")
MOJIBAKE_MARKERS = ("Ã", "Â", "â€", "ðŸ", "Ø", "Ù")

MENDELEY_SENTIMENT = {
    0: "tres_negatif",
    1: "negatif",
    2: "neutre",
    3: "positif",
    4: "tres_positif",
}
HIRAK_SENTIMENT = {0: "negatif", 1: "positif"}
YES_NO = {"yes": True, "no": False}


class PreparationError(RuntimeError):
    """Raised when a preparation invariant cannot be satisfied."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.part")
    if temporary.exists():
        raise PreparationError(f"Unexpected partial output: {temporary}")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.part")
    if temporary.exists():
        raise PreparationError(f"Unexpected partial output: {temporary}")
    count = 0
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            )
            handle.write("\n")
            count += 1
    os.replace(temporary, path)
    return count


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise PreparationError(f"Expected a JSON object in {path}")
    return value


def load_registry(path: Path) -> dict[str, Any]:
    registry = load_json(path)
    if registry.get("registry_version") != "slm_v2_sources_v0.1":
        raise PreparationError(f"Unsupported registry version in {path}")
    return registry


def dataset_file_path(
    dataset: dict[str, Any], file_spec: dict[str, Any], raw_root: Path
) -> Path:
    if file_spec.get("local_path"):
        return Path(file_spec["local_path"])
    return (
        raw_root
        / dataset["dataset_id"]
        / str(dataset["version"])
        / file_spec["filename"]
    )


def select_data_file(
    dataset: dict[str, Any], raw_root: Path, suffix: str
) -> tuple[dict[str, Any], Path]:
    matches = [
        (spec, dataset_file_path(dataset, spec, raw_root))
        for spec in dataset["files"]
        if spec["filename"].lower().endswith(suffix.lower())
    ]
    if len(matches) != 1:
        raise PreparationError(
            f"Expected one {suffix} data file for {dataset['dataset_id']}, "
            f"found {len(matches)}"
        )
    spec, path = matches[0]
    if not path.is_file():
        raise PreparationError(f"Missing acquired file: {path}")
    return spec, path


def normalize_and_redact(raw: str) -> tuple[str, dict[str, int], list[str]]:
    if not isinstance(raw, str):
        raw = str(raw)
    text = unicodedata.normalize("NFC", raw.replace("\r\n", "\n").replace("\r", "\n"))
    flags: list[str] = []

    if "\ufffd" in text:
        flags.append("unicode_replacement_character")
    if any(marker in text for marker in MOJIBAKE_MARKERS):
        flags.append("possible_mojibake")
    if ZERO_WIDTH_AND_BIDI_RE.search(text):
        flags.append("removed_zero_width_or_bidi_control")
        text = ZERO_WIDTH_AND_BIDI_RE.sub("", text)
    if CONTROL_RE.search(text):
        flags.append("removed_control_character")
        text = CONTROL_RE.sub(" ", text)

    redactions: dict[str, int] = {}
    for name, pattern, replacement in (
        ("email", EMAIL_RE, "<EMAIL>"),
        ("url", URL_RE, "<URL>"),
        ("phone", PHONE_RE, "<PHONE>"),
        ("handle", HANDLE_RE, "<USER>"),
    ):
        text, count = pattern.subn(replacement, text)
        if count:
            redactions[name] = count
            flags.append(f"redacted_{name}")

    text = WHITESPACE_RE.sub(" ", text).strip()
    return text, redactions, sorted(set(flags))


def dedup_normal_form(text: str) -> str:
    value = unicodedata.normalize("NFKC", text).casefold()
    value = value.replace("\u0640", "")
    value = ZERO_WIDTH_AND_BIDI_RE.sub("", value)
    return WHITESPACE_RE.sub(" ", value).strip()


def stable_record_id(
    dataset_id: str,
    version: str,
    source_file: str,
    source_row: str | int,
    raw_text_sha256: str,
) -> str:
    identity = (
        f"{dataset_id}\0{version}\0{source_file}\0{source_row}\0{raw_text_sha256}"
    )
    return f"{dataset_id}:{sha256_text(identity)[:20]}"


def stable_split(stratum: str, group_key: str) -> str:
    # The stratum is accepted for call-site clarity and reporting, but it must
    # not affect the bucket. A video/text group must never cross splits merely
    # because two rows in that group carry different labels.
    del stratum
    digest = hashlib.sha256(
        f"{SPLIT_SALT}\0{group_key}".encode("utf-8")
    ).digest()
    bucket = int.from_bytes(digest[:8], "big") % 10_000
    if bucket < 8_000:
        return "train"
    if bucket < 9_000:
        return "dev"
    return "test"


def make_record(
    dataset: dict[str, Any],
    file_spec: dict[str, Any],
    source_row: str | int,
    raw_text: str,
    task_labels: dict[str, Any],
    metadata: dict[str, Any],
    split: str,
    raw_quality_flags: Iterable[str] = (),
    preserve_text_for_offsets: bool = False,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    raw_text = str(raw_text)
    raw_hash = sha256_text(raw_text)
    normalized_text, redactions, flags = normalize_and_redact(raw_text)
    text = raw_text if preserve_text_for_offsets else normalized_text
    if preserve_text_for_offsets:
        flags.append("review_only_text_preserved_for_span_integrity")
        if redactions:
            flags.append("privacy_redaction_deferred_review_only")
    flags = sorted(set(flags) | set(raw_quality_flags))
    record_id = stable_record_id(
        dataset["dataset_id"],
        str(dataset["version"]),
        file_spec["filename"],
        source_row,
        raw_hash,
    )
    if not text:
        return None, {
            "record_id": record_id,
            "dataset_id": dataset["dataset_id"],
            "source_file": file_spec["filename"],
            "source_row": source_row,
            "raw_text_sha256": raw_hash,
            "rejection_reason": "empty_after_normalization",
        }
    if "\ufffd" in text:
        return None, {
            "record_id": record_id,
            "dataset_id": dataset["dataset_id"],
            "source_file": file_spec["filename"],
            "source_row": source_row,
            "raw_text_sha256": raw_hash,
            "rejection_reason": "invalid_unicode_replacement_character",
        }

    # Deduplication still uses the privacy-safe form for review-only records.
    dedup_value = dedup_normal_form(normalized_text)
    if not dedup_value:
        return None, {
            "record_id": record_id,
            "dataset_id": dataset["dataset_id"],
            "source_file": file_spec["filename"],
            "source_row": source_row,
            "raw_text_sha256": raw_hash,
            "rejection_reason": "empty_deduplication_form",
        }

    return {
        "record_id": record_id,
        "dataset": {
            "id": dataset["dataset_id"],
            "version": str(dataset["version"]),
            "licence": dataset["licence"]["spdx"],
        },
        "source": {
            "file": file_spec["filename"],
            "row": source_row,
            "intended_use": file_spec["intended_use"],
            "published_split": file_spec.get("published_split"),
        },
        "text": text,
        "text_sha256": sha256_text(text),
        "raw_text_sha256": raw_hash,
        "dedup_key": sha256_text(dedup_value),
        "split": split,
        "task_labels": task_labels,
        "metadata": metadata,
        "quality": {
            "flags": flags,
            "privacy_redactions": redactions,
        },
        "deduplication": {},
        "training": {
            "language_eligible": False,
            "supervised_tasks": {},
            "exclusion_reasons": [],
        },
    }, None


def normalize_mendeley(
    dataset: dict[str, Any], raw_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    file_spec, path = select_data_file(dataset, raw_root, ".csv")
    frame = pd.read_csv(path, encoding="utf-8-sig")
    expected_columns = {
        "text",
        "label",
        "last_updated",
        "like_count",
        "video_url",
        "annotation_datetime",
    }
    if set(frame.columns) != expected_columns:
        raise PreparationError(f"Unexpected columns in {path}: {frame.columns.tolist()}")

    records: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        source_row = int(index) + 2
        try:
            raw_label = int(row["label"])
            label = MENDELEY_SENTIMENT[raw_label]
        except (KeyError, TypeError, ValueError):
            rejects.append(
                {
                    "dataset_id": dataset["dataset_id"],
                    "source_file": file_spec["filename"],
                    "source_row": source_row,
                    "rejection_reason": "invalid_sentiment_5_class_label",
                    "raw_label": str(row["label"]),
                }
            )
            continue

        video_url = None if pd.isna(row["video_url"]) else str(row["video_url"])
        video_group = sha256_text(video_url) if video_url else None
        preliminary_text, _, _ = normalize_and_redact(str(row["text"]))
        preliminary_key = sha256_text(dedup_normal_form(preliminary_text))
        split = stable_split(label, video_group or preliminary_key)
        like_count = None
        if not pd.isna(row["like_count"]):
            try:
                like_count = int(row["like_count"])
            except (TypeError, ValueError):
                pass
        record, rejection = make_record(
            dataset,
            file_spec,
            source_row,
            str(row["text"]),
            {
                "sentiment_5_class": {
                    "raw": raw_label,
                    "label": label,
                    "ordinal": raw_label,
                }
            },
            {
                "platform": "youtube",
                "video_group_sha256": video_group,
                "like_count": like_count,
                "collected_at": str(row["last_updated"]),
                "annotated_at": str(row["annotation_datetime"]),
            },
            split,
        )
        if record:
            records.append(record)
        elif rejection:
            rejects.append(rejection)
    return records, rejects


def normalize_toxicity(
    dataset: dict[str, Any], raw_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    file_spec, path = select_data_file(dataset, raw_root, ".xlsx")
    frame = pd.read_excel(path, sheet_name="Sheet1")
    columns = {
        str(column).strip(): column
        for column in frame.columns
    }
    required = {
        "Id",
        "comment",
        "Topic",
        "Hate speech",
        "cyberbullying التنمر الإلكتروني",
        "Offensive Language  الكلام الـمسيئ",
        "Source",
    }
    if set(columns) != required:
        raise PreparationError(f"Unexpected columns in {path}: {frame.columns.tolist()}")

    records: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        source_row = int(index) + 2
        try:
            hate_raw = str(row[columns["Hate speech"]]).strip().casefold()
            cyber_raw = str(
                row[columns["cyberbullying التنمر الإلكتروني"]]
            ).strip().casefold()
            offensive_raw = str(
                row[columns["Offensive Language  الكلام الـمسيئ"]]
            ).strip().casefold()
            labels = {
                "hate_speech": YES_NO[hate_raw],
                "cyberbullying": YES_NO[cyber_raw],
                "offensive_language": YES_NO[offensive_raw],
            }
        except KeyError:
            rejects.append(
                {
                    "dataset_id": dataset["dataset_id"],
                    "source_file": file_spec["filename"],
                    "source_row": source_row,
                    "rejection_reason": "invalid_toxicity_label",
                }
            )
            continue

        topic = str(row[columns["Topic"]]).strip()
        platform = str(row[columns["Source"]]).strip().casefold()
        raw_text = str(row[columns["comment"]])
        preliminary_text, _, _ = normalize_and_redact(raw_text)
        group_key = sha256_text(dedup_normal_form(preliminary_text))
        stratum = (
            f"{platform}|{int(labels['hate_speech'])}|"
            f"{int(labels['cyberbullying'])}|{int(labels['offensive_language'])}"
        )
        split = stable_split(stratum, group_key)
        source_id = row[columns["Id"]]
        if isinstance(source_id, float) and math.isnan(source_id):
            source_id_hash = None
        elif source_id is None:
            source_id_hash = None
        else:
            source_id_hash = sha256_text(str(source_id))
        record, rejection = make_record(
            dataset,
            file_spec,
            source_row,
            raw_text,
            {"toxicity_multilabel": labels},
            {
                "source_id_sha256": source_id_hash,
                "topic": topic,
                "platform": platform,
            },
            split,
        )
        if record:
            records.append(record)
        elif rejection:
            rejects.append(rejection)
    return records, rejects


def normalize_hirak(
    dataset: dict[str, Any], raw_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    file_spec, path = select_data_file(dataset, raw_root, ".xlsx")
    frame = pd.read_excel(path, sheet_name="AlgD_dataset")
    if frame.columns.tolist() != ["label,text"]:
        raise PreparationError(f"Unexpected columns in {path}: {frame.columns.tolist()}")

    records: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    column = frame.columns[0]
    for index, value in frame[column].items():
        source_row = int(index) + 2
        raw_cell = "" if pd.isna(value) else str(value)
        parsed = next(csv.reader([raw_cell]))
        if len(parsed) < 2:
            rejects.append(
                {
                    "dataset_id": dataset["dataset_id"],
                    "source_file": file_spec["filename"],
                    "source_row": source_row,
                    "raw_text_sha256": sha256_text(raw_cell),
                    "rejection_reason": "malformed_single_cell_csv_row",
                    "field_count": len(parsed),
                }
            )
            continue
        raw_label_text, raw_text = parsed[0], ",".join(parsed[1:])
        try:
            raw_label = int(raw_label_text)
            label = HIRAK_SENTIMENT[raw_label]
        except (KeyError, TypeError, ValueError):
            rejects.append(
                {
                    "dataset_id": dataset["dataset_id"],
                    "source_file": file_spec["filename"],
                    "source_row": source_row,
                    "raw_text_sha256": sha256_text(raw_text),
                    "rejection_reason": "invalid_binary_sentiment_label",
                    "raw_label": raw_label_text,
                }
            )
            continue
        preliminary_text, _, _ = normalize_and_redact(raw_text)
        split = stable_split(label, sha256_text(dedup_normal_form(preliminary_text)))
        record, rejection = make_record(
            dataset,
            file_spec,
            source_row,
            raw_text,
            {"sentiment_binary": {"raw": raw_label, "label": label}},
            {"domain": "hirak_2019", "platform": "mixed_social"},
            split,
        )
        if record:
            records.append(record)
        elif rejection:
            rejects.append(rejection)
    return records, rejects


def conllu_sentences(path: Path) -> Iterator[tuple[int, dict[str, str], int]]:
    comments: dict[str, str] = {}
    token_count = 0
    sentence_index = 0
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if line.startswith("# "):
                body = line[2:]
                if " = " in body:
                    key, value = body.split(" = ", 1)
                    comments[key] = value
            elif line and not line.startswith("#"):
                fields = line.split("\t")
                if fields and "-" not in fields[0] and "." not in fields[0]:
                    token_count += 1
            elif not line and comments:
                sentence_index += 1
                yield sentence_index, comments, token_count
                comments = {}
                token_count = 0
    if comments:
        sentence_index += 1
        yield sentence_index, comments, token_count


def normalize_narabizi(
    dataset: dict[str, Any], raw_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    conllu_specs = [
        spec for spec in dataset["files"] if spec["filename"].endswith(".conllu")
    ]
    for file_spec in conllu_specs:
        path = dataset_file_path(dataset, file_spec, raw_root)
        if not path.is_file():
            raise PreparationError(f"Missing acquired file: {path}")
        published_split = file_spec.get("published_split")
        if published_split not in {"train", "dev", "test"}:
            raise PreparationError(f"Missing published split for {path}")
        for sentence_index, comments, token_count in conllu_sentences(path):
            raw_text = comments.get("text")
            if not raw_text:
                rejects.append(
                    {
                        "dataset_id": dataset["dataset_id"],
                        "source_file": file_spec["filename"],
                        "source_row": sentence_index,
                        "rejection_reason": "missing_conllu_text_comment",
                    }
                )
                continue
            offensive_raw = comments.get("offensive_classification")
            task_labels: dict[str, Any] = {
                "arabizi_language": {"variety": "algerian_arabizi"}
            }
            if offensive_raw in {"0", "1"}:
                task_labels["offensive_classification"] = {
                    "raw": int(offensive_raw),
                    "label_semantics": "preserved_raw_source_value",
                }
            elif offensive_raw is not None:
                task_labels["offensive_classification"] = {
                    "raw": offensive_raw,
                    "label_semantics": "preserved_raw_source_value",
                }
            translation_fr = comments.get("trad_fr")
            if translation_fr is not None:
                translation_fr, _, _ = normalize_and_redact(translation_fr)
            record, rejection = make_record(
                dataset,
                file_spec,
                sentence_index,
                raw_text,
                task_labels,
                {
                    "sent_id": comments.get("sent_id"),
                    "source_file_id": comments.get("file"),
                    "translation_fr": translation_fr,
                    "token_count": token_count,
                    "platform": "web_ugc",
                },
                published_split,
            )
            if record:
                records.append(record)
            elif rejection:
                rejects.append(rejection)
    return records, rejects


def iter_annotation_evidence(annotation: dict[str, Any]) -> Iterator[dict[str, Any]]:
    sentiment = annotation.get("sentiment")
    if isinstance(sentiment, dict):
        for evidence in sentiment.get("evidence", []):
            if isinstance(evidence, dict):
                yield evidence
    for collection_name in ("aspects", "alerts"):
        for item in annotation.get(collection_name, []):
            if isinstance(item, dict):
                for evidence in item.get("evidence", []):
                    if isinstance(evidence, dict):
                        yield evidence


def custom_annotation_errors(text: str, annotation: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entity_ids = {
        entity.get("id")
        for entity in annotation.get("entities", [])
        if isinstance(entity, dict)
    }
    for entity in annotation.get("entities", []):
        if not isinstance(entity, dict) or entity.get("source") != "texte":
            continue
        start, end, mention = (
            entity.get("start"),
            entity.get("end"),
            entity.get("mention"),
        )
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or not 0 <= start < end <= len(text)
            or text[start:end] != mention
        ):
            errors.append(f"invalid_entity_span:{entity.get('id')}")

    for index, evidence in enumerate(iter_annotation_evidence(annotation), start=1):
        start, end, evidence_text = (
            evidence.get("start"),
            evidence.get("end"),
            evidence.get("text"),
        )
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or not 0 <= start < end <= len(text)
            or text[start:end] != evidence_text
        ):
            errors.append(f"invalid_evidence_span:{index}")

    sentiment = annotation.get("sentiment", {})
    for target_id in sentiment.get("target_entity_ids", []):
        if target_id not in entity_ids:
            errors.append(f"unknown_sentiment_target:{target_id}")
    for collection_name in ("aspects", "alerts"):
        for item in annotation.get(collection_name, []):
            target_id = item.get("target_entity_id")
            if target_id is not None and target_id not in entity_ids:
                errors.append(f"unknown_{collection_name}_target:{target_id}")
    return sorted(set(errors))


def normalize_business_seed_pool(
    dataset: dict[str, Any], raw_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    del raw_root
    file_spec = dataset["files"][0]
    path = Path(file_spec["local_path"])
    if not path.is_file():
        raise PreparationError(f"Missing local business seed pool: {path}")
    expected_keys = {
        "aspect",
        "brand",
        "sentiment_label",
        "source",
        "text",
        "topic",
    }
    records: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                rejects.append(
                    {
                        "dataset_id": dataset["dataset_id"],
                        "source_file": file_spec["filename"],
                        "source_row": line_number,
                        "rejection_reason": "invalid_json",
                        "detail": str(exc),
                    }
                )
                continue
            if not isinstance(item, dict) or set(item) != expected_keys:
                rejects.append(
                    {
                        "dataset_id": dataset["dataset_id"],
                        "source_file": file_spec["filename"],
                        "source_row": line_number,
                        "rejection_reason": "unexpected_seed_record_shape",
                        "observed_keys": (
                            sorted(item) if isinstance(item, dict) else None
                        ),
                    }
                )
                continue
            raw_text = item.get("text")
            if not isinstance(raw_text, str):
                rejects.append(
                    {
                        "dataset_id": dataset["dataset_id"],
                        "source_file": file_spec["filename"],
                        "source_row": line_number,
                        "rejection_reason": "missing_text",
                    }
                )
                continue
            preliminary_text, _, _ = normalize_and_redact(raw_text)
            fold_key = sha256_text(dedup_normal_form(preliminary_text))
            sampling_fold = int(fold_key[:8], 16) % 10
            record, rejection = make_record(
                dataset,
                file_spec,
                line_number,
                raw_text,
                {},
                {
                    "context": {
                        "source": item.get("source"),
                        "topic": item.get("topic"),
                        "brand": item.get("brand"),
                    },
                    "legacy_weak_labels_not_for_model_target": {
                        "sentiment": item.get("sentiment_label"),
                        "aspect": item.get("aspect"),
                    },
                    "sampling_fold": sampling_fold,
                },
                "annotation_pool",
                (
                    "legacy_weak_labels_sampling_only",
                    "source_rights_unverified",
                ),
            )
            if record:
                records.append(record)
            elif rejection:
                rejects.append(rejection)
    return records, rejects


def normalize_gold_candidate(
    dataset: dict[str, Any],
    raw_root: Path,
    annotation_validator: Draft202012Validator,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    del raw_root
    candidate_specs = [
        spec
        for spec in dataset["files"]
        if spec["filename"] == "business_comments_gold_candidate_v0.1.jsonl"
    ]
    if len(candidate_specs) != 1:
        raise PreparationError("Missing unique combined gold-candidate file")
    file_spec = candidate_specs[0]
    path = Path(file_spec["local_path"])
    if not path.is_file():
        raise PreparationError(f"Missing local gold candidate: {path}")
    split_by_candidate_id: dict[str, str] = {}
    for partition_spec in dataset["files"]:
        published_split = partition_spec.get("published_split")
        if published_split not in {"gold_dev", "gold_test"}:
            continue
        partition_path = Path(partition_spec["local_path"])
        if not partition_path.is_file():
            raise PreparationError(f"Missing gold partition index: {partition_path}")
        with partition_path.open("r", encoding="utf-8") as partition_handle:
            for partition_line in partition_handle:
                if not partition_line.strip():
                    continue
                partition_item = json.loads(partition_line)
                candidate_id = partition_item.get("record_id")
                if not isinstance(candidate_id, str):
                    raise PreparationError(
                        f"Missing record_id in gold partition: {partition_path}"
                    )
                if candidate_id in split_by_candidate_id:
                    raise PreparationError(
                        f"Gold record appears in multiple partitions: {candidate_id}"
                    )
                split_by_candidate_id[candidate_id] = published_split
    if len(split_by_candidate_id) != int(dataset["declared_rows"]):
        raise PreparationError(
            "Gold DEV/TEST partition coverage does not match declared rows"
        )

    records: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                rejects.append(
                    {
                        "dataset_id": dataset["dataset_id"],
                        "source_file": file_spec["filename"],
                        "source_row": line_number,
                        "rejection_reason": "invalid_json",
                        "detail": str(exc),
                    }
                )
                continue
            raw_text = item.get("text")
            annotation = item.get("annotation")
            if not isinstance(raw_text, str) or not isinstance(annotation, dict):
                rejects.append(
                    {
                        "dataset_id": dataset["dataset_id"],
                        "source_file": file_spec["filename"],
                        "source_row": line_number,
                        "rejection_reason": "missing_text_or_annotation",
                    }
                )
                continue
            schema_errors = sorted(
                error.message for error in annotation_validator.iter_errors(annotation)
            )
            semantic_errors = custom_annotation_errors(raw_text, annotation)
            provenance = item.get("provenance", {})
            candidate_record_id = item.get("record_id")
            if candidate_record_id not in split_by_candidate_id:
                rejects.append(
                    {
                        "dataset_id": dataset["dataset_id"],
                        "source_file": file_spec["filename"],
                        "source_row": line_number,
                        "rejection_reason": "missing_gold_partition_assignment",
                    }
                )
                continue
            record, rejection = make_record(
                dataset,
                file_spec,
                line_number,
                raw_text,
                {"business_annotation_full": annotation},
                {
                    "candidate_record_id": candidate_record_id,
                    "candidate_schema_version": item.get("schema_version"),
                    "context": item.get("context"),
                    "review_status": provenance.get("review_status"),
                    "draft_provider": provenance.get("draft_provider"),
                    "draft_model": provenance.get("draft_model"),
                    "annotation_schema_valid": not schema_errors,
                    "annotation_semantic_valid": not semantic_errors,
                    "annotation_schema_errors": schema_errors,
                    "annotation_semantic_errors": semantic_errors,
                },
                split_by_candidate_id[candidate_record_id],
                ("human_review_required",),
                preserve_text_for_offsets=True,
            )
            if record:
                records.append(record)
            elif rejection:
                rejects.append(rejection)
    return records, rejects


def task_value_signature(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def apply_exact_deduplication(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_key[record["dedup_key"]].append(record)

    exact_duplicate_groups = 0
    records_in_duplicate_groups = 0
    train_eval_overlaps = 0
    for dedup_key, members in by_key.items():
        members.sort(key=lambda row: row["record_id"])
        protected = [member for member in members if member["split"] in EVAL_SPLITS]
        if len(members) > 1:
            exact_duplicate_groups += 1
            records_in_duplicate_groups += len(members)
        if protected and any(member["split"] == "train" for member in members):
            train_eval_overlaps += 1
        canonical = (protected or members)[0]
        for member in members:
            member["deduplication"].update(
                {
                    "exact_group_id": dedup_key[:20],
                    "exact_group_size": len(members),
                    "exact_canonical_record_id": canonical["record_id"],
                    "overlaps_protected_split": bool(protected),
                }
            )
            if member["split"] == "train" and protected:
                member["training"]["exclusion_reasons"].append(
                    "exact_duplicate_of_protected_eval"
                )

    # Language-adaptation views are deduplicated within each licence boundary.
    language_candidates: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if (
            record["split"] == "train"
            and record["source"]["intended_use"] in TRAINABLE_INTENDED_USES
            and not record["training"]["exclusion_reasons"]
        ):
            key = (record["dataset"]["licence"], record["dedup_key"])
            language_candidates[key].append(record)
    for candidates in language_candidates.values():
        candidates.sort(key=lambda row: row["record_id"])
        candidates[0]["training"]["language_eligible"] = True
        for duplicate in candidates[1:]:
            duplicate["training"]["exclusion_reasons"].append(
                "exact_duplicate_same_licence_language_view"
            )

    # Supervised rows are deduplicated per task. Conflicting labels are quarantined.
    task_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if (
            record["split"] == "train"
            and record["source"]["intended_use"] in TRAINABLE_INTENDED_USES
            and "exact_duplicate_of_protected_eval"
            not in record["training"]["exclusion_reasons"]
        ):
            for task_name in record["task_labels"]:
                task_groups[(task_name, record["dedup_key"])].append(record)

    task_label_conflicts = 0
    for (task_name, _), members in task_groups.items():
        signatures = {
            task_value_signature(member["task_labels"][task_name]) for member in members
        }
        if len(signatures) > 1:
            task_label_conflicts += 1
            for member in members:
                member["training"]["supervised_tasks"][task_name] = False
                member["training"]["exclusion_reasons"].append(
                    f"conflicting_exact_duplicate_label:{task_name}"
                )
            continue
        members.sort(key=lambda row: row["record_id"])
        members[0]["training"]["supervised_tasks"][task_name] = True
        for duplicate in members[1:]:
            duplicate["training"]["supervised_tasks"][task_name] = False
            duplicate["training"]["exclusion_reasons"].append(
                f"exact_duplicate_same_task:{task_name}"
            )

    for record in records:
        record["training"]["exclusion_reasons"] = sorted(
            set(record["training"]["exclusion_reasons"])
        )
    return {
        "unique_exact_keys": len(by_key),
        "exact_duplicate_groups": exact_duplicate_groups,
        "records_in_exact_duplicate_groups": records_in_duplicate_groups,
        "exact_train_eval_overlap_groups": train_eval_overlaps,
        "task_label_conflict_groups": task_label_conflicts,
    }


def simhash64(text: str) -> int | None:
    compact = "".join(
        character
        for character in unicodedata.normalize("NFKC", text).casefold()
        if character.isalnum()
    )
    if len(compact) < 20:
        return None
    shingles = {compact[index : index + 5] for index in range(len(compact) - 4)}
    weights = [0] * 64
    for shingle in shingles:
        value = int.from_bytes(
            hashlib.blake2b(shingle.encode("utf-8"), digest_size=8).digest(), "big"
        )
        for bit in range(64):
            weights[bit] += 1 if value & (1 << bit) else -1
    fingerprint = 0
    for bit, weight in enumerate(weights):
        if weight >= 0:
            fingerprint |= 1 << bit
    return fingerprint


def normalized_similarity_text(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKC", text).casefold()
        if character.isalnum() or character.isspace()
    )


def find_near_duplicates(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    exact_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        exact_groups[record["dedup_key"]].append(record)
    representatives: dict[str, dict[str, Any]] = {}
    for dedup_key, members in exact_groups.items():
        members.sort(key=lambda row: row["record_id"])
        protected = [member for member in members if member["split"] in EVAL_SPLITS]
        representatives[dedup_key] = (protected or members)[0]
    unique_records = sorted(representatives.values(), key=lambda row: row["record_id"])
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    fingerprints: list[int | None] = []
    comparable_texts: list[str] = []
    candidate_pairs: set[tuple[int, int]] = set()
    hot_bucket_skips = 0

    for index, record in enumerate(unique_records):
        fingerprint = simhash64(record["text"])
        fingerprints.append(fingerprint)
        comparable_text = normalized_similarity_text(record["text"])
        comparable_texts.append(comparable_text)
        if fingerprint is None:
            continue
        for band in range(4):
            value = (fingerprint >> (band * 16)) & 0xFFFF
            bucket = buckets[(band, value)]
            if len(bucket) <= MAX_NEAR_BUCKET:
                for previous in bucket:
                    pair = (previous, index)
                    candidate_pairs.add(pair)
            else:
                hot_bucket_skips += 1
            bucket.append(index)

    pairs: list[dict[str, Any]] = []
    blocking_dedup_keys: set[str] = set()
    for left_index, right_index in sorted(candidate_pairs):
        left_fingerprint = fingerprints[left_index]
        right_fingerprint = fingerprints[right_index]
        if left_fingerprint is None or right_fingerprint is None:
            continue
        if (left_fingerprint ^ right_fingerprint).bit_count() > 6:
            continue
        left_text = comparable_texts[left_index]
        right_text = comparable_texts[right_index]
        if not left_text or not right_text:
            continue
        length_ratio = min(len(left_text), len(right_text)) / max(
            len(left_text), len(right_text)
        )
        if length_ratio < 0.86:
            continue
        similarity = difflib.SequenceMatcher(
            None, left_text, right_text, autojunk=False
        ).ratio()
        if similarity < NEAR_REPORT_THRESHOLD:
            continue
        left = unique_records[left_index]
        right = unique_records[right_index]
        protected_train_pair = (
            left["split"] in EVAL_SPLITS and right["split"] == "train"
        ) or (right["split"] in EVAL_SPLITS and left["split"] == "train")
        blocking = protected_train_pair and similarity >= NEAR_BLOCK_THRESHOLD
        if blocking:
            train_record = right if right["split"] == "train" else left
            blocking_dedup_keys.add(train_record["dedup_key"])
        pairs.append(
            {
                "left_record_id": left["record_id"],
                "right_record_id": right["record_id"],
                "left_dataset_id": left["dataset"]["id"],
                "right_dataset_id": right["dataset"]["id"],
                "left_split": left["split"],
                "right_split": right["split"],
                "similarity": round(similarity, 6),
                "protected_train_overlap": protected_train_pair,
                "blocks_training": blocking,
            }
        )

    blocking_record_ids: set[str] = set()
    for record in records:
        if record["split"] != "train" or record["dedup_key"] not in blocking_dedup_keys:
            continue
        blocking_record_ids.add(record["record_id"])
        record["training"]["language_eligible"] = False
        for task_name in list(record["training"]["supervised_tasks"]):
            record["training"]["supervised_tasks"][task_name] = False
        record["training"]["exclusion_reasons"].append(
            "high_confidence_near_duplicate_of_protected_eval"
        )
        record["training"]["exclusion_reasons"] = sorted(
            set(record["training"]["exclusion_reasons"])
        )

    return pairs, {
        "simhash_unique_records_considered": len(unique_records),
        "simhash_candidate_pairs": len(candidate_pairs),
        "near_duplicate_pairs_reported": len(pairs),
        "near_protected_train_pairs": sum(
            pair["protected_train_overlap"] for pair in pairs
        ),
        "near_pairs_blocking_training": sum(pair["blocks_training"] for pair in pairs),
        "records_blocked_by_near_eval_overlap": len(blocking_record_ids),
        "hot_bucket_skips": hot_bucket_skips,
        "report_threshold": NEAR_REPORT_THRESHOLD,
        "blocking_threshold": NEAR_BLOCK_THRESHOLD,
    }


def flatten_counts(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(), key=str)}


def build_quality_report(
    registry: dict[str, Any],
    records: list[dict[str, Any]],
    rejects: list[dict[str, Any]],
    exact_stats: dict[str, Any],
    near_stats: dict[str, Any],
) -> dict[str, Any]:
    datasets: dict[str, Any] = {}
    for dataset in registry["datasets"]:
        dataset_id = dataset["dataset_id"]
        rows = [record for record in records if record["dataset"]["id"] == dataset_id]
        dataset_rejects = [
            rejection
            for rejection in rejects
            if rejection["dataset_id"] == dataset_id
        ]
        label_counts: dict[str, Counter[str]] = defaultdict(Counter)
        for row in rows:
            for task_name, value in row["task_labels"].items():
                label_counts[task_name][task_value_signature(value)] += 1
        privacy_counts: Counter[str] = Counter()
        flag_counts: Counter[str] = Counter()
        for row in rows:
            privacy_counts.update(row["quality"]["privacy_redactions"])
            flag_counts.update(row["quality"]["flags"])
        datasets[dataset_id] = {
            "declared_rows": dataset["declared_rows"],
            "accepted_rows": len(rows),
            "rejected_rows": len(dataset_rejects),
            "split_counts": flatten_counts(Counter(row["split"] for row in rows)),
            "licence": dataset["licence"]["spdx"],
            "label_counts": {
                task: flatten_counts(counts) for task, counts in sorted(label_counts.items())
            },
            "privacy_redactions": flatten_counts(privacy_counts),
            "quality_flags": flatten_counts(flag_counts),
            "rejection_reasons": flatten_counts(
                Counter(row["rejection_reason"] for row in dataset_rejects)
            ),
            "language_train_eligible": sum(
                bool(row["training"]["language_eligible"]) for row in rows
            ),
            "supervised_train_eligible": {
                task: sum(
                    row["training"]["supervised_tasks"].get(task) is True for row in rows
                )
                for task in sorted(
                    {
                        task
                        for row in rows
                        for task in row["training"]["supervised_tasks"]
                    }
                )
            },
        }

    gold_rows = [
        row
        for row in records
        if row["dataset"]["id"] == "ramypulse_business_gold_candidate"
    ]
    return {
        "pipeline_version": PIPELINE_VERSION,
        "registry_version": registry["registry_version"],
        "source_rows_declared": sum(
            int(dataset["declared_rows"]) for dataset in registry["datasets"]
        ),
        "accepted_rows": len(records),
        "rejected_rows": len(rejects),
        "split_counts": flatten_counts(Counter(row["split"] for row in records)),
        "licence_counts": flatten_counts(
            Counter(row["dataset"]["licence"] for row in records)
        ),
        "datasets": datasets,
        "deduplication": {**exact_stats, **near_stats},
        "gold_candidate_validation": {
            "rows": len(gold_rows),
            "schema_valid": sum(
                bool(row["metadata"].get("annotation_schema_valid")) for row in gold_rows
            ),
            "semantic_span_valid": sum(
                bool(row["metadata"].get("annotation_semantic_valid"))
                for row in gold_rows
            ),
            "review_status_counts": flatten_counts(
                Counter(row["metadata"].get("review_status") for row in gold_rows)
            ),
        },
        "policy": {
            "raw_files_modified": False,
            "published_dev_test_preserved": True,
            "gold_candidate_used_for_training": False,
            "licence_views_physically_separated": True,
            "near_duplicate_method": (
                "64-bit character-5-gram SimHash LSH, followed by exact "
                "SequenceMatcher verification"
            ),
            "near_duplicate_limit": (
                "Heuristic screening, not a semantic-duplicate guarantee; reported "
                "pairs require audit."
            ),
        },
    }


def write_outputs(
    output_root: Path,
    registry: dict[str, Any],
    registry_path: Path,
    records: list[dict[str, Any]],
    rejects: list[dict[str, Any]],
    near_pairs: list[dict[str, Any]],
    report: dict[str, Any],
) -> dict[str, Any]:
    output_files: list[dict[str, Any]] = []

    def write_rows(relative_path: Path, rows: Iterable[dict[str, Any]]) -> None:
        path = output_root / relative_path
        count = atomic_write_jsonl(path, rows)
        output_files.append(
            {
                "path": path.as_posix(),
                "rows": count,
                "sha256": sha256_file(path),
            }
        )

    for dataset in registry["datasets"]:
        dataset_id = dataset["dataset_id"]
        write_rows(
            Path("normalized") / f"{dataset_id}.jsonl",
            (
                row
                for row in records
                if row["dataset"]["id"] == dataset_id
            ),
        )
        write_rows(
            Path("rejects") / f"{dataset_id}.jsonl",
            (
                row
                for row in rejects
                if row["dataset_id"] == dataset_id
            ),
        )

    write_rows(Path("audit") / "near_duplicate_pairs.jsonl", near_pairs)

    licences = sorted(
        {
            row["dataset"]["licence"]
            for row in records
            if row["training"]["language_eligible"]
        }
    )
    for licence in licences:
        slug = licence.casefold().replace("-", "_")
        write_rows(
            Path("views") / f"language_train_{slug}.jsonl",
            (
                {
                    "record_id": row["record_id"],
                    "dataset_id": row["dataset"]["id"],
                    "text": row["text"],
                    "licence": row["dataset"]["licence"],
                }
                for row in records
                if row["training"]["language_eligible"]
                and row["dataset"]["licence"] == licence
            ),
        )

    report_path = output_root / "quality_report_v0.1.json"
    atomic_write_json(report_path, report)
    output_files.append(
        {
            "path": report_path.as_posix(),
            "rows": None,
            "sha256": sha256_file(report_path),
        }
    )

    manifest = {
        "manifest_version": "slm_v2_preparation_manifest_v0.1",
        "pipeline_version": PIPELINE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry": {
            "path": registry_path.as_posix(),
            "sha256": sha256_file(registry_path),
            "version": registry["registry_version"],
        },
        "outputs": output_files,
        "invariants": [
            "Raw source files were read-only inputs.",
            "Published NArabizi DEV and TEST were preserved.",
            "RamyPulse single-reviewer candidates remained evaluation/review-only.",
            "Language-adaptation views were physically separated by SPDX licence.",
            "Direct URL, email, phone, and handle patterns were replaced in trainable text.",
            "Review-only structured annotations preserved source text so evidence offsets remain valid.",
            "Exact protected-evaluation overlaps were excluded from TRAIN.",
            "High-confidence near protected-evaluation overlaps were excluded from TRAIN.",
        ],
    }
    manifest_path = output_root / "preparation_manifest_v0.1.json"
    atomic_write_json(manifest_path, manifest)
    return manifest


def prepare(
    registry_path: Path,
    raw_root: Path,
    output_root: Path,
    annotation_schema_path: Path,
    skip_near_duplicates: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    registry = load_registry(registry_path)
    annotation_schema = load_json(annotation_schema_path)
    annotation_validator = Draft202012Validator(annotation_schema)

    normalizers = {
        "dz_sentiment_mendeley_45k": normalize_mendeley,
        "algd_toxicity_speech": normalize_toxicity,
        "dz_sentiment_hirak_11760": normalize_hirak,
        "narabizi_ud": normalize_narabizi,
        "ramypulse_business_seed_pool": normalize_business_seed_pool,
    }
    records: list[dict[str, Any]] = []
    rejects: list[dict[str, Any]] = []
    for dataset in registry["datasets"]:
        dataset_id = dataset["dataset_id"]
        print(f"[{dataset_id}] normalize")
        if dataset_id == "ramypulse_business_gold_candidate":
            dataset_records, dataset_rejects = normalize_gold_candidate(
                dataset, raw_root, annotation_validator
            )
        elif dataset_id in normalizers:
            dataset_records, dataset_rejects = normalizers[dataset_id](
                dataset, raw_root
            )
        else:
            raise PreparationError(f"No normalizer for registered dataset: {dataset_id}")
        print(
            f"  accepted={len(dataset_records)} rejected={len(dataset_rejects)}"
        )
        records.extend(dataset_records)
        rejects.extend(dataset_rejects)

    print("[deduplication] exact")
    exact_stats = apply_exact_deduplication(records)
    if skip_near_duplicates:
        near_pairs: list[dict[str, Any]] = []
        near_stats = {
            "skipped": True,
            "near_duplicate_pairs_reported": 0,
            "near_pairs_blocking_training": 0,
        }
    else:
        print("[deduplication] near-duplicate screening")
        near_pairs, near_stats = find_near_duplicates(records)

    records.sort(key=lambda row: (row["dataset"]["id"], row["record_id"]))
    rejects.sort(
        key=lambda row: (
            row["dataset_id"],
            row.get("source_file", ""),
            str(row.get("source_row", "")),
        )
    )
    report = build_quality_report(
        registry, records, rejects, exact_stats, near_stats
    )
    print("[outputs] write normalized corpora, audit, report, and licence views")
    manifest = write_outputs(
        output_root,
        registry,
        registry_path,
        records,
        rejects,
        near_pairs,
        report,
    )
    return report, manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--annotation-schema", type=Path, default=DEFAULT_ANNOTATION_SCHEMA
    )
    parser.add_argument(
        "--skip-near-duplicates",
        action="store_true",
        help="Skip heuristic near-duplicate screening (exact dedup still runs).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report, manifest = prepare(
            args.registry,
            args.raw_root,
            args.output_root,
            args.annotation_schema,
            args.skip_near_duplicates,
        )
    except (PreparationError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"Prepared {report['accepted_rows']} rows; "
        f"rejected {report['rejected_rows']}."
    )
    print(
        f"Exact duplicate groups: "
        f"{report['deduplication']['exact_duplicate_groups']}."
    )
    print(
        f"Near duplicate pairs reported: "
        f"{report['deduplication']['near_duplicate_pairs_reported']}."
    )
    print(f"Manifest outputs: {len(manifest['outputs'])}.")
    print(f"Output root: {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
