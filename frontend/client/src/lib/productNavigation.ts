import {
  BellRing,
  ChartNoAxesCombined,
  Compass,
  DatabaseZap,
  LayoutDashboard,
  Lightbulb,
  Megaphone,
  Radar,
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

export const PRODUCT_STAGE_META: Record<
  ProductStage,
  { label: string; description: string; step: string; icon: LucideIcon }
> = {
  observer: {
    label: "Surveiller",
    description: "Collecte et alertes",
    step: "1",
    icon: Radar,
  },
  comprendre: {
    label: "Comprendre",
    description: "Avis et causes",
    step: "2",
    icon: ChartNoAxesCombined,
  },
  decider: {
    label: "Agir",
    description: "Actions à engager",
    step: "3",
    icon: Lightbulb,
  },
  configurer: {
    label: "Configurer",
    description: "Sources et accès",
    step: "",
    icon: DatabaseZap,
  },
};

export const PRODUCT_NAV_GROUPS: ProductNavGroup[] = [
  {
    label: "Surveiller",
    description: "Collecte et alertes",
    stage: "observer",
    step: "1",
    items: [
      {
        href: "/",
        label: "Situation du jour",
        shortLabel: "Accueil",
        description: "Ce qui a changé et ce qui demande votre attention",
        icon: LayoutDashboard,
        stage: "observer",
        testId: "nav-dashboard",
      },
      {
        href: "/watchlists",
        label: "Sujets surveillés",
        shortLabel: "Veille",
        description: "Marques, produits et sujets actuellement suivis",
        icon: Radar,
        stage: "observer",
        testId: "nav-watchlists",
      },
      {
        href: "/alertes",
        label: "Alertes à traiter",
        shortLabel: "Alertes",
        description: "Risques détectés qui nécessitent une réponse",
        icon: BellRing,
        stage: "observer",
        testId: "nav-alertes",
      },
    ],
  },
  {
    label: "Comprendre",
    description: "Avis et causes",
    stage: "comprendre",
    step: "2",
    items: [
      {
        href: "/explorateur",
        label: "Explorer les avis",
        shortLabel: "Explorer",
        description: "Lire les verbatims et rechercher les causes",
        icon: Compass,
        stage: "comprendre",
        testId: "nav-explorateur",
      },
      {
        href: "/campagnes",
        label: "Impact des campagnes",
        shortLabel: "Campagnes",
        description: "Comparer la perception avant, pendant et après",
        icon: Megaphone,
        stage: "comprendre",
        testId: "nav-campagnes",
      },
    ],
  },
  {
    label: "Agir",
    description: "Actions à engager",
    stage: "decider",
    step: "3",
    items: [
      {
        href: "/recommandations",
        label: "Actions recommandées",
        shortLabel: "Actions",
        description: "Décisions proposées, preuves et suivi",
        icon: Lightbulb,
        stage: "decider",
        testId: "nav-recommandations",
      },
    ],
  },
  {
    label: "Configurer",
    description: "Sources et accès",
    stage: "configurer",
    step: "",
    items: [
      {
        href: "/admin-sources",
        label: "Sources de données",
        shortLabel: "Sources",
        description: "Canaux connectés, accès et qualité de collecte",
        icon: DatabaseZap,
        stage: "configurer",
        testId: "nav-admin-sources",
      },
    ],
  },
];

export const PRODUCT_STAGES: Array<{
  id: Exclude<ProductStage, "configurer">;
  label: string;
  icon: LucideIcon;
}> = [
  { id: "observer", label: "Surveiller", icon: Radar },
  { id: "comprendre", label: "Comprendre", icon: ChartNoAxesCombined },
  { id: "decider", label: "Agir", icon: Lightbulb },
];

export const PRODUCT_NAV_ITEMS = PRODUCT_NAV_GROUPS.flatMap((group) => group.items);

export function routeMatches(href: string, location: string): boolean {
  if (href === "/") {
    return location === "/" || location === "";
  }
  return location.startsWith(href);
}

export function getProductRoute(location: string): ProductNavItem {
  return (
    PRODUCT_NAV_ITEMS.find((item) => routeMatches(item.href, location)) ??
    PRODUCT_NAV_ITEMS[0]
  );
}

export function formatTenantLabel(tenantId: string | null): string {
  if (!tenantId) return "Aucun espace";
  if (tenantId === "demo-expo-2026") return "Ramy · Démo Expo";
  if (tenantId === "ramy_client_001") return "Groupe Ramy";
  return tenantId
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
