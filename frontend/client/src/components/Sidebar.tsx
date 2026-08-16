import { Link, useLocation } from "wouter";
import { BellRing, Plus, Radio, Settings2 } from "lucide-react";

import { BrandMark } from "@/components/BrandMark";
import { ProfileMark } from "@/components/ProfileMark";
import {
  formatTenantLabel,
  PRODUCT_NAV_GROUPS,
  PRODUCT_NAV_ITEMS,
  routeMatches,
  type ProductStage,
} from "@/lib/productNavigation";
import { useTenantId } from "@/lib/tenantContext";

interface SidebarProps {
  footerAvatarSrc?: string;
  footerAvatarAlt?: string;
  footerSubtitle?: string;
  isOpen?: boolean;
  onNavigate?: () => void;
}

const STAGE_TONES: Record<
  ProductStage,
  { badge: string; active: string; icon: string }
> = {
  observer: {
    badge: "bg-monitor-container text-monitor",
    active: "border-monitor/25 bg-monitor-container text-on-monitor-container",
    icon: "text-monitor",
  },
  comprendre: {
    badge: "bg-insight-container text-insight",
    active: "border-insight/25 bg-insight-container text-on-insight-container",
    icon: "text-insight",
  },
  decider: {
    badge: "bg-action-container text-action",
    active: "border-action/25 bg-action-container text-on-action-container",
    icon: "text-action",
  },
  configurer: {
    badge: "bg-surface-container-high text-on-surface-variant",
    active: "border-outline/25 bg-surface-container-high text-on-surface",
    icon: "text-on-surface-variant",
  },
};

function activeTone(stage: ProductStage, href: string): string {
  if (href === "/alertes") {
    return "border-error/25 bg-error-container text-on-error-container";
  }
  return STAGE_TONES[stage].active;
}

function iconTone(stage: ProductStage, href: string): string {
  return href === "/alertes" ? "text-error" : STAGE_TONES[stage].icon;
}

