"""Convert the reviewed pilot drafts into reproducible baseline predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PILOT = (
    ROOT
    / "data"
    / "processed"
    / "slm_v2_pilot"
    / "20260729T204321Z"
    / "pilot_results.jsonl"
)
DEFAULT_GOLD_DIR = ROOT / "data" / "processed" / "slm_v2_gold"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed" / "slm_v2_baselines"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def record_id(seed_index: int) -> str:
    return f"gold_v01_seed_{seed_index:04d}"


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def select_predictions(
    predictions_by_id: dict[str, dict[str, Any]],
    gold_path: Path,
) -> list[dict[str, Any]]:
    gold_rows = load_jsonl(gold_path)
    selected: list[dict[str, Any]] = []
    for gold_row in gold_rows:
        current_id = gold_row["record_id"]
        if current_id not in predictions_by_id:
            raise ValueError(f"Prédiction absente pour {current_id}")
        prediction = predictions_by_id[current_id]
        if prediction["text_sha256"] != text_sha256(gold_row["text"]):
            raise ValueError(f"Texte différent entre le pilote et le gold: {current_id}")
        selected.append(prediction)
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prépare les prédictions Gemini du benchmark gold V0.1."
    )
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--gold-dir", type=Path, default=DEFAULT_GOLD_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    pilot_rows = load_jsonl(args.pilot)
    predictions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in pilot_rows:
        current_id = record_id(row["seed_index"])
        if current_id in seen:
            raise ValueError(f"Prédiction dupliquée: {current_id}")
        seen.add(current_id)
        predictions.append(
            {
                "record_id": current_id,
                "annotation": row.get("annotation"),
                "provider": row.get("provider"),
                "model": row.get("model"),
                "prediction_stage": "post_offset_normalization",
                "source_run_id": row.get("run_id"),
                "text_sha256": text_sha256(row["text"]),
                "pipeline_validation": row.get("validation", {}),
            }
        )

    predictions_by_id = {row["record_id"]: row for row in predictions}
    dataset_specs = {
        "all": (
            args.gold_dir / "business_comments_gold_candidate_v0.1.jsonl",
            args.output_dir
            / "gemini_3.5_flash_lite_gold_v0.1_predictions.jsonl",
        ),
        "dev": (
            args.gold_dir / "business_comments_gold_dev_v0.1.jsonl",
            args.output_dir
            / "gemini_3.5_flash_lite_gold_dev_v0.1_predictions.jsonl",
        ),
        "test": (
            args.gold_dir / "business_comments_gold_test_v0.1.jsonl",
            args.output_dir
            / "gemini_3.5_flash_lite_gold_test_v0.1_predictions.jsonl",
        ),
    }

    for label, (gold_path, output_path) in dataset_specs.items():
        selected = select_predictions(predictions_by_id, gold_path)
        write_jsonl(output_path, selected)
        print(f"{label.upper()}={output_path} ({len(selected)} prédictions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
