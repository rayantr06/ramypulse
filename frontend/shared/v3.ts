/**
 * Contrat additif LIDAL Pulse V3.
 *
 * Ce fichier est volontairement separe de schema.ts : la V3 peut evoluer sans
 * casser les routes historiques utilisees par la version de demonstration.
 */

export type V3EntityType =
  | "brand"
  | "organization"
  | "product"
  | "campaign"
  | "competitor"
  | "subject";

export type V3SourcePlatform = "facebook" | "tiktok" | "youtube" | "google_maps";
export type V3SignalSeverity = "critical" | "high" | "medium" | "low";
export type V3SignalStatus = "new" | "investigating" | "confirmed" | "dismissed" | "converted";
export type V3CaseStatus = "open" | "in_progress" | "blocked" | "resolved" | "closed";
export type V3AnnotationStatus = "valid" | "pending" | "failed" | "overridden";
export type V3Sentiment = "positif" | "negatif" | "neutre" | "mixte";

export interface V3Monitor {
  id: string;
  organizationId: string;
  name: string;
  objective: "customer_experience" | "reputation" | "campaign" | "competition" | "issue";
  targetType: V3EntityType;
  targetName: string;
  aliases: string[];
  exclusions: string[];
  languages: string[];
  territories: string[];
  sources: V3SourcePlatform[];
  competitors: string[];
  frequencyMinutes: number;
  maxMonthlyDocuments: number;
  maxMonthlyCostDzd: number;
  active: boolean;
  lastCollectedAt: string | null;
  coverageNote: string | null;
}

export interface V3MentionEvidence {
  id: string;
  text: string;
  source: V3SourcePlatform;
  sourceUrl: string | null;
  publishedAt: string;
  language: string;
  territory: string | null;
  sentiment: V3Sentiment;
  aspects: string[];
  annotationStatus: V3AnnotationStatus;
}

export interface V3Observation {
  id: string;
  monitorId: string;
  title: string;
  summary: string;
  mentionCount: number;
  sentiment: V3Sentiment;
  aspects: string[];
  firstSeenAt: string;
  lastSeenAt: string;
  evidenceIds: string[];
}

export interface V3Signal {
  id: string;
  monitorId: string;
  title: string;
  summary: string;
  severity: V3SignalSeverity;
  status: V3SignalStatus;
  signalType: "volume_spike" | "negative_shift" | "recurrence" | "safety" | "fraud" | "compliance" | "competitor_move";
  detectedAt: string;
  mentionCount: number;
  velocityPercent: number | null;
  confidence: number;
  territory: string | null;
  observationIds: string[];
  evidenceIds: string[];
  explanation: string;
  priorityScore: number;
  priorityFactors: Array<{ label: string; value: number; weight: number }>;
}

export interface V3Case {
  id: string;
  signalId: string;
  title: string;
  status: V3CaseStatus;
  priority: V3SignalSeverity;
  ownerId: string | null;
  ownerName: string | null;
  dueAt: string | null;
  expectedOutcome: string | null;
  openedAt: string;
  updatedAt: string;
  actionCount: number;
  overdueActionCount: number;
}

export interface V3ActionItem {
  id: string;
  caseId: string;
  title: string;
  description: string;
  status: V3CaseStatus;
  ownerId: string | null;
  ownerName: string | null;
  dueAt: string | null;
  expectedImpact: string | null;
  metricId: string | null;
  baselineValue: number | null;
  resultValue: number | null;
}

export interface V3SentimentDistribution {
  positif: number;
  negatif: number;
  neutre: number;
  mixte: number;
}

export interface V3AnalyticsOverview {
  period: { start: string; end: string; comparisonStart: string; comparisonEnd: string };
  qualifiedMentions: number;
  collectedDocuments: number;
  validAnnotations: number;
  analyticalCoveragePercent: number;
  netSentiment: number | null;
  netSentimentDelta: number | null;
  insufficientSample: boolean;
  distribution: V3SentimentDistribution;
  negativeRatePercent: number;
  openSignalsBySeverity: Record<V3SignalSeverity, number>;
  medianTimeToOwnershipHours: number | null;
  overdueActions: number;
  topDrivers: Array<{ aspect: string; deltaPoints: number; mentionCount: number }>;
  sourceHealth: Array<{
    source: V3SourcePlatform;
    status: "healthy" | "degraded" | "unavailable";
    successRatePercent: number;
    freshnessMinutes: number | null;
    collectedDocuments: number;
    analyticalCoveragePercent: number;
  }>;
}

export interface V3Report {
  id: string;
  title: string;
  reportType: "daily" | "weekly" | "crisis" | "reputation" | "territory" | "product";
  periodStart: string;
  periodEnd: string;
  status: "draft" | "ready" | "failed";
  generatedAt: string | null;
  downloadUrl: string | null;
  evidenceCount: number;
}

export interface V3AgentDraft {
  id: string;
  draftType: "explanation" | "comparison" | "case_summary" | "action_plan" | "report" | "response";
  title: string;
  content: string;
  citations: Array<{ kind: "metric" | "observation" | "mention"; id: string; label: string }>;
  generatedAt: string;
  model: string;
  latencyMs: number;
  estimatedCostUsd: number | null;
}

export interface V3Notification {
  id: string;
  title: string;
  body: string;
  kind: "signal" | "assignment" | "deadline" | "report" | "source";
  read: boolean;
  createdAt: string;
  href: string | null;
}
