"""Compile la sortie compacte du SLM en annotation métier V0.4.

Le modèle ne calcule ni les offsets, ni la cible surveillée, ni le routage.
Ces informations déterministes sont reconstruites ici puis validées contre le
JSON Schema canonique avant toute persistance.
"""

from __future__ import annotations

import copy
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

import config

SCHEMA_PATH = (
    Path(config.BASE_DIR)
    / "docs"
    / "slm_v2"
    / "business_comment_annotation_v0.4.schema.json"
)
COMPILER_VERSION = "wire-v0.4.1"

SIGN_TO_SENTIMENT = {"+": "positif", "-": "negatif", "±": "mixte", "0": "neutre"}
ROLE_FROM_WIRE = {
    "c": "consommateur",
    "m": "marque",
    "d": "moderateur",
    "j": "media",
    "i": "institution",
    "?": "inconnu",
}
SCRIPT_FROM_WIRE = {
    "a": "arabe",
    "l": "latin",
    "t": "tifinagh",
    "n": "chiffres",
    "x": "autre",
}
SEVERITY_SCORE = {"faible": 1, "moyenne": 2, "elevee": 3}
SEVERITY_FROM_SCORE = {value: key for key, value in SEVERITY_SCORE.items()}
QUEUE_BY_FAMILY = {
    "produit_service": "produit",
    "prix_valeur": "pricing",
    "disponibilite_acces": "operations",
    "experience_client": "service_client",
    "service_client_sav": "service_client",
    "livraison_logistique": "logistique",
    "digital_technologie": "digital",
    "communication_information": "communication",
    "confiance_reputation": "communication",
    "operations_processus": "operations",
    "emploi_management": "rh",
    "securite_conformite": "juridique_conformite",
    "ethique_impact": "direction",
    "marche_innovation": "direction",
    "infrastructure_service_public": "service_public",
}

_BACKSLASH = chr(92)
_QUOTED = r'(?:[^"\\]|\\.)*'


@dataclass(frozen=True)
class CompilationResult:
    """Résultat auditable d'une compilation de sortie modèle."""

    annotation: dict[str, Any] | None
    validation_status: str
    errors: list[str] = field(default_factory=list)
    repairs: dict[str, int] = field(default_factory=dict)
    compiler_version: str = COMPILER_VERSION


def _unescape(value: str) -> str:
    return value.replace(_BACKSLASH + '"', '"').replace(_BACKSLASH * 2, _BACKSLASH)


def resolve_evidence(evidence: object, text: str) -> list[dict[str, object]]:
    """Recalcule systématiquement les offsets depuis les extraits littéraux."""

    values: list[object]
    if isinstance(evidence, str):
        values = [evidence]
    elif isinstance(evidence, list):
        values = evidence
    else:
        values = []

    resolved: list[dict[str, object]] = []
    for value in values:
        literal = value.get("text") if isinstance(value, dict) else value
        if not isinstance(literal, str) or not literal.strip():
            continue
        start = text.find(literal)
        if start < 0:
            continue
        resolved.append({"text": literal, "start": start, "end": start + len(literal)})
    return resolved


def resolve_entity(entity: dict[str, Any], text: str) -> None:
    """Résout la mention d'une entité ou la rebascule honnêtement en contexte."""

    if entity.get("source") == "contexte":
        entity["mention"] = entity["start"] = entity["end"] = None
        return
    mention = entity.get("mention")
    start = text.find(mention) if isinstance(mention, str) and mention else -1
    if start < 0:
        entity["source"] = "contexte"
        entity["mention"] = entity["start"] = entity["end"] = None
        return
    entity["start"] = start
    entity["end"] = start + len(mention)


def derive_actionability(annotation: dict[str, Any]) -> dict[str, object]:
    """Dérive le routage selon les décisions D2/D3 du contrat."""

    alerts = list(annotation.get("alerts") or [])
    aspects = list(annotation.get("aspects") or [])
    is_organisation = (
        (annotation.get("monitoring_target") or {}).get("scope") == "organisation"
    )
    negative_aspects = [item for item in aspects if item.get("sentiment") == "negatif"]
    if alerts and is_organisation:
        priority = SEVERITY_FROM_SCORE[
            max(SEVERITY_SCORE.get(item.get("severity"), 1) for item in alerts)
        ]
    elif is_organisation and any(item.get("intensity") == "forte" for item in negative_aspects):
        priority = "moyenne"
    else:
        priority = "faible"

    dominant = negative_aspects[0] if negative_aspects else (aspects[0] if aspects else None)
    return {
        "actionable": bool(is_organisation and (alerts or negative_aspects)),
        "queue": QUEUE_BY_FAMILY.get((dominant or {}).get("family"), "aucune")
        if is_organisation
        else "aucune",
        "priority": priority,
    }


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    """Charge une seule fois le contrat canonique V0.4."""

    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator() -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(load_schema())


