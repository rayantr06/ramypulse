import type {
  V3ActionItem,
  V3AnalyticsOverview,
  V3Case,
  V3MentionEvidence,
  V3Monitor,
  V3Notification,
  V3Observation,
  V3Report,
  V3Signal,
  V3SourcePlatform,
} from "@shared/v3";

type LeticiaSlmAnalysis = {
  evidence: string;
  normalizedText: string;
  aspect: "disponibilite";
  recommendation: string;
};

type LeticiaDemoInputChannel = V3SourcePlatform | "audio";

export type LeticiaDemoScenario = {
  authorizedInputChannels: LeticiaDemoInputChannel[];
  mentions: V3MentionEvidence[];
  monitors: V3Monitor[];
  observations: V3Observation[];
  signals: V3Signal[];
  cases: V3Case[];
  actions: V3ActionItem[];
  overview: V3AnalyticsOverview;
  reports: V3Report[];
  notifications: V3Notification[];
  slmAnalysesByMentionId: Record<string, LeticiaSlmAnalysis>;
};

const availabilityEvidence: Array<V3MentionEvidence & { evidence: string }> = [
  {
    id: "m_oran_arabizi_01",
    text: "Ma l9itch le produit fi Oran depuis trois jours.",
    evidence: "Ma l9itch le produit fi Oran",
    source: "facebook",
    sourceUrl: "https://example.invalid/leticia/facebook/m_oran_arabizi_01",
    publishedAt: "2026-08-18T08:12:00Z",
    language: "darija_arabizi",
    territory: "Oran",
    sentiment: "negatif",
    aspects: ["disponibilite"],
    annotationStatus: "valid",
  },
  {
    id: "m_oran_arabe_02",
    text: "المنتج ماكانش متوفر في المحل بوهران هذا الأسبوع",
    evidence: "ماكانش متوفر في المحل بوهران",
    source: "google_maps",
    sourceUrl: "https://example.invalid/leticia/google-maps/m_oran_arabe_02",
    publishedAt: "2026-08-18T09:04:00Z",
    language: "darija_arabe",
    territory: "Oran",
    sentiment: "negatif",
    aspects: ["disponibilite"],
    annotationStatus: "valid",
  },
  {
    id: "m_oran_fr_03",
    text: "Produit indisponible dans deux points de vente à Oran.",
    evidence: "Produit indisponible",
    source: "youtube",
    sourceUrl: "https://example.invalid/leticia/youtube/m_oran_fr_03",
    publishedAt: "2026-08-18T09:48:00Z",
    language: "francais",
    territory: "Oran",
    sentiment: "negatif",
    aspects: ["disponibilite"],
    annotationStatus: "valid",
  },
];

