"""Run a small, auditable pilot of the RamyPulse business annotation schema.

This script intentionally uses synchronous API calls instead of OpenAI Batch:
the pilot is small, results are available immediately, and each response is
validated before any larger generation is considered.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from jsonschema import Draft202012Validator
from openai import OpenAI


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "data" / "processed" / "master_seed_7k.jsonl"
SCHEMA_PATH = (
    ROOT
    / "docs"
    / "slm_v2"
    / "business_comment_annotation_v0.1.schema.json"
)
OUTPUT_ROOT = ROOT / "data" / "processed" / "slm_v2_pilot"
REPORT_ROOT = ROOT / "docs" / "slm_v2" / "pilot_reports"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
DEFAULT_SAMPLE_SIZE = 24
RANDOM_SEED = 20260729


SYSTEM_PROMPT = """Tu es un annotateur professionnel de commentaires business multilingues, avec une expertise particulière de l'Algérie (darija arabe, Arabizi, arabe standard, français et code-switching).

Retourne uniquement l'objet JSON demandé par le schéma. N'ajoute ni explication, ni balise ChatML, ni trace de raisonnement.

Règles impératives :
1. Analyse le texte sans le traduire ni le corriger.
2. N'invente aucune marque, organisation, personne, produit ou service.
3. Une entité explicitement écrite dans le commentaire a source="texte". Sa mention est une citation exacte et start/end sont les indices Python tels que texte[start:end] == mention.
4. Une marque fournie uniquement dans le contexte peut être ajoutée avec source="contexte" et mention/start/end à null.
5. Chaque preuve est une citation exacte et contiguë du commentaire. Ses offsets Python doivent vérifier texte[start:end] == evidence.text.
6. Utilise uniquement les familles et attributs du schéma. Ne crée jamais de nouvelle étiquette.
7. "mixte" exige de vrais signaux positifs et négatifs. L'absence d'opinion est "neutre".
8. Une alerte correspond à un risque concret, pas à toute opinion négative.
9. Si le texte est inexploitable, mets is_exploitable=false, choisis une raison, et retourne aspects=[] et alerts=[].
10. Si le commentaire est court mais clair grâce au contexte de collecte, il peut être exploitable.
11. Un pays, une ville ou une région utilise le type d'entité "lieu".
12. Les identifiants d'entités commencent à ent_1 et sont uniques.
"""


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_seed_index"] = line_number - 1
            rows.append(row)
    return rows


def collect_attribute_map(schema: dict[str, Any]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for rule in schema["$defs"]["aspect"].get("allOf", []):
        family = (
            rule.get("if", {})
            .get("properties", {})
            .get("family", {})
            .get("const")
        )
        enum_values = (
            rule.get("then", {})
            .get("properties", {})
            .get("attribute", {})
            .get("enum", [])
        )
        if family:
            mapping[family] = list(enum_values)
    return mapping


def make_openai_generation_schema(full_schema: dict[str, Any]) -> dict[str, Any]:
    """Convert the authoritative schema to the Structured Outputs subset.

    Conditional family/attribute rules remain enforced by the local Draft
    2020-12 validator after generation. The generation schema uses the union of
    all allowed attributes so the model still cannot invent free labels.
    """

    attribute_map = collect_attribute_map(full_schema)
    unsupported = {
        "$schema",
        "$id",
        "allOf",
        "if",
        "then",
        "else",
        "not",
        "dependentRequired",
        "dependentSchemas",
        "uniqueItems",
    }

    def convert(node: Any) -> Any:
        if isinstance(node, list):
            return [convert(item) for item in node]
        if not isinstance(node, dict):
            return node

        converted: dict[str, Any] = {}
        for key, value in node.items():
            if key in unsupported:
                continue
            if key == "const":
                converted["enum"] = [value]
                continue
            converted[key] = convert(value)
        return converted

    generation_schema = convert(copy.deepcopy(full_schema))
    aspect_schema = generation_schema["$defs"]["aspect"]
    variants: list[dict[str, Any]] = []
    for family, attributes in attribute_map.items():
        variant = copy.deepcopy(aspect_schema)
        variant["properties"]["family"] = {
            "type": "string",
            "enum": [family],
        }
        variant["properties"]["attribute"] = {
            "type": "string",
            "enum": attributes,
        }
        variants.append(variant)
    generation_schema["$defs"]["aspect"] = {"anyOf": variants}
    generation_schema["$defs"]["entity"]["properties"]["type"]["description"] = (
        "Utiliser 'lieu' pour une ville, une région ou un pays."
    )
    generation_schema["title"] = "RamyPulse business annotation V0.1"
    return generation_schema


Predicate = Callable[[dict[str, Any]], bool]


def select_stratified_sample(
    rows: list[dict[str, Any]], requested_size: int
) -> list[dict[str, Any]]:
    """Select a stable sample covering direct, indirect, and edge cases.

    The first 24 seeds were manually reviewed only for sampling suitability,
    never for their target annotations. They provide more diagnostic value than
    a purely random draw from this corpus, which contains long runs of duplicate
    contest answers and off-topic social comments.
    """

    curated: list[tuple[int, str]] = [
        (5658, "fmcg_risque_sanitaire"),
        (5715, "fmcg_risque_sanitaire"),
        (6602, "fmcg_promotion_mixte"),
        (6611, "fmcg_question_achat_arabizi"),
        (6617, "fmcg_promotion_mixte"),
        (7013, "fmcg_promotion_plainte"),
        (7028, "fmcg_reputation_positive"),
        (7047, "fmcg_suggestion_produit"),
        (7215, "fmcg_prix_negatif"),
        (6928, "fmcg_contexte_ambigu"),
        (6966, "fmcg_hors_sujet"),
        (7224, "tenant_stock"),
        (7226, "tenant_qualite_securite"),
        (7229, "tenant_emballage"),
        (0, "emploi_salaire"),
        (1, "emploi_recrutement"),
        (2, "economie_prix"),
        (236, "marche_prix_petrole"),
        (1500, "sante_disponibilite_prix"),
        (844, "education_emploi_equite"),
        (5532, "telecom_reseau"),
        (5560, "tourisme_reputation"),
        (4381, "commerce_prix_livraison"),
        (41, "bruit_texte_insuffisant"),
    ]
    by_index = {row["_seed_index"]: row for row in rows}
    selected: list[dict[str, Any]] = []
    selected_indices: set[int] = set()
    for seed_index, stratum_name in curated[:requested_size]:
        row = by_index[seed_index]
        copy_row = dict(row)
        copy_row["_stratum"] = stratum_name
        selected.append(copy_row)
        selected_indices.add(seed_index)

    if len(selected) >= requested_size:
        return selected

    strata: list[tuple[str, int, Predicate]] = [
        (
            "fmcg_negatif",
            3,
            lambda row: row.get("source") == "ramypulse_v1_facebook"
            and row.get("sentiment_label") == "negatif",
        ),
        (
            "fmcg_positif",
            3,
            lambda row: row.get("source") == "ramypulse_v1_facebook"
            and row.get("sentiment_label") == "positif",
        ),
        (
            "fmcg_neutre",
            2,
            lambda row: row.get("source") == "ramypulse_v1_facebook"
            and row.get("sentiment_label") == "neutre",
        ),
        (
            "fmcg_mixte",
            1,
            lambda row: row.get("source") == "ramypulse_v1_facebook"
            and row.get("sentiment_label") == "mixte",
        ),
        (
            "tenant_demo",
            3,
            lambda row: row.get("source") == "tenant_demo_expo",
        ),
        (
            "business",
            2,
            lambda row: row.get("topic") == "business",
        ),
        (
            "economy",
            2,
            lambda row: row.get("topic") == "economy",
        ),
        (
            "health",
            1,
            lambda row: row.get("topic") == "health",
        ),
        (
            "education",
            1,
            lambda row: row.get("topic") in {"education", "university"},
        ),
        (
            "technology",
            1,
            lambda row: row.get("topic") == "technologie",
        ),
        (
            "tourism",
            1,
            lambda row: row.get("topic") == "tourism",
        ),
        (
            "social_short",
            1,
            lambda row: row.get("topic") in {"social", "religious", "media"}
            and len(row.get("text", "")) <= 18,
        ),
        (
            "social_long",
            1,
            lambda row: row.get("topic") in {"social", "religious", "media"}
            and len(row.get("text", "")) >= 180,
        ),
        (
            "cross_domain_mixed",
            1,
            lambda row: row.get("sentiment_label") == "mixte",
        ),
    ]

    rng = random.Random(RANDOM_SEED)
    for stratum_name, count, predicate in strata:
        candidates = [
            row
            for row in rows
            if row["_seed_index"] not in selected_indices
            and predicate(row)
            and row.get("text", "").strip() not in {"[TEXTE_BRUT]", "TEXTE_BRUT"}
        ]
        rng.shuffle(candidates)
        # Prefer a mixture of lengths instead of the first adjacent corpus rows.
        candidates.sort(key=lambda row: (len(row.get("text", "")), rng.random()))
        if count == 1 and candidates:
            picks = [candidates[len(candidates) // 2]]
        elif count > 1 and candidates:
            positions = [
                round(index * (len(candidates) - 1) / max(count - 1, 1))
                for index in range(count)
            ]
            picks = [candidates[position] for position in positions]
        else:
            picks = []

        for row in picks:
            copy_row = dict(row)
            copy_row["_stratum"] = stratum_name
            selected.append(copy_row)
            selected_indices.add(row["_seed_index"])

    if len(selected) < requested_size:
        remaining = [
            row
            for row in rows
            if row["_seed_index"] not in selected_indices
            and row.get("text", "").strip() not in {"[TEXTE_BRUT]", "TEXTE_BRUT"}
        ]
        rng.shuffle(remaining)
        for row in remaining[: requested_size - len(selected)]:
            copy_row = dict(row)
            copy_row["_stratum"] = "complement"
            selected.append(copy_row)

    return selected[:requested_size]


def context_for_model(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_collecte": row.get("source"),
        "theme_historique": row.get("topic"),
        "marque_connue_par_contexte": row.get("brand"),
    }


def find_occurrences(text: str, excerpt: str) -> list[int]:
    starts: list[int] = []
    cursor = 0
    while excerpt and cursor <= len(text):
        position = text.find(excerpt, cursor)
        if position < 0:
            break
        starts.append(position)
        cursor = position + 1
    return starts


def repair_span(
    text: str, span: dict[str, Any], location: str, repairs: list[dict[str, Any]]
) -> None:
    excerpt = span.get("text")
    if not isinstance(excerpt, str) or not excerpt:
        return
    start = span.get("start")
    end = span.get("end")
    if (
        isinstance(start, int)
        and isinstance(end, int)
        and 0 <= start <= end <= len(text)
        and text[start:end] == excerpt
    ):
        return

    occurrences = find_occurrences(text, excerpt)
    if not occurrences:
        return
    old_start = start
    if isinstance(start, int):
        new_start = min(occurrences, key=lambda value: abs(value - start))
    else:
        new_start = occurrences[0]
    span["start"] = new_start
    span["end"] = new_start + len(excerpt)
    repairs.append(
        {
            "location": location,
            "old_start": old_start,
            "old_end": end,
            "new_start": span["start"],
            "new_end": span["end"],
        }
    )


def repair_offsets(
    annotation: dict[str, Any], text: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    repaired = copy.deepcopy(annotation)
    repairs: list[dict[str, Any]] = []

    for index, entity in enumerate(repaired.get("entities", [])):
        if entity.get("source") != "texte":
            continue
        proxy = {
            "text": entity.get("mention"),
            "start": entity.get("start"),
            "end": entity.get("end"),
        }
        repair_span(text, proxy, f"entities[{index}]", repairs)
        entity["start"] = proxy.get("start")
        entity["end"] = proxy.get("end")

    evidence_groups: list[tuple[str, list[dict[str, Any]]]] = [
        ("sentiment.evidence", repaired.get("sentiment", {}).get("evidence", []))
    ]
    for index, aspect in enumerate(repaired.get("aspects", [])):
        evidence_groups.append((f"aspects[{index}].evidence", aspect.get("evidence", [])))
    for index, alert in enumerate(repaired.get("alerts", [])):
        evidence_groups.append((f"alerts[{index}].evidence", alert.get("evidence", [])))

    for group_name, evidence_items in evidence_groups:
        for index, evidence in enumerate(evidence_items):
            repair_span(text, evidence, f"{group_name}[{index}]", repairs)

    return repaired, repairs


def format_schema_errors(
    validator: Draft202012Validator, annotation: dict[str, Any]
) -> list[str]:
    messages: list[str] = []
    for error in sorted(validator.iter_errors(annotation), key=lambda item: list(item.path)):
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        messages.append(f"{path}: {error.message}")
    return messages


def semantic_errors(annotation: dict[str, Any], text: str) -> list[str]:
    errors: list[str] = []
    entities = annotation.get("entities", [])
    entity_ids = [entity.get("id") for entity in entities]
    known_ids = set(entity_ids)
    if len(entity_ids) != len(known_ids):
        errors.append("entity_ids_non_uniques")

    def check_span(span: dict[str, Any], location: str, key: str = "text") -> None:
        excerpt = span.get(key)
        start = span.get("start")
        end = span.get("end")
        if not isinstance(excerpt, str) or not isinstance(start, int) or not isinstance(end, int):
            errors.append(f"{location}:span_incomplet")
            return
        if not 0 <= start <= end <= len(text):
            errors.append(f"{location}:offset_hors_limites")
            return
        if text[start:end] != excerpt:
            errors.append(f"{location}:citation_non_alignee")

    for index, entity in enumerate(entities):
        if entity.get("source") == "texte":
            check_span(entity, f"entities[{index}]", key="mention")
        elif any(entity.get(key) is not None for key in ("mention", "start", "end")):
            errors.append(f"entities[{index}]:contexte_avec_offsets")

    target_ids = annotation.get("sentiment", {}).get("target_entity_ids", [])
    for target_id in target_ids:
        if target_id not in known_ids:
            errors.append(f"sentiment:cible_inconnue:{target_id}")

    evidence_groups: list[tuple[str, list[dict[str, Any]]]] = [
        ("sentiment.evidence", annotation.get("sentiment", {}).get("evidence", []))
    ]
    for index, aspect in enumerate(annotation.get("aspects", [])):
        target_id = aspect.get("target_entity_id")
        if target_id is not None and target_id not in known_ids:
            errors.append(f"aspects[{index}]:cible_inconnue:{target_id}")
        evidence_groups.append((f"aspects[{index}].evidence", aspect.get("evidence", [])))
    for index, alert in enumerate(annotation.get("alerts", [])):
        target_id = alert.get("target_entity_id")
        if target_id is not None and target_id not in known_ids:
            errors.append(f"alerts[{index}]:cible_inconnue:{target_id}")
        evidence_groups.append((f"alerts[{index}].evidence", alert.get("evidence", [])))

    for group_name, evidence_items in evidence_groups:
        for index, evidence in enumerate(evidence_items):
            check_span(evidence, f"{group_name}[{index}]")

    if annotation.get("is_exploitable") is False:
        if annotation.get("aspects"):
            errors.append("inexploitable_avec_aspects")
        if annotation.get("alerts"):
            errors.append("inexploitable_avec_alertes")
    return errors


def call_openai(
    client: OpenAI,
    model: str,
    generation_schema: dict[str, Any],
    row: dict[str, Any],
) -> dict[str, Any]:
    text = row["text"]
    payload = {"texte": text, "contexte_collecte": context_for_model(row)}
    started = time.perf_counter()
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False, indent=2),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "ramypulse_business_annotation_v01",
                    "strict": True,
                    "schema": generation_schema,
                },
            },
            max_completion_tokens=2400,
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        message = completion.choices[0].message
        if getattr(message, "refusal", None):
            raise RuntimeError(f"Model refusal: {message.refusal}")
        if not message.content:
            raise RuntimeError("Empty model response")
        annotation = json.loads(message.content)
        usage = completion.usage
        return {
            "ok": True,
            "annotation": annotation,
            "latency_ms": latency_ms,
            "usage": {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            },
            "request_id": completion.id,
        }
    except Exception as exc:  # noqa: BLE001 - each pilot item must be recorded
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }


def call_gemini(
    client: Any,
    model: str,
    generation_schema: dict[str, Any],
    row: dict[str, Any],
) -> dict[str, Any]:
    from google.genai import types

    text = row["text"]
    payload = {"texte": text, "contexte_collecte": context_for_model(row)}
    started = time.perf_counter()
    generation_mode = "response_json_schema"
    try:
        def generate_with_prompt_schema() -> Any:
            fallback_payload = {
                **payload,
                "instruction": "Produis exactement un objet conforme au schema_de_sortie.",
                "schema_de_sortie": generation_schema,
            }
            return client.models.generate_content(
                model=model,
                contents=json.dumps(fallback_payload, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.0,
                    max_output_tokens=2400,
                    response_mime_type="application/json",
                ),
            )

        # This variant rejects the contract's large enum at the API boundary.
        # Skip the known-failing request and validate its JSON-mode output locally.
        if model == "gemini-3.5-flash-lite":
            generation_mode = "json_mode_prompt_schema"
            response = generate_with_prompt_schema()
        else:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=json.dumps(payload, ensure_ascii=False, indent=2),
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.0,
                        max_output_tokens=2400,
                        response_mime_type="application/json",
                        response_json_schema=generation_schema,
                    ),
                )
            except Exception as schema_exc:
                # Other Gemini variants may also reject complex schemas.
                if "400" not in str(schema_exc) or "INVALID_ARGUMENT" not in str(
                    schema_exc
                ):
                    raise
                generation_mode = "json_mode_prompt_schema"
                response = generate_with_prompt_schema()
        latency_ms = round((time.perf_counter() - started) * 1000)
        annotation = response.parsed
        if annotation is None:
            if not response.text:
                raise RuntimeError("Empty model response")
            annotation = json.loads(response.text)
        if not isinstance(annotation, dict):
            annotation = json.loads(response.text)
        usage = getattr(response, "usage_metadata", None)
        return {
            "ok": True,
            "annotation": annotation,
            "latency_ms": latency_ms,
            "usage": {
                "prompt_tokens": getattr(usage, "prompt_token_count", None),
                "completion_tokens": getattr(usage, "candidates_token_count", None),
                "total_tokens": getattr(usage, "total_token_count", None),
            },
            "request_id": getattr(response, "response_id", None),
            "generation_mode": generation_mode,
        }
    except Exception as exc:  # noqa: BLE001 - each pilot item must be recorded
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": round((time.perf_counter() - started) * 1000),
        }


def percent(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100 * numerator / denominator:.1f}%"


def build_report(
    results: list[dict[str, Any]],
    provider: str,
    model: str,
    run_id: str,
    results_path: Path,
    sample_path: Path,
) -> str:
    successful = [result for result in results if result["api"]["ok"]]
    final_valid = [
        result
        for result in successful
        if not result["validation"]["final_schema_errors"]
        and not result["validation"]["final_semantic_errors"]
    ]
    raw_valid = [
        result
        for result in successful
        if not result["validation"]["raw_schema_errors"]
        and not result["validation"]["raw_semantic_errors"]
    ]
    repaired = [
        result
        for result in successful
        if result["validation"]["offset_repairs"]
    ]
    latencies = [result["api"]["latency_ms"] for result in successful]
    total_tokens = sum(
        (result["api"].get("usage", {}).get("total_tokens") or 0)
        for result in successful
    )

    sentiment_counts: Counter[str] = Counter()
    relevance_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    intent_counts: Counter[str] = Counter()
    aspect_counts: Counter[str] = Counter()
    alert_counts: Counter[str] = Counter()
    weak_agreement = 0
    weak_comparable = 0

    for result in successful:
        annotation = result["annotation"]
        sentiment = annotation.get("sentiment", {}).get("label")
        sentiment_counts[sentiment] += 1
        relevance_counts[annotation.get("business_relevance")] += 1
        language_counts[annotation.get("language", {}).get("dominant")] += 1
        intent_counts.update(annotation.get("intents", []))
        aspect_counts.update(
            aspect.get("family") for aspect in annotation.get("aspects", [])
        )
        alert_counts.update(alert.get("type") for alert in annotation.get("alerts", []))
        weak_label = result["input"].get("sentiment_label")
        if weak_label in {"negatif", "neutre", "positif", "mixte"} and sentiment:
            weak_comparable += 1
            weak_agreement += int(weak_label == sentiment)

    failure_lines: list[str] = []
    for result in results:
        if not result["api"]["ok"]:
            failure_lines.append(
                f"- seed `{result['seed_index']}` : API — {result['api']['error']}"
            )
            continue
        validation = result["validation"]
        combined = (
            validation["final_schema_errors"] + validation["final_semantic_errors"]
        )
        if combined:
            failure_lines.append(
                f"- seed `{result['seed_index']}` : " + " ; ".join(combined[:4])
            )

    repaired_lines = [
        f"- seed `{result['seed_index']}` : "
        f"{len(result['validation']['offset_repairs'])} offset(s) réaligné(s)"
        for result in repaired
    ]

    def counter_text(counter: Counter[str]) -> str:
        return ", ".join(
            f"`{key}` {value}"
            for key, value in counter.most_common()
            if key is not None
        ) or "aucun"

    mean_latency = round(statistics.mean(latencies)) if latencies else 0
    p95_latency = (
        round(sorted(latencies)[max(0, int(0.95 * len(latencies)) - 1)])
        if latencies
        else 0
    )
    failure_section = "\n".join(failure_lines) or "- Aucun échec final."
    repaired_section = "\n".join(repaired_lines) or "- Aucun offset réparé."

    return f"""# Rapport du pilote — schéma business V0.1