@lru_cache(maxsize=1)
def _allowed_attributes() -> dict[str, set[str]]:
    allowed: dict[str, set[str]] = {}
    for rule in load_schema()["$defs"]["aspect"].get("allOf", []):
        family = (((rule.get("if") or {}).get("properties") or {}).get("family") or {}).get("const")
        values = (((rule.get("then") or {}).get("properties") or {}).get("attribute") or {}).get("enum")
        if family and values:
            allowed[family] = set(values)
    return allowed


def _deduplicate(values: list[Any]) -> list[Any]:
    unique: list[Any] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _repair_deterministic(annotation: dict[str, Any]) -> Counter[str]:
    repairs: Counter[str] = Counter()
    for path in (
        ("intents",),
        ("language", "detected"),
        ("language", "scripts"),
        ("sentiment", "target_entity_ids"),
    ):
        parent: dict[str, Any] = annotation
        for key in path[:-1]:
            candidate = parent.get(key)
            parent = candidate if isinstance(candidate, dict) else {}
        values = parent.get(path[-1])
        if isinstance(values, list):
            unique = _deduplicate(values)
            if unique != values:
                repairs[f"{'.'.join(path)}_deduplicated"] += len(values) - len(unique)
                parent[path[-1]] = unique

    valid_aspects: list[dict[str, Any]] = []
    allowed_attributes = _allowed_attributes()
    for aspect in annotation.get("aspects") or []:
        if not aspect.get("evidence"):
            repairs["aspect_without_evidence_removed"] += 1
            continue
        attribute = aspect.get("attribute")
        allowed = allowed_attributes.get(aspect.get("family"))
        if attribute is not None and allowed is not None and attribute not in allowed:
            aspect.pop("attribute", None)
            repairs["invalid_optional_attribute_removed"] += 1
        valid_aspects.append(aspect)
    annotation["aspects"] = valid_aspects

    valid_alerts = []
    for alert in annotation.get("alerts") or []:
        if not alert.get("evidence"):
            repairs["alert_without_evidence_removed"] += 1
            continue
        valid_alerts.append(alert)
    annotation["alerts"] = valid_alerts

    if not annotation.get("is_exploitable"):
        repairs["non_exploitable_aspects_removed"] += len(annotation["aspects"])
        repairs["non_exploitable_alerts_removed"] += len(annotation["alerts"])
        annotation["aspects"] = []
        annotation["alerts"] = []

    annotation["actionability"] = derive_actionability(annotation)
    return +repairs