export const LETICIA_DEMO_SCENARIO: LeticiaDemoScenario = {
  authorizedInputChannels: ["facebook", "google_maps", "audio", "youtube"],
  monitors: [{ id: "mon_lidal_availability", organizationId: "demo-leticia-2026", name: "Disponibilité produits LIDAL", objective: "issue", targetType: "product", targetName: "Produits LIDAL", aliases: ["LIDAL", "ليدال", "produit LIDAL"], exclusions: ["emploi", "recrutement"], languages: ["francais", "darija_arabe", "darija_arabizi"], territories: ["Oran", "Alger", "Constantine"], sources: ["facebook", "google_maps", "youtube"], competitors: [], frequencyMinutes: 180, maxMonthlyDocuments: 12_000, maxMonthlyCostDzd: 18_000, active: true, lastCollectedAt: "2026-08-18T10:15:00Z", coverageNote: "Scénario déterministe avec sources anonymisées." }],
  mentions: [
    ...availabilityEvidence.map(({ evidence: _evidence, ...mention }) => mention),
    { id: "m_alger_fr_04", text: "J'ai trouvé le produit sans difficulté à Alger ce matin.", source: "facebook", sourceUrl: "https://example.invalid/leticia/facebook/m_alger_fr_04", publishedAt: "2026-08-18T07:45:00Z", language: "francais", territory: "Alger", sentiment: "positif", aspects: ["disponibilite"], annotationStatus: "valid" },
    { id: "m_oran_arabizi_05", text: "Rani dourt 3 magasins, ma kayench stock à Oran.", source: "facebook", sourceUrl: "https://example.invalid/leticia/facebook/m_oran_arabizi_05", publishedAt: "2026-08-18T10:02:00Z", language: "darija_arabizi", territory: "Oran", sentiment: "negatif", aspects: ["disponibilite"], annotationStatus: "valid" },
    { id: "m_constantine_arabe_06", text: "لقيت المنتج متوفر في قسنطينة والسعر مناسب", source: "google_maps", sourceUrl: "https://example.invalid/leticia/google-maps/m_constantine_arabe_06", publishedAt: "2026-08-18T06:58:00Z", language: "darija_arabe", territory: "Constantine", sentiment: "positif", aspects: ["disponibilite", "prix"], annotationStatus: "valid" },
    { id: "m_oran_fr_07", text: "Le magasin m'a indiqué une livraison demain pour le réassort à Oran.", source: "youtube", sourceUrl: "https://example.invalid/leticia/youtube/m_oran_fr_07", publishedAt: "2026-08-18T10:21:00Z", language: "francais", territory: "Oran", sentiment: "neutre", aspects: ["disponibilite"], annotationStatus: "pending" },
    { id: "m_alger_arabizi_08", text: "Stock disponible chez nous, service rapide.", source: "facebook", sourceUrl: "https://example.invalid/leticia/facebook/m_alger_arabizi_08", publishedAt: "2026-08-18T09:28:00Z", language: "darija_arabizi", territory: "Alger", sentiment: "positif", aspects: ["disponibilite", "reactivite"], annotationStatus: "valid" },
  ],
  observations: [{ id: "obs_oran_availability", monitorId: "mon_lidal_availability", title: "Indisponibilité signalée dans des points de vente à Oran", summary: "Trois langues concordent sur une rupture de disponibilité à Oran.", mentionCount: 4, sentiment: "negatif", aspects: ["disponibilite"], firstSeenAt: "2026-08-18T08:12:00Z", lastSeenAt: "2026-08-18T10:02:00Z", evidenceIds: ["m_oran_arabizi_01", "m_oran_arabe_02", "m_oran_fr_03", "m_oran_arabizi_05"] }],
  signals: [{ id: "sig_oran_availability", monitorId: "mon_lidal_availability", title: "Disponibilité à vérifier à Oran", summary: "Des clients signalent une indisponibilité dans plusieurs points de vente d'Oran.", severity: "high", status: "confirmed", signalType: "recurrence", detectedAt: "2026-08-18T10:20:00Z", mentionCount: 4, velocityPercent: 67, confidence: 0.91, territory: "Oran", observationIds: ["obs_oran_availability"], evidenceIds: ["m_oran_arabizi_01", "m_oran_arabe_02", "m_oran_fr_03"], explanation: "Les preuves en darija arabizi, arabe et français décrivent une indisponibilité à Oran.", priorityScore: 81, priorityFactors: [{ label: "Gravité", value: 80, weight: 0.35 }, { label: "Volume", value: 64, weight: 0.25 }, { label: "Confiance", value: 91, weight: 0.4 }] }],
  cases: [{ id: "case_oran_availability", signalId: "sig_oran_availability", title: "Vérifier la disponibilité LIDAL à Oran", status: "in_progress", priority: "high", ownerId: "u_leticia", ownerName: "Leticia M.", dueAt: "2026-08-18T15:00:00Z", expectedOutcome: "Confirmer le stock avant tout réassort ciblé.", openedAt: "2026-08-18T10:25:00Z", updatedAt: "2026-08-18T10:30:00Z", actionCount: 2, overdueActionCount: 0 }],
  actions: [
    { id: "act_verify_oran_stock", caseId: "case_oran_availability", title: "Vérifier le stock des points de vente d'Oran", description: "Confirmer les niveaux de stock avant d'engager un réassort ciblé.", status: "in_progress", ownerId: "u_leticia", ownerName: "Leticia M.", dueAt: "2026-08-18T12:00:00Z", expectedImpact: "Éviter un réassort fondé sur un signal non confirmé.", metricId: "availability_confirmation_rate", baselineValue: 0, resultValue: null },
    { id: "act_replenish_oran", caseId: "case_oran_availability", title: "Préparer un réassort ciblé après vérification", description: "Planifier le réassort uniquement si la rupture est confirmée par les points de vente.", status: "open", ownerId: "u_logistics", ownerName: "Équipe logistique", dueAt: "2026-08-18T16:00:00Z", expectedImpact: "Rétablir la disponibilité dans les magasins confirmés.", metricId: "oran_stockout_mentions", baselineValue: 4, resultValue: null },
  ],
  overview: { period: { start: "2026-08-11T00:00:00Z", end: "2026-08-18T23:59:59Z", comparisonStart: "2026-08-04T00:00:00Z", comparisonEnd: "2026-08-10T23:59:59Z" }, qualifiedMentions: 8, collectedDocuments: 8, validAnnotations: 7, analyticalCoveragePercent: 87.5, netSentiment: -25, netSentimentDelta: -18, insufficientSample: false, distribution: { positif: 3, negatif: 4, neutre: 1, mixte: 0 }, negativeRatePercent: 50, openSignalsBySeverity: { critical: 0, high: 1, medium: 0, low: 0 }, medianTimeToOwnershipHours: 0.1, overdueActions: 0, topDrivers: [{ aspect: "Disponibilité", deltaPoints: -18, mentionCount: 5 }], sourceHealth: [{ source: "facebook", status: "healthy", successRatePercent: 100, freshnessMinutes: 12, collectedDocuments: 4, analyticalCoveragePercent: 100 }, { source: "google_maps", status: "healthy", successRatePercent: 100, freshnessMinutes: 18, collectedDocuments: 2, analyticalCoveragePercent: 100 }, { source: "youtube", status: "healthy", successRatePercent: 100, freshnessMinutes: 22, collectedDocuments: 2, analyticalCoveragePercent: 100 }] },
  reports: [{ id: "rpt_oran_availability", title: "Disponibilité LIDAL à Oran", reportType: "territory", periodStart: "2026-08-18T00:00:00Z", periodEnd: "2026-08-18T23:59:59Z", status: "ready", generatedAt: "2026-08-18T10:35:00Z", downloadUrl: null, evidenceCount: 4 }],
  notifications: [{ id: "notif_oran_signal", title: "Signal disponibilité à Oran", body: "Vérifier le stock avant tout réassort ciblé.", kind: "signal", read: false, createdAt: "2026-08-18T10:20:00Z", href: "/signals" }, { id: "notif_oran_action", title: "Action assignée à Leticia", body: "Vérifier les stocks des points de vente d'Oran.", kind: "assignment", read: false, createdAt: "2026-08-18T10:26:00Z", href: "/actions" }],
  slmAnalysesByMentionId: Object.fromEntries(availabilityEvidence.map(({ id, evidence, text }) => [id, { evidence, normalizedText: text, aspect: "disponibilite", recommendation: "Vérifier le stock avant un réassort ciblé à Oran." }])),
};