## Verdict automatique

- Exécution : `{run_id}`
- Fournisseur du pilote : `{provider}`
- Modèle enseignant : `{model}`
- Échantillon : {len(results)} commentaires stratifiés
- Réponses API : {len(successful)}/{len(results)} ({percent(len(successful), len(results))})
- Valides sans correction : {len(raw_valid)}/{len(successful)} ({percent(len(raw_valid), len(successful))})
- Valides après réalignement déterministe des offsets : {len(final_valid)}/{len(successful)} ({percent(len(final_valid), len(successful))})
- Sorties nécessitant un réalignement d'offset : {len(repaired)}/{len(successful)} ({percent(len(repaired), len(successful))})
- Latence moyenne / p95 : {mean_latency} ms / {p95_latency} ms
- Jetons totaux : {total_tokens}
- Accord avec les anciens labels faibles de sentiment : {weak_agreement}/{weak_comparable} ({percent(weak_agreement, weak_comparable)})

L'accord avec les anciens labels n'est pas une mesure d'exactitude : ces labels sont faibles et servent seulement de signal de divergence à revoir humainement.

## Couverture observée

- Pertinence business : {counter_text(relevance_counts)}
- Sentiment : {counter_text(sentiment_counts)}
- Langue dominante : {counter_text(language_counts)}
- Intentions : {counter_text(intent_counts)}
- Familles d'aspect : {counter_text(aspect_counts)}
- Alertes : {counter_text(alert_counts)}

