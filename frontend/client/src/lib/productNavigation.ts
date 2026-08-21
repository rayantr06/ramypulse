import {
  BellRing,
  ChartNoAxesCombined,
  Compass,
  DatabaseZap,
  FileBarChart2,
  LayoutDashboard,
  Lightbulb,
  ListChecks,
  Megaphone,
  Radar,
  QrCode,
  type LucideIcon,
} from "lucide-react";

export type ProductStage = "observer" | "comprendre" | "decider" | "configurer";

export interface ProductNavItem {
  href: string;
  label: string;
  shortLabel: string;
  description: string;
  icon: LucideIcon;
  stage: ProductStage;
  testId: string;
}

export interface ProductNavGroup {
  label: string;
  description: string;
  stage: ProductStage;
  step: string;
  items: ProductNavItem[];
}

export const PRODUCT_STAGE_META: Record<ProductStage, { label: string; description: string; step: string; icon: LucideIcon }> = {
  observer: { label: "Surveiller", description: "Collecte et signaux", step: "1", icon: Radar },
  comprendre: { label: "Comprendre", description: "Observations et preuves", step: "2", icon: ChartNoAxesCombined },
  decider: { label: "Agir", description: "Dossiers et impact", step: "3", icon: Lightbulb },
  configurer: { label: "Configurer", description: "Sources et accès", step: "", icon: DatabaseZap },
};

export const PRODUCT_NAV_GROUPS: ProductNavGroup[] = [
  {
    label: "Surveiller", description: "Collecte et signaux", stage: "observer", step: "1",
    items: [
      { href: "/", label: "Aujourd’hui", shortLabel: "Aujourd’hui", description: "Changements, KPI et urgences", icon: LayoutDashboard, stage: "observer", testId: "nav-dashboard" },
      { href: "/watchlists", label: "Surveillances", shortLabel: "Veille", description: "Marques, produits, campagnes, concurrents et sujets", icon: Radar, stage: "observer", testId: "nav-watchlists" },
      { href: "/listening-points", label: "Points d’écoute", shortLabel: "Écoute", description: "QR directs et retours locaux à analyser", icon: QrCode, stage: "observer", testId: "nav-listening-points" },
      { href: "/signals", label: "Signaux", shortLabel: "Signaux", description: "Changements détectés à vérifier", icon: BellRing, stage: "observer", testId: "nav-alertes" },
    ],
  },
  {
    label: "Comprendre", description: "Observations et preuves", stage: "comprendre", step: "2",
    items: [
      { href: "/explorateur", label: "Explorer", shortLabel: "Explorer", description: "Faits saillants, observations et verbatims", icon: Compass, stage: "comprendre", testId: "nav-explorateur" },
      { href: "/campagnes", label: "Campagnes", shortLabel: "Campagnes", description: "Analyse avant, pendant et après", icon: Megaphone, stage: "comprendre", testId: "nav-campagnes" },
    ],
  },
  {
    label: "Agir", description: "Dossiers et impact", stage: "decider", step: "3",
    items: [
      { href: "/actions", label: "Actions", shortLabel: "Actions", description: "Dossiers, responsables, échéances et impact", icon: ListChecks, stage: "decider", testId: "nav-recommandations" },
      { href: "/reports", label: "Rapports", shortLabel: "Rapports", description: "Briefs et synthèses reliés aux preuves", icon: FileBarChart2, stage: "decider", testId: "nav-reports" },
    ],
  },
  {
    label: "Configurer", description: "Sources et accès", stage: "configurer", step: "",
    items: [
      { href: "/sources", label: "Sources", shortLabel: "Sources", description: "Fraîcheur, coût, quota et erreurs", icon: DatabaseZap, stage: "configurer", testId: "nav-admin-sources" },
    ],
  },
];

export const PRODUCT_STAGES: Array<{ id: Exclude<ProductStage, "configurer">; label: string; icon: LucideIcon }> = [
  { id: "observer", label: "Surveiller", icon: Radar },
  { id: "comprendre", label: "Comprendre", icon: ChartNoAxesCombined },
  { id: "decider", label: "Agir", icon: Lightbulb },
];

export const PRODUCT_NAV_ITEMS = PRODUCT_NAV_GROUPS.flatMap((group) => group.items);

export function routeMatches(href: string, location: string): boolean {
  if (href === "/") return location === "/" || location === "";
  return location.startsWith(href);
}

export function getProductRoute(location: string): ProductNavItem {
  return PRODUCT_NAV_ITEMS.find((item) => routeMatches(item.href, location)) ?? PRODUCT_NAV_ITEMS[0];
}

export function formatTenantLabel(tenantId: string | null): string {
  if (!tenantId) return "Aucun espace";
  if (tenantId === "demo-expo-2026") return "LIDAL · Démo métier";
  if (tenantId === "ramy_client_001") return "Groupe Ramy";
  return tenantId.split(/[-_]/).filter(Boolean).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}
