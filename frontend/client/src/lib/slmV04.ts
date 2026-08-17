export interface SlmEvidence {
  text: string;
  start: number | null;
  end: number | null;
}

export interface SlmEntity {
  id: string;
  type: string;
  name: string;
  mention: string | null;
  source: string;
}

export interface SlmAspect {
  family: string;
  attribute: string | null;
  targetEntityId: string | null;
  sentiment: string;
  intensity: string;
  implicit: boolean;
  evidence: SlmEvidence[];
}

export interface SlmAlert {
  type: string;
  severity: string;
  targetEntityId: string | null;
  evidence: SlmEvidence[];
}

export interface SlmAnnotationV04 {
  schemaVersion: string;
  isExploitable: boolean;
  nonExploitableReason: string | null;
  businessRelevance: string;
  authorRole: string;
  requiresParentContext: boolean;
  language: {
    dominant: string;
    detected: string[];
    codeSwitching: boolean;
    scripts: string[];
  };
  entities: SlmEntity[];
  sentiment: {
    label: string;
    intensity: string;
    emotion: string;
    sarcasm: boolean;
    targetEntityIds: string[];
    evidence: SlmEvidence[];
  };
  intents: string[];
  aspects: SlmAspect[];
  alerts: SlmAlert[];
  actionability: {
    actionable: boolean;
    queue: string;
    priority: string;
  };
}

export interface SlmAnalysisEnvelope {
  annotation: SlmAnnotationV04;
  modelVersion: string | null;
  compilerVersion: string | null;
  validationStatus: string;
  inferenceMs: number | null;
}

const FAMILY_LABELS: Record<string, string> = {
  produit_service: "Produit ou service",
  prix_valeur: "Prix et valeur",
  disponibilite_acces: "Disponibilité et accès",
  experience_client: "Expérience client",
  service_client_sav: "Service client et SAV",
  livraison_logistique: "Livraison et logistique",
  digital_technologie: "Digital et technologie",
  communication_information: "Communication et information",
  confiance_reputation: "Confiance et réputation",
  operations_processus: "Opérations et processus",
  emploi_management: "Emploi et management",
  securite_conformite: "Sécurité et conformité",
  ethique_impact: "Éthique et impact",
  marche_innovation: "Marché et innovation",
  infrastructure_service_public: "Infrastructure et service public",
};

const LABELS: Record<string, string> = {
  directe: "Pertinence directe",
  indirecte: "Pertinence indirecte",
  aucune: "Aucune",
  positif: "Positif",
  negatif: "Négatif",
  neutre: "Neutre",
  mixte: "Mixte",
  faible: "Faible",
  moyenne: "Moyenne",
  forte: "Forte",
  elevee: "Élevée",
  consommateur: "Consommateur",
  marque: "Marque",
  moderateur: "Modérateur",
  media: "Média",
  institution: "Institution",
  inconnu: "Rôle inconnu",
  satisfaction: "Satisfaction",
  admiration: "Admiration",
  joie: "Joie",
  confiance: "Confiance",
  gratitude: "Gratitude",
  deception: "Déception",
  frustration: "Frustration",
  colere: "Colère",
  inquietude: "Inquiétude",
  peur: "Peur",
  tristesse: "Tristesse",
  degout: "Dégoût",
  surprise: "Surprise",
  plainte: "Plainte",
  eloge: "Éloge",
  question: "Question",
  demande_information: "Demande d’information",
  demande_aide: "Demande d’aide",
  suggestion: "Suggestion",
  recommandation: "Recommandation",
  comparaison: "Comparaison",
  intention_achat: "Intention d’achat",
  partage_experience: "Partage d’expérience",
  signalement_incident: "Signalement d’incident",
  appel_action: "Appel à l’action",
  promotion_spam: "Promotion ou spam",
  tag_mention: "Mention",
  darija_arabe: "Darija — écriture arabe",
  darija_arabizi: "Darija — arabizi",
  arabe_msa: "Arabe standard",
  francais: "Français",
  anglais: "Anglais",
  tamazight_latin: "Tamazight — latin",
  tamazight_tifinagh: "Tamazight — tifinagh",
  produit: "Équipe produit",
  pricing: "Tarification",
  operations: "Opérations",
  service_client: "Service client",
  logistique: "Logistique",
  digital: "Équipe digitale",
  communication: "Communication",
  rh: "Ressources humaines",
  juridique_conformite: "Juridique et conformité",
  direction: "Direction",
  service_public: "Service public",
  qualite_produit: "Qualité produit",
  securite_sante: "Sécurité ou santé",
  fraude_arnaque: "Fraude ou arnaque",
  rupture_service: "Rupture de service",
  rupture_stock: "Rupture de stock",
  reputation_virale: "Risque réputationnel",
  donnees_confidentialite: "Données et confidentialité",
  harcelement_discrimination: "Harcèlement ou discrimination",
};

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asBoolean(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function asNullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function asRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(asRecord).filter((item) => Object.keys(item).length > 0) : [];
}