def decode_compact_output(
    raw_output: str,
    *,
    text: str,
    monitoring_target: dict[str, Any],
) -> dict[str, Any]:
    """Reconstruit l'annotation V0.4 depuis le bloc ``<answer>`` du SLM."""

    if "<answer>" in raw_output:
        body = raw_output.split("<answer>", 1)[1].split("</answer>", 1)[0].strip()
    else:
        body = raw_output.replace("<think>", "").replace("</think>", "").strip()
    lines = [line.strip() for line in body.splitlines() if line.strip()]

    evidence_map: dict[str, str] = {}
    entities: list[dict[str, Any]] = []
    aspects: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    sentiment: dict[str, Any] = {}
    intents: list[str] = []
    scan: dict[str, Any] = {}

    for line in lines:
        if line.startswith("scan → "):
            match = re.match(
                r"scan → ([^,]+),([^,]+),([^\[]+)\[([^|]*)\|([^|\]]*)(\|cs)?\],(.)(\^?)",
                line,
            )
            if not match:
                continue
            state, relevance, dominant, detected, scripts, code_switch, role, parent = match.groups()
            scan = {
                "is_exploitable": state == "exploitable",
                "non_exploitable_reason": None if state == "exploitable" else state.split(":", 1)[1],
                "business_relevance": relevance,
                "language": {
                    "dominant": dominant,
                    "detected": [value for value in detected.split("/") if value],
                    "code_switching": bool(code_switch),
                    "scripts": [SCRIPT_FROM_WIRE.get(value, "autre") for value in scripts],
                },
                "author_role": ROLE_FROM_WIRE.get(role, "inconnu"),
                "requires_parent_context": parent == "^",
            }
        elif re.match(r'^ev_\d+="', line):
            match = re.match(rf'^(ev_\d+)="({_QUOTED})"$', line)
            if match:
                identifier, literal = match.groups()
                evidence_map[identifier] = _unescape(literal)
        elif re.match(r"^ent_\d+:", line):
            match = re.match(
                rf'^(ent_\d+):([a-z_]+):([a-z]+)="({_QUOTED})"(?:~"({_QUOTED})")?$',
                line,
            )
            if match:
                identifier, entity_type, source, name, mention = match.groups()
                name = _unescape(name)
                mention = _unescape(mention) if mention else None
                entities.append(
                    {
                        "id": identifier,
                        "type": entity_type,
                        "source": source,
                        "name": name,
                        "mention": (mention or name) if source == "texte" else None,
                        "start": None,
                        "end": None,
                    }
                )
        elif " → sentiment:" in line:
            source, remainder = line.split(" → sentiment:", 1)
            match = re.match(r"^(.)(!?):([a-z]+):([a-z_]+)@(.*)$", remainder)
            if match:
                sign, sarcasm, intensity, emotion, targets = match.groups()
                sentiment = {
                    "label": SIGN_TO_SENTIMENT.get(sign, "neutre"),
                    "intensity": intensity,
                    "emotion": emotion,
                    "sarcasm": sarcasm == "!",
                    "target_entity_ids": [value for value in targets.split(",") if value not in {"", "-"}],
                    "evidence": [evidence_map[key] for key in source.split("+") if key in evidence_map],
                }
        elif " → !" in line:
            source, remainder = line.split(" → !", 1)
            match = re.match(r"^([a-z_]+)(?:@(ent_\d+))?:([a-z]+)$", remainder)
            if match:
                alert_type, target, severity = match.groups()
                alerts.append(
                    {
                        "type": alert_type,
                        "severity": severity,
                        "target_entity_id": target,
                        "evidence": [evidence_map[key] for key in source.split("+") if key in evidence_map],
                    }
                )
        elif " → " in line:
            source, remainder = line.split(" → ", 1)
            match = re.match(
                r"^([a-z_]+)(?:\.([a-z_]+))?(?:@(ent_\d+))?:(.)(~?):([a-z]+)$",
                remainder,
            )
            if match:
                family, attribute, target, sign, implicit, intensity = match.groups()
                aspect: dict[str, Any] = {
                    "family": family,
                    "target_entity_id": target,
                    "sentiment": SIGN_TO_SENTIMENT.get(sign, "negatif"),
                    "intensity": intensity,
                    "implicit": implicit == "~",
                    "evidence": [evidence_map[key] for key in source.split("+") if key in evidence_map],
                }
                if attribute:
                    aspect["attribute"] = attribute
                aspects.append(aspect)
        elif line.startswith("∴"):
            intents = [value for value in line[1:].strip().split(",") if value]

    annotation = {
        **scan,
        "monitoring_target": copy.deepcopy(monitoring_target),
        "entities": entities,
        "sentiment": sentiment,
        "intents": intents,
        "aspects": aspects,
        "alerts": alerts,
        "schema_version": load_schema()["properties"]["schema_version"]["const"],
    }
    for block in [sentiment, *aspects, *alerts]:
        if block:
            block["evidence"] = resolve_evidence(block.get("evidence"), text)
    for entity in entities:
        resolve_entity(entity, text)
    return annotation


def compile_slm_output(
    raw_output: str,
    *,
    text: str,
    monitoring_target: dict[str, Any],
) -> CompilationResult:
    """Compile, répare mécaniquement et valide une sortie du modèle."""

    try:
        annotation = decode_compact_output(
            raw_output,
            text=text,
            monitoring_target=monitoring_target,
        )
        repairs = _repair_deterministic(annotation)
        errors = sorted(_validator().iter_errors(annotation), key=lambda error: list(error.path))
        if errors:
            return CompilationResult(
                annotation=None,
                validation_status="invalid",
                errors=[error.message for error in errors[:5]],
                repairs=dict(repairs),
            )
        return CompilationResult(
            annotation=annotation,
            validation_status="valid",
            repairs=dict(repairs),
        )
    except Exception as exc:
        return CompilationResult(
            annotation=None,
            validation_status="invalid",
            errors=[str(exc)],
        )


def legacy_projection(annotation: dict[str, Any]) -> dict[str, str | None]:
    """Projette V0.4 vers les deux champs encore utilisés par les écrans V2."""

    sentiment = annotation.get("sentiment") or {}
    label = str(sentiment.get("label") or "neutre")
    intensity = str(sentiment.get("intensity") or "faible")
    if label == "positif" and intensity == "forte":
        legacy_sentiment = "très_positif"
    elif label == "negatif" and intensity == "forte":
        legacy_sentiment = "très_négatif"
    else:
        legacy_sentiment = label
    aspects = list(annotation.get("aspects") or [])
    return {
        "sentiment_label": legacy_sentiment,
        "aspect": aspects[0].get("family") if aspects else None,
    }
