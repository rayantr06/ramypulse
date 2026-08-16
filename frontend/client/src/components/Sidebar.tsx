import { Link, useLocation } from "wouter";
import { Plus, Radio, Settings2, X } from "lucide-react";

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

const STAGE_TONES: Record<ProductStage, string> = {
  observer: "text-monitor",
  comprendre: "text-insight",
  decider: "text-action",
  configurer: "text-on-surface-variant",
};

function mobileActiveTone(href: string): string {
  return href === "/alertes"
    ? "border-error/20 bg-error-container text-error"
    : "border-primary/20 bg-primary-container text-primary";
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
      className={`fixed inset-y-0 left-0 z-50 flex w-[19rem] flex-col border-r border-outline-variant/70 bg-surface px-4 pb-4 pt-5 shadow-ambient transition-transform duration-300 lg:w-[5.5rem] lg:translate-x-0 lg:px-3 lg:shadow-none ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
      aria-label="Navigation principale"
    >
      <div className="flex items-center justify-between px-1 lg:justify-center">
        <div className="lg:hidden"><BrandMark /></div>
        <div className="hidden lg:block"><BrandMark compact /></div>
        <button
          className="flex h-10 w-10 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container lg:hidden"
          onClick={onNavigate}
          type="button"
          aria-label="Fermer la navigation"
        >
          <X className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      <div className="mt-6 border-y border-outline-variant py-3.5 lg:hidden">
        <div className="flex items-center gap-3">
          <ProfileMark label={organizationLabel} className="h-9 w-9" />
          <div className="min-w-0 flex-1">
            <p className="truncate font-headline text-sm font-bold text-on-surface">{organizationLabel}</p>
            <p className="mt-0.5 text-[10px] text-on-surface-variant">
              {isOperatorConsole ? "Administration des flux" : "Espace opérationnel"}
            </p>
          </div>
          <Settings2 className="h-4 w-4 text-on-surface-variant" aria-hidden="true" />
        </div>
      </div>

      <Link
        href="/watchlists/new"
        onClick={onNavigate}
        className="mt-4 flex min-h-11 items-center justify-center gap-2 rounded-full bg-primary px-4 py-2.5 font-headline text-xs font-bold text-primary-foreground shadow-pulse-glow transition-transform duration-150 hover:-translate-y-0.5 lg:mx-auto lg:h-11 lg:w-11 lg:min-h-0 lg:px-0"
        data-testid="nav-new-watch"
        aria-label="Créer une surveillance"
        title="Créer une surveillance"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
        <span className="lg:hidden">Créer une surveillance</span>
      </Link>

      <nav className="mt-6 flex-1 space-y-5 overflow-y-auto overflow-x-visible lg:mt-7 lg:space-y-3" aria-label="Fonctions du produit">
        {PRODUCT_NAV_GROUPS.map((group) => (
          <section key={group.label} className="space-y-1.5">
            <div className="mb-1 px-2 lg:hidden">
              <p className="font-headline text-[10px] font-bold text-on-surface">{group.label}</p>
              <p className="text-[9px] text-on-surface-variant">{group.description}</p>
            </div>
            {group.items.map((item) => {
              const active = routeMatches(item.href, location);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  data-testid={item.testId}
                  onClick={onNavigate}
                  className={`group relative flex min-h-11 items-center gap-3 rounded-2xl px-3 py-2.5 transition-colors duration-150 lg:mx-auto lg:h-11 lg:w-11 lg:min-h-0 lg:justify-center lg:px-0 lg:py-0 ${
                    active
                      ? "bg-primary text-primary-foreground shadow-pulse-glow"
                      : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
                  }`}
                  aria-label={item.label}
                  title={item.label}
                >
                  <Icon className={`h-[18px] w-[18px] shrink-0 ${active ? "text-primary-foreground" : STAGE_TONES[item.stage]}`} strokeWidth={active ? 2.2 : 1.8} aria-hidden="true" />
                  <span className="min-w-0 flex-1 truncate font-headline text-[13px] font-semibold lg:hidden">{item.label}</span>
                  {item.href === "/alertes" ? (
                    <span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-white" : "bg-error"}`} aria-label="Alertes actives" />
                  ) : null}
                  <span className="pointer-events-none absolute left-full z-50 ml-3 hidden whitespace-nowrap rounded-xl bg-inverse-surface px-3 py-2 text-xs font-semibold text-inverse-on-surface opacity-0 shadow-ambient transition-opacity group-hover:opacity-100 lg:block">
                    {item.label}
                  </span>
                </Link>
              );
            })}
          </section>
        ))}
      </nav>

      <div className="mt-4 border-t border-outline-variant pt-4">
        <div className="flex items-center gap-3 rounded-2xl px-2 py-1.5 lg:flex-col lg:px-0">
          <div className="relative">
            <ProfileMark label={footerAvatarAlt || organizationLabel} className="h-9 w-9" />
            <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-surface bg-success" />
          </div>
          <div className="min-w-0 flex-1 lg:hidden">
            <p className="text-[10px] font-semibold text-on-surface">Collecte connectée</p>
            <p className="truncate text-[9px] text-on-surface-variant">{footerSubtitle || "Surveillance multi-source active"}</p>
          </div>
          <Radio className="h-4 w-4 text-success lg:hidden" aria-hidden="true" />
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
    <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 items-center rounded-t-[1.35rem] border-x-0 border-b-0 border-t border-outline-variant bg-surface px-2 py-1 shadow-ambient lg:hidden" aria-label="Navigation mobile">
      {items.slice(0, 2).map((item) => {
        const Icon = item.icon;
        const active = routeMatches(item.href, location);
        return (
          <Link key={item.href} href={item.href} className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-xl border text-[9px] font-semibold ${active ? mobileActiveTone(item.href) : "border-transparent text-on-surface-variant"}`}>
            <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
            {item.shortLabel}
          </Link>
        );
      })}
      <Link href="/watchlists/new" className="mx-auto flex h-11 w-11 -translate-y-3 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-pulse-glow" aria-label="Créer une surveillance">
        <Plus className="h-5 w-5" strokeWidth={2.4} aria-hidden="true" />
      </Link>
      {items.slice(2).map((item) => {
        const Icon = item.icon;
        const active = routeMatches(item.href, location);
        return (
          <Link key={item.href} href={item.href} className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-xl border text-[9px] font-semibold ${active ? mobileActiveTone(item.href) : "border-transparent text-on-surface-variant"}`}>
            <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
            {item.shortLabel}
          </Link>
        );
      })}
    </nav>
  );
}