export function validateLeticiaDemoScenario(): string[] {
  const errors: string[] = [];
  const requiredChannels: LeticiaDemoInputChannel[] = ["facebook", "google_maps", "audio", "youtube"];
  const mentionIds = new Set(LETICIA_DEMO_SCENARIO.mentions.map((mention) => mention.id));
  const caseIds = new Set(LETICIA_DEMO_SCENARIO.cases.map((item) => item.id));
  for (const mention of LETICIA_DEMO_SCENARIO.mentions) if (!mention.sourceUrl?.startsWith("https://example.invalid/")) errors.push(`Mention ${mention.id} must use a non-real source URL.`);
  if (LETICIA_DEMO_SCENARIO.authorizedInputChannels.join(",") !== requiredChannels.join(",")) errors.push("Authorized input channels must include facebook, google_maps, audio, and youtube.");
  if (LETICIA_DEMO_SCENARIO.monitors.some((monitor) => monitor.sources.includes("tiktok")) || LETICIA_DEMO_SCENARIO.mentions.some((mention) => mention.source === "tiktok") || LETICIA_DEMO_SCENARIO.overview.sourceHealth.some((source) => source.source === "tiktok")) errors.push("V3 fixtures must not include TikTok.");
  const collectedDocuments = LETICIA_DEMO_SCENARIO.overview.sourceHealth.reduce((total, source) => total + source.collectedDocuments, 0);
  if (LETICIA_DEMO_SCENARIO.overview.collectedDocuments !== collectedDocuments) errors.push("Overview collected documents must equal the source-health total.");
  for (const item of [...LETICIA_DEMO_SCENARIO.signals, ...LETICIA_DEMO_SCENARIO.observations]) for (const evidenceId of item.evidenceIds) if (!mentionIds.has(evidenceId)) errors.push(`${item.id} references unknown evidence ${evidenceId}.`);
  for (const action of LETICIA_DEMO_SCENARIO.actions) if (!caseIds.has(action.caseId)) errors.push(`Action ${action.id} references unknown case ${action.caseId}.`);
  for (const [mentionId, analysis] of Object.entries(LETICIA_DEMO_SCENARIO.slmAnalysesByMentionId)) {
    const mention = LETICIA_DEMO_SCENARIO.mentions.find((item) => item.id === mentionId);
    if (!mention) errors.push(`SLM analysis references unknown mention ${mentionId}.`);
    else if (!mention.text.includes(analysis.evidence)) errors.push(`SLM evidence for ${mentionId} is not contained in its mention text.`);
  }
  return errors;
}