export function Sidebar({
  footerAvatarSrc: _footerAvatarSrc,
  footerAvatarAlt = "Profil organisation",
  footerSubtitle,
  isOpen = false,
  onNavigate,
}: SidebarProps) {
  const [location] = useLocation();
  const tenantId = useTenantId();
  const isOperatorConsole = location.startsWith("/admin-sources") && !tenantId;
  const organizationLabel = isOperatorConsole ? "Console opérateur" : formatTenantLabel(tenantId);

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-50 flex w-[17.5rem] flex-col border-r border-outline-variant bg-surface px-4 pb-4 pt-5 shadow-ambient transition-transform duration-300 lg:translate-x-0 ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
      aria-label="Navigation principale"
    >
      <div className="flex items-center justify-between px-2">
        <BrandMark />
        <button
          className="flex h-9 w-9 items-center justify-center rounded-xl text-on-surface-variant transition-colors duration-150 hover:bg-surface-container hover:text-on-surface lg:hidden"
          onClick={onNavigate}
          type="button"
          aria-label="Fermer la navigation"
        >
          <span className="material-symbols-outlined text-xl">close</span>
        </button>
      </div>

      <div className="mt-6 border-y border-outline-variant py-3.5">
        <div className="flex items-center gap-3">
          <ProfileMark label={organizationLabel} className="h-9 w-9" />
          <div className="min-w-0 flex-1">
            <p className="truncate font-headline text-xs font-bold text-on-surface">
              {organizationLabel}
            </p>
            <p className="mt-0.5 flex items-center gap-1.5 text-[10px] text-on-surface-variant">
              <span className="h-1.5 w-1.5 rounded-full bg-success" />
              {isOperatorConsole ? "Administration des flux" : "Espace opérationnel"}
            </p>
          </div>
          <Settings2 className="h-4 w-4 text-on-surface-variant/70" aria-hidden="true" />
        </div>
      </div>

      <Link
        href="/watchlists/new"
        onClick={onNavigate}
        className="mt-3 flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 font-headline text-xs font-bold text-primary-foreground shadow-pulse-glow transition-colors duration-150 hover:bg-on-primary-fixed-variant"
        data-testid="nav-new-watch"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
        Créer une surveillance
      </Link>

      <nav className="mt-5 flex-1 space-y-4 overflow-y-auto pr-1">
        {PRODUCT_NAV_GROUPS.map((group) => (
          <section key={group.label} aria-labelledby={`nav-${group.label.toLowerCase().replaceAll(" ", "-")}`}>
            <div className="mb-1.5 flex items-center gap-2.5 px-2">
              <span className={`flex h-6 min-w-6 items-center justify-center rounded-lg text-[10px] font-extrabold ${STAGE_TONES[group.stage].badge}`}>
                {group.step || <Settings2 className="h-3.5 w-3.5" aria-hidden="true" />}
              </span>
              <div className="min-w-0">
                <p
                  id={`nav-${group.label.toLowerCase().replaceAll(" ", "-")}`}
                  className="font-headline text-[10px] font-bold text-on-surface"
                >
                  {group.label}
                </p>
                <p className="truncate text-[9px] text-on-surface-variant">{group.description}</p>
              </div>
            </div>
            <div className="space-y-1">
              {group.items.map((item) => {
                const isActive = routeMatches(item.href, location);
                const Icon = item.icon;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    data-testid={item.testId}
                    className={`group relative flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors duration-150 ${
                      isActive
                        ? activeTone(item.stage, item.href)
                        : "border-transparent text-on-surface-variant hover:border-outline-variant hover:bg-surface-container-low hover:text-on-surface"
                    }`}
                    onClick={onNavigate}
                  >
                    <Icon
                      className={`h-[18px] w-[18px] shrink-0 ${iconTone(item.stage, item.href)}`}
                      strokeWidth={isActive ? 2.2 : 1.8}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1 truncate font-headline text-[12px] font-semibold tracking-tight">
                      {item.label}
                    </span>
                    {item.href === "/alertes" ? (
                      <span
                        className="h-1.5 w-1.5 rounded-full bg-error"
                        aria-label="Alertes actives"
                      />
                    ) : null}
                  </Link>
                );
              })}
            </div>
          </section>
        ))}
      </nav>

      <div className="mt-4 border-t border-outline-variant pt-4">
        <div className="flex items-center gap-3 px-2 py-1.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-success/10 text-success">
            <Radio className="h-4 w-4" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-semibold text-on-surface">Collecte connectée</p>
            <p className="truncate text-[9px] text-on-surface-variant">
              {footerSubtitle || "Surveillance multi-source active"}
            </p>
          </div>
          <ProfileMark label={footerAvatarAlt || organizationLabel} className="h-8 w-8" />
        </div>
      </div>
    </aside>
  );
}

const MOBILE_ITEM_HREFS = ["/", "/watchlists", "/alertes", "/recommandations"];

export function MobileNavigation() {
  const [location] = useLocation();
  const items = PRODUCT_NAV_ITEMS.filter((item) => MOBILE_ITEM_HREFS.includes(item.href));

  return (
    <nav
      className="fixed inset-x-3 bottom-3 z-40 grid grid-cols-5 items-center rounded-2xl border border-outline-variant bg-surface/96 px-2 py-1.5 shadow-ambient backdrop-blur-xl lg:hidden"
      aria-label="Navigation mobile"
    >
      {items.slice(0, 2).map((item) => {
        const Icon = item.icon;
        const active = routeMatches(item.href, location);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-xl text-[9px] font-semibold ${
              active ? activeTone(item.stage, item.href) : "border border-transparent text-on-surface-variant"
            }`}
          >
            <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
            {item.shortLabel}
          </Link>
        );
      })}

      <Link
        href="/watchlists/new"
        className="mx-auto flex h-11 w-11 -translate-y-3 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-pulse-glow"
        aria-label="Créer une surveillance"
      >
        <Plus className="h-5 w-5" strokeWidth={2.4} aria-hidden="true" />
      </Link>

      {items.slice(2).map((item) => {
        const Icon = item.icon;
        const active = routeMatches(item.href, location);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-xl text-[9px] font-semibold ${
              active ? activeTone(item.stage, item.href) : "border border-transparent text-on-surface-variant"
            }`}
          >
            <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
            {item.shortLabel}
          </Link>
        );
      })}
    </nav>
  );
}
