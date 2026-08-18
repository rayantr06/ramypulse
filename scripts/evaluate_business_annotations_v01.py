"""Evaluate SLM predictions against the RamyPulse 100-record gold candidate."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Hashable

from jsonschema import Draft202012Validator


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GOLD = (
    ROOT
    / "data"
    / "processed"
    / "slm_v2_gold"
    / "business_comments_gold_candidate_v0.1.jsonl"
)
SCHEMA_PATH = (
    ROOT
    / "docs"
    / "slm_v2"
    / "business_comment_annotation_v0.1.schema.json"
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def accuracy(gold: list[Hashable], predicted: list[Hashable]) -> float:
    return safe_div(
        sum(expected == actual for expected, actual in zip(gold, predicted)),
        len(gold),
    )


def macro_f1(
    gold: list[Hashable],
    predicted: list[Hashable],
    labels: set[Hashable] | None = None,
) -> float:
    evaluated_labels = sorted(labels or (set(gold) | set(predicted)), key=str)
    scores: list[float] = []
    for label in evaluated_labels:
        true_positive = sum(
            expected == label and actual == label
            for expected, actual in zip(gold, predicted)
        )
        false_positive = sum(
            expected != label and actual == label
            for expected, actual in zip(gold, predicted)
        )
        false_negative = sum(
            expected == label and actual != label
            for expected, actual in zip(gold, predicted)
        )
        precision = safe_div(true_positive, true_positive + false_positive)
        recall = safe_div(true_positive, true_positive + false_negative)
        scores.append(safe_div(2 * precision * recall, precision + recall))
    return safe_div(sum(scores), len(scores))


def multilabel_micro(
    gold_sets: list[set[Hashable]], predicted_sets: list[set[Hashable]]
) -> dict[str, float | int]:
    true_positive = sum(
        len(expected & actual)
        for expected, actual in zip(gold_sets, predicted_sets)
    )
    false_positive = sum(
        len(actual - expected)
        for expected, actual in zip(gold_sets, predicted_sets)
    )
    false_negative = sum(
        len(expected - actual)
        for expected, actual in zip(gold_sets, predicted_sets)
    )
    precision = safe_div(true_positive, true_positive + false_positive)
    recall = safe_div(true_positive, true_positive + false_negative)
    return {
        "precision": precision,
        "recall": recall,
        "f1": safe_div(2 * precision * recall, precision + recall),
        "exact_match": safe_div(
            sum(expected == actual for expected, actual in zip(gold_sets, predicted_sets)),
            len(gold_sets),
        ),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "gold_labels": true_positive + false_negative,
        "predicted_labels": true_positive + false_positive,
    }


def span_grounding(annotation: dict[str, Any], text: str) -> tuple[int, int]:
    spans: list[dict[str, Any]] = list(
        annotation.get("sentiment", {}).get("evidence", [])
    )
    spans.extend(
        span
        for aspect in annotation.get("aspects", [])
        for span in aspect.get("evidence", [])
    )
    spans.extend(
        span
        for alert in annotation.get("alerts", [])
        for span in alert.get("evidence", [])
    )
    grounded = 0
    for span in spans:
        start = span.get("start")
        end = span.get("end")
        excerpt = span.get("text")
        if (
            isinstance(start, int)
            and isinstance(end, int)
            and isinstance(excerpt, str)
            and 0 <= start <= end <= len(text)
            and text[start:end] == excerpt
        ):
            grounded += 1
    return grounded, len(spans)


def semantic_errors(annotation: dict[str, Any], text: str) -> list[str]:
    """Validate references and evidence rules that JSON Schema cannot express."""
    errors: list[str] = []
    entities = annotation.get("entities", [])
    entity_ids = [entity.get("id") for entity in entities]
    known_ids = set(entity_ids)
    if len(entity_ids) != len(known_ids):
        errors.append("entity_ids_non_uniques")

    def check_span(
        span: dict[str, Any], location: str, text_key: str = "text"
    ) -> None:
        excerpt = span.get(text_key)
        start = span.get("start")
        end = span.get("end")
        if (
            not isinstance(excerpt, str)
            or not isinstance(start, int)
            or not isinstance(end, int)
        ):
            errors.append(f"{location}:span_incomplet")
            return
        if not 0 <= start <= end <= len(text):
            errors.append(f"{location}:offset_hors_limites")
            return
        if text[start:end] != excerpt:
            errors.append(f"{location}:citation_non_alignee")

    for index, entity in enumerate(entities):
        if entity.get("source") == "texte":
            check_span(entity, f"entities[{index}]", text_key="mention")
        elif any(
            entity.get(key) is not None for key in ("mention", "start", "end")
        ):
            errors.append(f"entities[{index}]:contexte_avec_offsets")

    for target_id in annotation.get("sentiment", {}).get(
        "target_entity_ids", []
    ):
        if target_id not in known_ids:
            errors.append(f"sentiment:cible_inconnue:{target_id}")

    evidence_groups: list[tuple[str, list[dict[str, Any]]]] = [
        (
            "sentiment.evidence",
            annotation.get("sentiment", {}).get("evidence", []),
        )
    ]
    for index, aspect in enumerate(annotation.get("aspects", [])):
        target_id = aspect.get("target_entity_id")
        if target_id is not None and target_id not in known_ids:
            errors.append(f"aspects[{index}]:cible_inconnue:{target_id}")
        evidence_groups.append(
            (f"aspects[{index}].evidence", aspect.get("evidence", []))
        )
    for index, alert in enumerate(annotation.get("alerts", [])):
        target_id = alert.get("target_entity_id")
        if target_id is not None and target_id not in known_ids:
            errors.append(f"alerts[{index}]:cible_inconnue:{target_id}")
        evidence_groups.append(
            (f"alerts[{index}].evidence", alert.get("evidence", []))
        )

    for group_name, evidence_items in evidence_groups:
        for index, evidence in enumerate(evidence_items):
            check_span(evidence, f"{group_name}[{index}]")

    if annotation.get("is_exploitable") is False:
        if annotation.get("aspects"):
            errors.append("inexploitable_avec_aspects")
        if annotation.get("alerts"):
            errors.append("inexploitable_avec_alertes")
    return errors


def rounded(value: float) -> float:
    return round(value, 4)


def label_key(value: Hashable) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "null"
    return str(value)


CategoricalGetter = Callable[[dict[str, Any]], Hashable]
SetGetter = Callable[[dict[str, Any]], set[Hashable]]


def score_annotations(
    pairs: list[tuple[dict[str, Any], dict[str, Any] | None]],
) -> dict[str, Any]:
    """Score annotation pairs; None represents a missing or invalid output."""
    categorical_getters: list[tuple[str, CategoricalGetter]] = [
        ("is_exploitable", lambda item: item["is_exploitable"]),
        ("business_relevance", lambda item: item["business_relevance"]),
        ("sentiment", lambda item: item["sentiment"]["label"]),
        (
            "sentiment_intensity",
            lambda item: item["sentiment"]["intensity"],
        ),
        ("sarcasm", lambda item: item["sentiment"]["sarcasm"]),
        ("language", lambda item: item["language"]["dominant"]),
        ("actionable", lambda item: item["actionability"]["actionable"]),
        ("action_queue", lambda item: item["actionability"]["queue"]),
        (
            "action_priority",
            lambda item: item["actionability"]["priority"],
        ),
    ]

    categorical_metrics: dict[str, dict[str, Any]] = {}
    for name, getter in categorical_getters:
        gold_values = [getter(expected) for expected, _ in pairs]
        predicted_values = [
            getter(actual) if actual is not None else "__invalid__"
            for _, actual in pairs
        ]
        gold_labels = sorted(set(gold_values), key=str)
        per_label: dict[str, dict[str, float | int]] = {}
        for label in gold_labels:
            true_positive = sum(
                expected == label and actual == label
                for expected, actual in zip(gold_values, predicted_values)
            )
            false_positive = sum(
                expected != label and actual == label
                for expected, actual in zip(gold_values, predicted_values)
            )
            false_negative = sum(
                expected == label and actual != label
                for expected, actual in zip(gold_values, predicted_values)
            )
            precision = safe_div(
                true_positive, true_positive + false_positive
            )
            recall = safe_div(
                true_positive, true_positive + false_negative
            )
            per_label[label_key(label)] = {
                "precision": rounded(precision),
                "recall": rounded(recall),
                "f1": rounded(
                    safe_div(2 * precision * recall, precision + recall)
                ),
                "support": sum(value == label for value in gold_values),
            }
        confusion = Counter(
            (label_key(expected), label_key(actual))
            for expected, actual in zip(gold_values, predicted_values)
        )
        categorical_metrics[name] = {
            "accuracy": rounded(accuracy(gold_values, predicted_values)),
            "macro_f1": rounded(
                macro_f1(
                    gold_values,
                    predicted_values,
                    labels=set(gold_values),
                )
            ),
            "per_label": per_label,
            "confusion": [
                {"gold": expected, "predicted": actual, "count": count}
                for (expected, actual), count in sorted(confusion.items())
            ],
        }

    set_getters: list[tuple[str, SetGetter]] = [
        ("intents", lambda item: set(item["intents"])),
        (
            "aspects_family_attribute_sentiment",
            lambda item: {
                (
                    aspect["family"],
                    aspect["attribute"],
                    aspect["sentiment"],
                )
                for aspect in item["aspects"]
            },
        ),
        (
            "alerts_type_severity",
            lambda item: {
                (alert["type"], alert["severity"])
                for alert in item["alerts"]
            },
        ),
        (
            "entities_type_name",
            lambda item: {
                (entity["type"], entity["name"].casefold())
                for entity in item["entities"]
            },
        ),
    ]
    multilabel_metrics: dict[str, dict[str, float]] = {}
    for name, getter in set_getters:
        result = multilabel_micro(
            [getter(expected) for expected, _ in pairs],
            [
                getter(actual) if actual is not None else set()
                for _, actual in pairs
            ],
        )
        multilabel_metrics[name] = {
            key: value if isinstance(value, int) else rounded(value)
            for key, value in result.items()
        }
    return {
        "records_scored": len(pairs),
        "categorical": categorical_metrics,
        "multilabel": multilabel_metrics,
    }


def evaluate(
    gold_rows: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]],
    validator: Draft202012Validator,
) -> dict[str, Any]:
    predictions_by_id = {
        row.get("record_id"): row for row in prediction_rows if row.get("record_id")
    }
    duplicate_count = len(prediction_rows) - len(predictions_by_id)
    gold_ids = [row["record_id"] for row in gold_rows]
    missing_ids = [record_id for record_id in gold_ids if record_id not in predictions_by_id]
    unexpected_ids = sorted(set(predictions_by_id) - set(gold_ids))

    valid_pairs: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    end_to_end_pairs: list[
        tuple[dict[str, Any], dict[str, Any] | None]
    ] = []
    invalid_schema: dict[str, list[str]] = {}
    invalid_semantics: dict[str, list[str]] = {}
    grounded_spans = 0
    total_spans = 0
    for gold_row in gold_rows:
        prediction_row = predictions_by_id.get(gold_row["record_id"])
        if prediction_row is None:
            end_to_end_pairs.append((gold_row["annotation"], None))
            continue
        annotation = prediction_row.get("annotation")
        if not isinstance(annotation, dict):
            invalid_schema[gold_row["record_id"]] = ["annotation absente"]
            end_to_end_pairs.append((gold_row["annotation"], None))
            continue
        errors = list(validator.iter_errors(annotation))
        if errors:
            invalid_schema[gold_row["record_id"]] = [
                error.message for error in errors[:10]
            ]
            end_to_end_pairs.append((gold_row["annotation"], None))
            continue
        grounded, count = span_grounding(annotation, gold_row["text"])
        grounded_spans += grounded
        total_spans += count
        semantic = semantic_errors(annotation, gold_row["text"])
        if semantic:
            invalid_semantics[gold_row["record_id"]] = semantic[:10]
            end_to_end_pairs.append((gold_row["annotation"], None))
            continue
        pair = (gold_row["annotation"], annotation)
        valid_pairs.append(pair)
        end_to_end_pairs.append(pair)

    return {
        "gold_records": len(gold_rows),
        "prediction_records": len(prediction_rows),
        "coverage": {
            "aligned_valid": len(valid_pairs),
            "missing": len(missing_ids),
            "unexpected": len(unexpected_ids),
            "duplicates": duplicate_count,
            "schema_invalid": len(invalid_schema),
            "semantic_invalid": len(invalid_semantics),
            "valid_output_rate": rounded(
                safe_div(len(valid_pairs), len(gold_rows))
            ),
        },
        "missing_record_ids": missing_ids,
        "unexpected_record_ids": unexpected_ids,
        "schema_errors": invalid_schema,
        "semantic_errors": invalid_semantics,
        "valid_only": score_annotations(valid_pairs),
        "end_to_end": score_annotations(end_to_end_pairs),
        "evidence_grounding_rate": rounded(
            safe_div(grounded_spans, total_spans)
        ),
        "evidence_spans": {
            "grounded": grounded_spans,
            "total": total_spans,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Évalue des prédictions SLM contre le gold candidat V0.1."
    )
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    report = evaluate(
        gold_rows=load_jsonl(args.gold),
        prediction_rows=load_jsonl(args.predictions),
        validator=validator,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"REPORT={args.output}")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
