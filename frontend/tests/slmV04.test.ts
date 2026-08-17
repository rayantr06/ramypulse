import assert from "node:assert/strict";
import test from "node:test";

import {
  collectAnnotationEvidence,
  entityName,
  formatSlmLabel,
  parseSlmAnalysis,
} from "../client/src/lib/slmV04";

const annotation = {
  schema_version: "0.4.0",
  monitoring_target: {
    scope: "organisation",
    entity_name: "Algérie Télécom",
    entity_type: "organisation",
  },
  author_role: "consommateur",
  requires_parent_context: false,
  is_exploitable: true,
  non_exploitable_reason: null,
  business_relevance: "directe",
  language: {
    dominant: "darija_arabizi",
    detected: ["darija", "francais"],
    code_switching: true,
    scripts: ["latin"],
  },
  entities: [
    {
      id: "ent_1",
      type: "service",
      name: "internet",
      mention: "internet",
      start: 0,
      end: 8,
      source: "texte",
    },
  ],
  sentiment: {
    label: "negatif",
    intensity: "forte",
    emotion: "frustration",
    sarcasm: false,
    target_entity_ids: ["ent_1"],
    evidence: [{ text: "y9ta3 bezaf", start: 9, end: 20 }],
  },
  intents: ["plainte", "partage_experience"],
  aspects: [
    {
      family: "digital_technologie",
      attribute: "connexion_reseau",
      target_entity_id: "ent_1",
      sentiment: "negatif",
      intensity: "forte",
      implicit: false,
      evidence: [{ text: "internet y9ta3 bezaf", start: 0, end: 20 }],
    },
  ],
  alerts: [],
  actionability: { actionable: true, queue: "digital", priority: "moyenne" },
};

test("parseSlmAnalysis reads the canonical nested V0.4 envelope", () => {
  const result = parseSlmAnalysis({
    analysis: {
      annotation,
      model_version: "lidal-slm-0.8b-s1",
      compiler_version: "wire-v0.4",
      validation_status: "valid",
      inference_ms: 2680,
    },
  });

  assert.equal(result?.annotation.sentiment.label, "negatif");
  assert.equal(result?.annotation.language.codeSwitching, true);
  assert.equal(result?.annotation.aspects[0]?.family, "digital_technologie");
  assert.equal(result?.modelVersion, "lidal-slm-0.8b-s1");
  assert.equal(result?.inferenceMs, 2680);
  assert.equal(entityName(result!.annotation, "ent_1"), "internet");
});

test("parseSlmAnalysis accepts additive annotation fields on legacy explorer routes", () => {
  const result = parseSlmAnalysis({ annotation, validation_status: "valid" });
  assert.equal(result?.annotation.schemaVersion, "0.4.0");
  assert.deepEqual(result?.annotation.intents, ["plainte", "partage_experience"]);
});

test("missing validation metadata remains unknown instead of claiming validity", () => {
  const result = parseSlmAnalysis({ annotation });
  assert.equal(result?.validationStatus, "unknown");
});

test("V0.4 helpers deduplicate evidence and expose business labels", () => {
  const result = parseSlmAnalysis({ annotation });
  const evidence = collectAnnotationEvidence(result!.annotation);

  assert.equal(evidence.length, 2);
  assert.equal(formatSlmLabel("service_client_sav"), "Service client et SAV");
  assert.equal(formatSlmLabel("darija_arabizi"), "Darija — arabizi");
});

test("legacy explorer records remain explicitly outside the V0.4 contract", () => {
  assert.equal(parseSlmAnalysis({ sentiment_label: "negatif", aspect: "prix" }), null);
});