## Échecs après validation finale

{failure_section}

## Corrections déterministes des offsets

{repaired_section}

## Fichiers

- Résultats détaillés : `{results_path}`
- Manifeste de l'échantillon : `{sample_path}`
- Schéma métier validé : `{SCHEMA_PATH}`

## Critère recommandé avant génération massive

Ne pas relancer les milliers d'exemples tant que :

1. 100 % des sorties ne passent pas le schéma final et les contrôles de citations ;
2. les divergences sémantiques n'ont pas été revues sur un échantillon humain ;
3. l'ontologie n'a pas été testée sur davantage de secteurs réels que le corpus actuel ;
4. le format d'entraînement final du SLM n'est pas figé séparément du format d'annotation.
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pilote contrôlé du schéma d'annotation business V0.1"
    )
    parser.add_argument(
        "--provider", choices=("openai", "gemini"), default="openai"
    )
    parser.add_argument("--model")
    parser.add_argument("--limit", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--pacing-seconds",
        type=float,
        default=0.0,
        help="Pause après chaque appel dans un worker pour respecter les quotas.",
    )
    parser.add_argument(
        "--retry-from",
        type=Path,
        help="Relance uniquement les échecs API d'un fichier pilot_results.jsonl.",
    )
    parser.add_argument(
        "--indices",
        help="Indices de seeds séparés par des virgules pour un test ciblé.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prépare et affiche l'échantillon sans appeler l'API.",
    )
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit doit être supérieur à zéro")
    if not 1 <= args.workers <= 8:
        parser.error("--workers doit être compris entre 1 et 8")
    if args.pacing_seconds < 0:
        parser.error("--pacing-seconds ne peut pas être négatif")

    full_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(full_schema)
    validator = Draft202012Validator(full_schema)
    generation_schema = make_openai_generation_schema(full_schema)
    rows = load_jsonl(INPUT_PATH)
    base_results: list[dict[str, Any]] = []
    if args.retry_from and args.indices:
        parser.error("--retry-from et --indices sont mutuellement exclusifs")

    if args.retry_from:
        with args.retry_from.open("r", encoding="utf-8") as handle:
            base_results = [json.loads(line) for line in handle if line.strip()]
        failed_indices = [
            result["seed_index"]
            for result in base_results
            if not result.get("api", {}).get("ok")
        ]
        rows_by_index = {row["_seed_index"]: row for row in rows}
        strata_by_index = {
            result["seed_index"]: result.get("stratum", "retry")
            for result in base_results
        }
        sample = []
        for seed_index in failed_indices:
            row = dict(rows_by_index[seed_index])
            row["_stratum"] = strata_by_index[seed_index]
            sample.append(row)
        if not sample:
            print("Aucun échec API à relancer.")
            return 0
    elif args.indices:
        requested_indices = [
            int(value.strip()) for value in args.indices.split(",") if value.strip()
        ]
        rows_by_index = {row["_seed_index"]: row for row in rows}
        curated_strata = {
            row["_seed_index"]: row["_stratum"]
            for row in select_stratified_sample(rows, DEFAULT_SAMPLE_SIZE)
        }
        sample = []
        for seed_index in requested_indices:
            if seed_index not in rows_by_index:
                parser.error(f"seed index inconnu : {seed_index}")
            row = dict(rows_by_index[seed_index])
            row["_stratum"] = curated_strata.get(seed_index, "test_cible")
            sample.append(row)
    else:
        sample = select_stratified_sample(rows, args.limit)

    if args.dry_run:
        for row in sample:
            print(
                json.dumps(
                    {
                        "seed_index": row["_seed_index"],
                        "stratum": row["_stratum"],
                        "text": row["text"],
                        "context": context_for_model(row),
                    },
                    ensure_ascii=False,
                )
            )
        return 0

    load_dotenv(ROOT / ".env", override=True)
    if args.provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("OPENAI_API_KEY absent de G:\\ramypulse\\.env", file=sys.stderr)
            return 2
        model = args.model or DEFAULT_MODEL
        client: Any = OpenAI(api_key=api_key)
        call_provider = call_openai
    else:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print(
                "GEMINI_API_KEY / GOOGLE_API_KEY absent de G:\\ramypulse\\.env",
                file=sys.stderr,
            )
            return 2
        from google import genai

        model = args.model or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
        client = genai.Client(api_key=api_key)
        call_provider = call_gemini

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = OUTPUT_ROOT / run_id
    report_dir = REPORT_ROOT / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    report_dir.mkdir(parents=True, exist_ok=False)
    sample_path = output_dir / "sample_manifest.jsonl"
    results_path = output_dir / "pilot_results.jsonl"
    generation_schema_path = output_dir / "generation_schema.json"
    report_path = report_dir / "PILOT_REPORT.md"

    if base_results:
        rows_by_index = {row["_seed_index"]: row for row in rows}
        manifest_rows = []
        for result in base_results:
            row = dict(rows_by_index[result["seed_index"]])
            row["_stratum"] = result.get("stratum", "retry")
            manifest_rows.append(row)
    else:
        manifest_rows = sample

    with sample_path.open("w", encoding="utf-8") as handle:
        for row in manifest_rows:
            handle.write(
                json.dumps(
                    {
                        "seed_index": row["_seed_index"],
                        "stratum": row["_stratum"],
                        "text": row["text"],
                        "context": context_for_model(row),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    generation_schema_path.write_text(
        json.dumps(generation_schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    calls: dict[Any, dict[str, Any]] = {}
    api_results: dict[int, dict[str, Any]] = {}

    def call_with_pacing(row: dict[str, Any]) -> dict[str, Any]:
        result = call_provider(client, model, generation_schema, row)
        if args.pacing_seconds:
            time.sleep(args.pacing_seconds)
        return result

    with ThreadPoolExecutor(max_workers=min(args.workers, len(sample))) as executor:
        for row in sample:
            future = executor.submit(call_with_pacing, row)
            calls[future] = row

        completed = 0
        for future in as_completed(calls):
            row = calls[future]
            api_results[row["_seed_index"]] = future.result()
            completed += 1
            print(
                f"[{completed}/{len(sample)}] seed {row['_seed_index']} terminé",
                flush=True,
            )

    retry_results: list[dict[str, Any]] = []
    for row in sample:
        api_result = api_results[row["_seed_index"]]
        result: dict[str, Any] = {
            "run_id": run_id,
            "provider": args.provider,
            "model": model,
            "schema_version": "0.1.0",
            "seed_index": row["_seed_index"],
            "stratum": row["_stratum"],
            "text": row["text"],
            "input": {
                key: row.get(key)
                for key in ("sentiment_label", "source", "topic", "brand", "aspect")
            },
            "api": {key: value for key, value in api_result.items() if key != "annotation"},
            "annotation": None,
            "raw_annotation": None,
            "validation": {
                "raw_schema_errors": [],
                "raw_semantic_errors": [],
                "offset_repairs": [],
                "final_schema_errors": [],
                "final_semantic_errors": [],
            },
        }
        if api_result["ok"]:
            raw_annotation = api_result["annotation"]
            raw_schema_errors = format_schema_errors(validator, raw_annotation)
            raw_semantic_errors = semantic_errors(raw_annotation, row["text"])
            annotation, repairs = repair_offsets(raw_annotation, row["text"])
            result["annotation"] = annotation
            result["raw_annotation"] = raw_annotation if repairs else None
            result["validation"] = {
                "raw_schema_errors": raw_schema_errors,
                "raw_semantic_errors": raw_semantic_errors,
                "offset_repairs": repairs,
                "final_schema_errors": format_schema_errors(validator, annotation),
                "final_semantic_errors": semantic_errors(annotation, row["text"]),
            }
        retry_results.append(result)

    if base_results:
        retry_by_index = {
            result["seed_index"]: result for result in retry_results
        }
        results = [
            retry_by_index.get(result["seed_index"], result)
            for result in base_results
        ]
    else:
        results = retry_results

    with results_path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")

    report = build_report(
        results=results,
        provider=args.provider,
        model=model,
        run_id=run_id,
        results_path=results_path,
        sample_path=sample_path,
    )
    report_path.write_text(report, encoding="utf-8")

    print(f"RESULTS={results_path}")
    print(f"REPORT={report_path}")
    print(f"GENERATION_SCHEMA={generation_schema_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
