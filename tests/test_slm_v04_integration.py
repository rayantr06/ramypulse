"""Tests du contrat d'inférence compact LIDAL SLM V0.4."""

from __future__ import annotations

import json

from core.database import DatabaseManager
from core.analysis.slm_v04_client import analyze_with_slm
from core.analysis.slm_v04_compiler import compile_slm_output, legacy_projection
from core.normalization import normalizer_pipeline
from inference.slm_v04_service import _build_prompt


TEXT = "internet y9ta3 bezaf service client ma yjawbouch"
TARGET = {
    "scope": "organisation",
    "entity_name": "Algérie Télécom",
    "entity_type": "organisation",
}
COMPACT_OUTPUT = """<answer>
scan → exploitable,directe,darija_arabizi[darija/francais|l|cs],c
ev_1="internet y9ta3 bezaf"
ev_2="service client ma yjawbouch"
ent_1:organisation:contexte="Algérie Télécom"
ent_2:service:texte="internet"
ent_3:service:texte="service client"
ev_1+ev_2 → sentiment:-:forte:frustration@ent_1,ent_2,ent_3
ev_1 → digital_technologie.connexion_reseau@ent_2:-:forte
ev_2 → service_client_sav.reactivite@ent_3:-:forte
∴ plainte,partage_experience
</answer>"""


def test_compiler_builds_valid_annotation_and_deterministic_fields() -> None:
    result = compile_slm_output(COMPACT_OUTPUT, text=TEXT, monitoring_target=TARGET)

    assert result.validation_status == "valid"
    assert result.annotation is not None
    annotation = result.annotation
    assert annotation["monitoring_target"] == TARGET
    assert annotation["sentiment"]["label"] == "negatif"
    assert annotation["sentiment"]["evidence"][0] == {
        "text": "internet y9ta3 bezaf",
        "start": 0,
        "end": 20,
    }
    assert annotation["entities"][1]["start"] == 0
    assert annotation["entities"][2]["start"] == 21
    assert annotation["actionability"] == {
        "actionable": True,
        "queue": "digital",
        "priority": "moyenne",
    }


def test_compiler_rejects_an_incomplete_model_answer() -> None:
    result = compile_slm_output(
        "<answer>scan → exploitable,directe,francais[francais|l],c</answer>",
        text="Service lent",
        monitoring_target=TARGET,
    )

    assert result.validation_status == "invalid"
    assert result.annotation is None
    assert result.errors


def test_legacy_projection_keeps_old_screens_compatible() -> None:
    result = compile_slm_output(COMPACT_OUTPUT, text=TEXT, monitoring_target=TARGET)
    assert result.annotation is not None

    assert legacy_projection(result.annotation) == {
        "sentiment_label": "très_négatif",
        "aspect": "digital_technologie",
    }


def test_client_compiles_service_output_and_preserves_provenance(monkeypatch) -> None:
    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "raw_model_output": COMPACT_OUTPUT,
                "model_version": "answer_only_s1",
                "inference_ms": 2710,
                "created_at": "2026-08-17T10:00:00+00:00",
            }

    class _Session:
        def __init__(self) -> None:
            self.payload: dict[str, object] | None = None

        def post(self, _url: str, **kwargs):
            self.payload = kwargs["json"]
            return _Response()

    session = _Session()
    monkeypatch.setattr("config.SLM_V04_BASE_URL", "http://slm.test:8010")
    result = analyze_with_slm(
        TEXT,
        monitoring_target=TARGET,
        topic="télécommunications",
        session=session,  # type: ignore[arg-type]
    )

    assert result.compilation.validation_status == "valid"
    assert result.model_version == "answer_only_s1"
    assert result.inference_ms == 2710
    assert session.payload == {
        "text": TEXT,
        "context": {
            "monitoring_target": TARGET,
            "topic": "télécommunications",
        },
    }


def test_inference_prompt_matches_training_contract() -> None:
    prompt = _build_prompt(
        TEXT,
        {"monitoring_target": TARGET, "topic": "télécommunications"},
    )

    assert prompt == (
        "### Contexte ###\n"
        "scope=organisation entite=Algérie Télécom secteur=télécommunications\n\n"
        f"### Commentaire ###\n{TEXT}\n\n"
        "### Reponse compacte ###\n"
    )


def test_normalizer_persists_annotation_and_model_provenance(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "slm-v04.db"
    database = DatabaseManager(db_path)
    database.create_tables()
    database.connection.execute(
        """
        INSERT INTO sources (
            source_id, client_id, source_name, platform, source_type, owner_type
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("src-1", "tenant-1", "Google Maps", "google_maps", "reviews", "public"),
    )
    database.connection.execute(
        """
        INSERT INTO raw_documents (
            raw_document_id, client_id, source_id, raw_text, raw_metadata,
            collected_at, is_normalized
        ) VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (
            "raw-1",
            "tenant-1",
            "src-1",
            TEXT,
            json.dumps(
                {
                    "channel": "google_maps",
                    "source_url": "https://maps.example/review-1",
                    "monitoring_target": TARGET,
                },
                ensure_ascii=False,
            ),
            "2026-08-17T10:00:00+00:00",
        ),
    )
    database.connection.commit()
    database.close()

    compiled = compile_slm_output(COMPACT_OUTPUT, text=TEXT, monitoring_target=TARGET)
    assert compiled.annotation is not None
    monkeypatch.setattr(
        normalizer_pipeline,
        "_analyze_text",
        lambda _text: {
            "global_sentiment": "neutre",
            "confidence": 0.5,
            "aspects": [],
            "aspect_sentiments": [],
        },
    )
    monkeypatch.setattr(
        normalizer_pipeline,
        "_resolve_entities",
        lambda *_args, **_kwargs: {
            "brand": None,
            "competitor": None,
            "product": None,
            "product_line": None,
            "sku": None,
            "wilaya": None,
        },
    )
    monkeypatch.setattr(
        normalizer_pipeline,
        "_analyze_slm_v04",
        lambda *_args, **_kwargs: {
            "annotation": compiled.annotation,
            "raw_model_output": COMPACT_OUTPUT,
            "validation_status": "valid",
            "model_version": "answer_only_s1",
            "compiler_version": compiled.compiler_version,
            "inference_ms": 2710,
            "annotation_created_at": "2026-08-17T10:00:00+00:00",
            "legacy_projection": legacy_projection(compiled.annotation),
        },
    )

    result = normalizer_pipeline.run_normalization_job(db_path=db_path)

    assert result["processed_count"] == 1
    database = DatabaseManager(db_path)
    row = database.connection.execute(
        """
        SELECT annotation_json, raw_model_output, validation_status, model_version,
               compiler_version, inference_ms, sentiment_label, aspect, source_url
        FROM enriched_signals
        """
    ).fetchone()
    database.close()
    assert row is not None
    assert json.loads(row["annotation_json"])["schema_version"] == "0.4.0"
    assert row["raw_model_output"] == COMPACT_OUTPUT
    assert row["validation_status"] == "valid"
    assert row["model_version"] == "answer_only_s1"
    assert row["compiler_version"] == compiled.compiler_version
    assert row["inference_ms"] == 2710
    assert row["sentiment_label"] == "très_négatif"
    assert row["aspect"] == "digital_technologie"
    assert row["source_url"] == "https://maps.example/review-1"
