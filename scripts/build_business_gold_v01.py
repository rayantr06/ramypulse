"""Build the reviewed 100-comment RamyPulse gold candidate dataset."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = (
    ROOT
    / "docs"
    / "slm_v2"
    / "business_comment_annotation_v0.1.schema.json"
)
PILOT_SCRIPT = ROOT / "scripts" / "pilot_business_annotation_v01.py"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed" / "slm_v2_gold"
DEFAULT_DOCS_DIR = ROOT / "docs" / "slm_v2" / "gold_v0.1"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=False) + "\n")


def load_pilot_helpers() -> Any:
    spec = importlib.util.spec_from_file_location("ramypulse_pilot", PILOT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger {PILOT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_review(
    annotation: dict[str, Any],
    review: dict[str, Any],
    text: str,
    pilot_helpers: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    reviewed = copy.deepcopy(annotation)
    if review["decision"] == "replace":
        replacement = review.get("annotation")
        if not isinstance(replacement, dict):
            raise ValueError(
                f"seed {review['seed_index']}: decision=replace exige annotation"
            )
        reviewed = copy.deepcopy(replacement)
    elif review["decision"] == "modify":
        changes = review.get("set")
        if not isinstance(changes, dict) or not changes:
            raise ValueError(
                f"seed {review['seed_index']}: decision=modify exige set"
            )
        for field, value in changes.items():
            if "." in field:
                raise ValueError(
                    f"seed {review['seed_index']}: utiliser un objet complet "
                    f"pour le champ imbriqué {field}"
                )
            if field not in reviewed:
                raise ValueError(
                    f"seed {review['seed_index']}: champ inconnu {field}"
                )
            reviewed[field] = copy.deepcopy(value)
    elif review["decision"] != "accept":
        raise ValueError(
            f"seed {review['seed_index']}: décision inconnue {review['decision']}"
        )

    reviewed, repairs = pilot_helpers.repair_offsets(reviewed, text)
    return reviewed, repairs


def validate_reviews(
    drafts: list[dict[str, Any]], reviews: list[dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    draft_indices = [row["seed_index"] for row in drafts]
    review_indices = [row.get("seed_index") for row in reviews]
    if len(review_indices) != len(set(review_indices)):
        duplicates = [
            value
            for value, count in Counter(review_indices).items()
            if count > 1
        ]
        raise ValueError(f"Décisions de revue dupliquées : {duplicates}")
    missing = sorted(set(draft_indices) - set(review_indices))
    unexpected = sorted(set(review_indices) - set(draft_indices))
    if missing or unexpected:
        raise ValueError(
            f"Revue incomplète. Manquants={missing}; inattendus={unexpected}"
        )
    return {row["seed_index"]: row for row in reviews}


def evidence_count(annotation: dict[str, Any]) -> int:
    total = len(annotation.get("sentiment", {}).get("evidence", []))
    total += sum(len(item.get("evidence", [])) for item in annotation.get("aspects", []))
    total += sum(len(item.get("evidence", [])) for item in annotation.get("alerts", []))
    return total


def build_dataset(
    drafts: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    schema: dict[str, Any],
    pilot_helpers: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    review_by_index = validate_reviews(drafts, reviews)
    validator = Draft202012Validator(schema)
    dataset: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []

    for draft in drafts:
        seed_index = draft["seed_index"]
        if not draft.get("api", {}).get("ok") or not isinstance(
            draft.get("annotation"), dict
        ):
            raise ValueError(f"seed {seed_index}: brouillon API absent ou invalide")

        review = review_by_index[seed_index]
        reviewed, post_review_repairs = apply_review(
            draft["annotation"], review, draft["text"], pilot_helpers
        )
        schema_errors = pilot_helpers.format_schema_errors(validator, reviewed)
        semantic_errors = pilot_helpers.semantic_errors(reviewed, draft["text"])
        if schema_errors or semantic_errors:
            raise ValueError(
                f"seed {seed_index}: annotation revue invalide: "
                f"{schema_errors + semantic_errors}"
            )

        record_id = f"gold_v01_seed_{seed_index:04d}"
        record = {
            "record_id": record_id,
            "schema_version": reviewed["schema_version"],
            "split": "gold_evaluation",
            "text": draft["text"],
            "context": {
                "source": draft["input"].get("source"),
                "topic": draft["input"].get("topic"),
                "brand": draft["input"].get("brand"),
            },
            "annotation": reviewed,
            "provenance": {
                "seed_index": seed_index,
                "draft_provider": draft.get("provider"),
                "draft_model": draft.get("model"),
                "draft_run_id": draft.get("run_id"),
                "reviewer_role": "expert_ai_reviewer",
                "review_method": "manual_semantic_review",
                "review_status": "single_reviewer_gold_candidate",
                "reviewed_at": review.get("reviewed_at"),
                "legacy_weak_labels_not_for_model_input": {
                    "aspect": draft["input"].get("aspect"),
                    "sentiment": draft["input"].get("sentiment_label"),
                },
            },
        }
        dataset.append(record)
        audit.append(
            {
                "record_id": record_id,
                "seed_index": seed_index,
                "decision": review["decision"],
                "notes": review.get("notes", ""),
                "post_review_offset_repairs": post_review_repairs,
                "schema_valid": True,
                "semantic_valid": True,
                "evidence_count": evidence_count(reviewed),
            }
        )

    return dataset, audit


def build_validation_report(
    dataset: list[dict[str, Any]], audit: list[dict[str, Any]], sha256: str
) -> dict[str, Any]:
    annotations = [row["annotation"] for row in dataset]
    texts = [row["text"] for row in dataset]
    evidence_counts = [item["evidence_count"] for item in audit]
    return {
        "dataset_version": "gold_candidate_v0.1",
        "record_count": len(dataset),
        "sha256": sha256,
        "review_status": "single_reviewer_gold_candidate",
        "review_decisions": dict(Counter(item["decision"] for item in audit)),
        "sources": dict(Counter(row["context"]["source"] for row in dataset)),
        "topics": dict(Counter(row["context"]["topic"] for row in dataset)),
        "is_exploitable": dict(
            Counter(str(item["is_exploitable"]).lower() for item in annotations)
        ),
        "business_relevance": dict(
            Counter(item["business_relevance"] for item in annotations)
        ),
        "sentiment": dict(
            Counter(item["sentiment"]["label"] for item in annotations)
        ),
        "language_dominant": dict(
            Counter(item["language"]["dominant"] for item in annotations)
        ),
        "intents": dict(
            Counter(intent for item in annotations for intent in item["intents"])
        ),
        "aspect_families": dict(
            Counter(
                aspect["family"]
                for item in annotations
                for aspect in item["aspects"]
            )
        ),
        "alerts": dict(
            Counter(alert["type"] for item in annotations for alert in item["alerts"])
        ),
        "text_length": {
            "min": min(map(len, texts)),
            "median": statistics.median(map(len, texts)),
            "max": max(map(len, texts)),
        },
        "evidence": {
            "total": sum(evidence_counts),
            "records_without_evidence": sum(count == 0 for count in evidence_counts),
        },
        "validation": {
            "json_schema_pass": len(dataset),
            "semantic_span_pass": len(dataset),
            "target_reference_pass": len(dataset),
        },
    }


def dataset_card(report: dict[str, Any], dataset_path: Path) -> str:
    return f"""# RamyPulse Business Comments — Gold Candidate V0.1

