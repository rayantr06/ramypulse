"""Create deterministic, balanced DEV/TEST splits for the gold candidate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = (
    ROOT
    / "data"
    / "processed"
    / "slm_v2_gold"
    / "business_comments_gold_candidate_v0.1.jsonl"
)
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed" / "slm_v2_gold"
DEFAULT_MANIFEST = (
    ROOT / "docs" / "slm_v2" / "gold_v0.1" / "split_manifest.json"
)
RANDOM_SEED = 20260729
SEARCH_ITERATIONS = 150_000


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def features(record: dict[str, Any]) -> set[str]:
    annotation = record["annotation"]
    context = record["context"]
    values = {
        f"source={context['source']}",
        f"topic={context['topic']}",
        f"sentiment={annotation['sentiment']['label']}",
        f"relevance={annotation['business_relevance']}",
        f"language={annotation['language']['dominant']}",
        f"exploitable={annotation['is_exploitable']}",
        f"has_alert={bool(annotation['alerts'])}",
        f"has_aspect={bool(annotation['aspects'])}",
        f"sarcasm={annotation['sentiment']['sarcasm']}",
    }
    values.update(f"intent={intent}" for intent in annotation["intents"])
    values.update(
        f"aspect_family={aspect['family']}" for aspect in annotation["aspects"]
    )
    values.update(f"alert_type={alert['type']}" for alert in annotation["alerts"])
    return values


def split_loss(
    dev_indices: set[int],
    record_features: list[set[str]],
    totals: Counter[str],
) -> float:
    dev_counts: Counter[str] = Counter(
        feature
        for index in dev_indices
        for feature in record_features[index]
    )
    loss = 0.0
    for feature, total in totals.items():
        if total < 2:
            continue
        target = total / 2
        deviation = abs(dev_counts[feature] - target)
        prefix = feature.split("=", 1)[0]
        if prefix in {
            "source",
            "topic",
            "sentiment",
            "relevance",
            "language",
            "exploitable",
            "has_alert",
            "has_aspect",
            "sarcasm",
        }:
            weight = 5.0
        elif prefix in {"aspect_family", "alert_type"}:
            weight = 2.5
        else:
            weight = 1.0
        if total <= 10:
            weight *= 1.5
        loss += weight * deviation / math.sqrt(total)
    return loss


def find_balanced_split(
    records: list[dict[str, Any]],
) -> tuple[set[int], float]:
    if len(records) != 100:
        raise ValueError(f"100 enregistrements attendus, trouvé {len(records)}")
    record_features = [features(record) for record in records]
    totals: Counter[str] = Counter(
        feature for values in record_features for feature in values
    )
    positions_by_feature: dict[str, set[int]] = {
        feature: {
            index
            for index, values in enumerate(record_features)
            if feature in values
        }
        for feature in totals
    }
    rng = random.Random(RANDOM_SEED)
    best_indices: set[int] | None = None
    best_loss = float("inf")

    all_indices = list(range(len(records)))
    for _ in range(SEARCH_ITERATIONS):
        candidate = set(rng.sample(all_indices, 50))
        exact_half_features = {
            "source=ramypulse_v1_facebook",
            "has_alert=True",
            "sentiment=mixte",
            "language=darija_arabizi",
            "topic=economy",
            "topic=health",
            "topic=education",
        }
        if any(
            len(candidate & positions_by_feature[feature]) != totals[feature] // 2
            for feature in exact_half_features
        ):
            continue
        if len(candidate & positions_by_feature["exploitable=False"]) not in {2, 3}:
            continue
        loss = split_loss(candidate, record_features, totals)
        if loss < best_loss:
            best_indices = candidate
            best_loss = loss
            if best_loss == 0:
                break
    if best_indices is None:
        raise RuntimeError("Aucun split généré")
    return best_indices, best_loss


def distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(rows),
        "sources": dict(Counter(row["context"]["source"] for row in rows)),
        "topics": dict(Counter(row["context"]["topic"] for row in rows)),
        "sentiment": dict(
            Counter(row["annotation"]["sentiment"]["label"] for row in rows)
        ),
        "business_relevance": dict(
            Counter(row["annotation"]["business_relevance"] for row in rows)
        ),
        "language": dict(
            Counter(row["annotation"]["language"]["dominant"] for row in rows)
        ),
        "exploitable": dict(
            Counter(
                str(row["annotation"]["is_exploitable"]).lower() for row in rows
            )
        ),
        "has_alert": dict(
            Counter(str(bool(row["annotation"]["alerts"])).lower() for row in rows)
        ),
        "aspect_families": dict(
            Counter(
                aspect["family"]
                for row in rows
                for aspect in row["annotation"]["aspects"]
            )
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crée les splits gold_dev/gold_test V0.1."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    records = load_jsonl(args.input)
    record_ids = [row["record_id"] for row in records]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("record_id dupliqué dans le gold")

    dev_positions, loss = find_balanced_split(records)
    dev_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []
    for position, record in enumerate(records):
        target = dev_rows if position in dev_positions else test_rows
        copied = copy.deepcopy(record)
        copied["split"] = "gold_dev" if position in dev_positions else "gold_test"
        target.append(copied)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    dev_path = args.output_dir / "business_comments_gold_dev_v0.1.jsonl"
    test_path = args.output_dir / "business_comments_gold_test_v0.1.jsonl"
    write_jsonl(dev_path, dev_rows)
    write_jsonl(test_path, test_rows)

    dev_ids = {row["record_id"] for row in dev_rows}
    test_ids = {row["record_id"] for row in test_rows}
    manifest = {
        "dataset_version": "gold_candidate_v0.1",
        "algorithm": "deterministic_random_search_multifeature_balance",
        "random_seed": RANDOM_SEED,
        "search_iterations": SEARCH_ITERATIONS,
        "balance_loss": loss,
        "source_dataset": str(args.input),
        "source_sha256": sha256(args.input),
        "dev": {
            "path": str(dev_path),
            "sha256": sha256(dev_path),
            "record_ids": [row["record_id"] for row in dev_rows],
            "seed_indices": [
                row["provenance"]["seed_index"] for row in dev_rows
            ],
            "distribution": distribution(dev_rows),
        },
        "test": {
            "path": str(test_path),
            "sha256": sha256(test_path),
            "record_ids": [row["record_id"] for row in test_rows],
            "seed_indices": [
                row["provenance"]["seed_index"] for row in test_rows
            ],
            "distribution": distribution(test_rows),
        },
        "integrity": {
            "dev_count": len(dev_rows),
            "test_count": len(test_rows),
            "overlap": len(dev_ids & test_ids),
            "union_matches_source": dev_ids | test_ids == set(record_ids),
        },
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"DEV={dev_path}")
    print(f"TEST={test_path}")
    print(f"MANIFEST={args.manifest}")
    print(f"BALANCE_LOSS={loss:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