function parseEvidence(value: unknown): SlmEvidence[] {
  return asRecords(value)
    .map((item) => ({
      text: asString(item.text),
      start: asNullableNumber(item.start),
      end: asNullableNumber(item.end),
    }))
    .filter((item) => item.text.length > 0);
}

function parseAnnotation(value: unknown): SlmAnnotationV04 | null {
  const record = asRecord(value);
  const schemaVersion = asString(record.schema_version);
  const sentiment = asRecord(record.sentiment);
  if (schemaVersion !== "0.4.0" || !asString(sentiment.label)) return null;

  const language = asRecord(record.language);
  const actionability = asRecord(record.actionability);

  return {
    schemaVersion,
    isExploitable: asBoolean(record.is_exploitable),
    nonExploitableReason: asString(record.non_exploitable_reason) || null,
    businessRelevance: asString(record.business_relevance, "aucune"),
    authorRole: asString(record.author_role, "inconnu"),
    requiresParentContext: asBoolean(record.requires_parent_context),
    language: {
      dominant: asString(language.dominant, "autre"),
      detected: asStringArray(language.detected),
      codeSwitching: asBoolean(language.code_switching),
      scripts: asStringArray(language.scripts),
    },
    entities: asRecords(record.entities).map((item) => ({
      id: asString(item.id),
      type: asString(item.type, "autre"),
      name: asString(item.name),
      mention: asString(item.mention) || null,
      source: asString(item.source, "texte"),
    })),
    sentiment: {
      label: asString(sentiment.label),
      intensity: asString(sentiment.intensity, "faible"),
      emotion: asString(sentiment.emotion, "aucune"),
      sarcasm: asBoolean(sentiment.sarcasm),
      targetEntityIds: asStringArray(sentiment.target_entity_ids),
      evidence: parseEvidence(sentiment.evidence),
    },
    intents: asStringArray(record.intents),
    aspects: asRecords(record.aspects).map((item) => ({
      family: asString(item.family),
      attribute: asString(item.attribute) || null,
      targetEntityId: asString(item.target_entity_id) || null,
      sentiment: asString(item.sentiment, "neutre"),
      intensity: asString(item.intensity, "faible"),
      implicit: asBoolean(item.implicit),
      evidence: parseEvidence(item.evidence),
    })),
    alerts: asRecords(record.alerts).map((item) => ({
      type: asString(item.type),
      severity: asString(item.severity, "faible"),
      targetEntityId: asString(item.target_entity_id) || null,
      evidence: parseEvidence(item.evidence),
    })),
    actionability: {
      actionable: asBoolean(actionability.actionable),
      queue: asString(actionability.queue, "aucune"),
      priority: asString(actionability.priority, "faible"),
    },
  };
}

export function parseSlmAnalysis(value: unknown): SlmAnalysisEnvelope | null {
  const record = asRecord(value);
  const analysisRecord = asRecord(record.analysis);
  const directAnnotation = parseAnnotation(record.annotation ?? record.slm_annotation);
  const nestedAnnotation = parseAnnotation(analysisRecord.annotation);
  const annotation = nestedAnnotation ?? directAnnotation;
  if (!annotation) return null;

  const metadata = Object.keys(analysisRecord).length > 0 ? analysisRecord : record;
  return {
    annotation,
    modelVersion: asString(metadata.model_version) || null,
    compilerVersion: asString(metadata.compiler_version) || null,
    validationStatus: asString(metadata.validation_status, "unknown"),
    inferenceMs: asNullableNumber(metadata.inference_ms),
  };
}

export function collectAnnotationEvidence(annotation: SlmAnnotationV04): SlmEvidence[] {
  const evidence = [
    ...annotation.sentiment.evidence,
    ...annotation.aspects.flatMap((aspect) => aspect.evidence),
    ...annotation.alerts.flatMap((alert) => alert.evidence),
  ];
  const seen = new Set<string>();
  return evidence.filter((item) => {
    const key = `${item.start ?? ""}:${item.end ?? ""}:${item.text}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function entityName(annotation: SlmAnnotationV04, entityId: string | null): string | null {
  if (!entityId) return null;
  return annotation.entities.find((entity) => entity.id === entityId)?.name ?? null;
}

export function formatSlmLabel(value: string): string {
  if (!value) return "Non renseigné";
  return FAMILY_LABELS[value] ?? LABELS[value] ?? value
    .replaceAll("_", " ")
    .replace(/^./, (character) => character.toUpperCase());
}

export function sentimentTone(value: string): string {
  if (value === "positif") return "bg-success/10 text-success";
  if (value === "negatif") return "bg-error-container text-error";
  if (value === "mixte") return "bg-insight-container text-insight";
  return "bg-surface-container-high text-on-surface-variant";
}