## Statut

Ce fichier est un benchmark candidat à annotateur unique. Ses {report['record_count']} lignes ont fait l'objet d'une revue sémantique explicite et passent le schéma métier V0.1 ainsi que les contrôles de citations et de références.

Il peut servir au développement, à la comparaison de prompts et à l'évaluation préliminaire. Il ne doit pas être présenté comme un gold humain définitif tant qu'une seconde annotation indépendante et une adjudication n'ont pas été réalisées.

Les 100 lignes portent le split `gold_evaluation` : elles doivent rester hors des données d'entraînement.

## Fichier

- Dataset : `{dataset_path}`
- SHA-256 : `{report['sha256']}`
- Schéma : `{SCHEMA_PATH}`

## Composition

- Sources : {json.dumps(report['sources'], ensure_ascii=False)}
- Thèmes : {json.dumps(report['topics'], ensure_ascii=False)}
- Pertinence business : {json.dumps(report['business_relevance'], ensure_ascii=False)}
- Sentiment : {json.dumps(report['sentiment'], ensure_ascii=False)}
- Langues dominantes : {json.dumps(report['language_dominant'], ensure_ascii=False)}
- Familles d'aspect : {json.dumps(report['aspect_families'], ensure_ascii=False)}

## Contrôles

- JSON Schema : {report['validation']['json_schema_pass']}/{report['record_count']}
- Preuves et offsets : {report['validation']['semantic_span_pass']}/{report['record_count']}
- Références d'entités : {report['validation']['target_reference_pass']}/{report['record_count']}
- Décisions de revue : {json.dumps(report['review_decisions'], ensure_ascii=False)}

## Évaluation d'un modèle

Le fichier de prédictions attendu contient une ligne par `record_id` avec un champ `annotation`.

```powershell
python scripts/evaluate_business_annotations_v01.py `
  --predictions chemin\\predictions.jsonl `
  --output chemin\\evaluation.json
```

L'évaluateur mesure la couverture, la validité du schéma, les catégories principales, les intentions, les aspects, les alertes, les entités et l'ancrage exact des preuves.

## Usage recommandé

1. Ne jamais entraîner et évaluer sur les mêmes lignes.
2. Conserver `text` inchangé.
3. Ne pas exposer les anciens labels faibles au modèle.
4. Utiliser `annotation` comme cible et `context` uniquement lorsque la donnée est réellement disponible en production.
5. Après double annotation, figer les splits et publier une nouvelle version immuable.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Construit le gold candidat V0.1 après revue explicite."
    )
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIR)
    args = parser.parse_args()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    drafts = load_jsonl(args.draft)
    reviews = load_jsonl(args.reviews)
    pilot_helpers = load_pilot_helpers()
    dataset, audit = build_dataset(drafts, reviews, schema, pilot_helpers)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.docs_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = args.output_dir / "business_comments_gold_candidate_v0.1.jsonl"
    audit_path = args.docs_dir / "review_audit.jsonl"
    report_path = args.docs_dir / "validation_report.json"
    card_path = args.docs_dir / "DATASET_CARD.md"

    write_jsonl(dataset_path, dataset)
    write_jsonl(audit_path, audit)
    sha256 = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    report = build_validation_report(dataset, audit, sha256)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    card_path.write_text(dataset_card(report, dataset_path), encoding="utf-8")

    print(f"DATASET={dataset_path}")
    print(f"AUDIT={audit_path}")
    print(f"REPORT={report_path}")
    print(f"CARD={card_path}")
    print(f"SHA256={sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
