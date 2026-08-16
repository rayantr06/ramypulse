import { type FormEvent, type ReactNode, useState } from "react";
import { Bell, Menu, Plus, Search } from "lucide-react";
import { Link, useLocation } from "wouter";

import { MobileNavigation, Sidebar } from "@/components/Sidebar";
import { TenantSwitcher } from "@/components/TenantSwitcher";
import { toast } from "@/hooks/use-toast";
import {
  getProductRoute,
  PRODUCT_NAV_GROUPS,
} from "@/lib/productNavigation";

interface AppShellProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  headerRight?: ReactNode;
  headerSearchPlaceholder?: string;
  onSearch?: (query: string) => void;
  avatarSrc?: string;
  avatarAlt?: string;
  sidebarFooterAvatarSrc?: string;
  sidebarFooterAvatarAlt?: string;
  sidebarFooterSubtitle?: string;
}

export function AppShell({
  children,
  title: _title,
  subtitle: _subtitle,
  headerRight,
  headerSearchPlaceholder = "Rechercher dans cette vue…",
  onSearch,
  avatarSrc: _avatarSrc,
  avatarAlt: _avatarAlt,
  sidebarFooterAvatarSrc,
  sidebarFooterAvatarAlt,
  sidebarFooterSubtitle,
}: AppShellProps) {
  const [location, setLocation] = useLocation();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const route = getProductRoute(location);

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (onSearch) return;
    setLocation("/explorateur");
  }

  function handleSearchChange(value: string) {
    setSearchQuery(value);
    onSearch?.(value);
  }

  return (
    <div className="min-h-screen bg-surface-container-lowest text-on-surface">
      {isSidebarOpen ? (
        <button
          className="fixed inset-0 z-40 bg-surface-container-lowest/80 backdrop-blur-sm lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
          type="button"
          aria-label="Fermer la navigation"
        />
      ) : null}

      <Sidebar
        footerAvatarSrc={sidebarFooterAvatarSrc}
        footerAvatarAlt={sidebarFooterAvatarAlt}
        footerSubtitle={sidebarFooterSubtitle}
        isOpen={isSidebarOpen}
        onNavigate={() => setIsSidebarOpen(false)}
      />

      <main className="flex min-h-screen flex-col pb-24 lg:pl-[5.5rem] lg:pb-0">
        <header className="sticky top-0 z-30 border-b border-outline-variant/70 bg-surface/95 backdrop-blur-xl">
          <div className="flex min-h-[5.25rem] items-center gap-3 px-4 sm:px-6 lg:px-7">
            <button
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-outline-variant bg-surface text-on-surface-variant transition-colors duration-150 hover:border-primary/30 hover:text-primary lg:hidden"
              onClick={() => setIsSidebarOpen(true)}
              type="button"
              aria-label="Ouvrir la navigation"
            >
              <Menu className="h-5 w-5" aria-hidden="true" />
            </button>

            <nav className="hidden shrink-0 items-center gap-1.5 xl:flex" aria-label="Étapes du parcours">
              {PRODUCT_NAV_GROUPS.slice(0, 3).map((group) => {
                const active = route.stage === group.stage;
                return (
                  <Link
                    key={group.stage}
                    href={group.items[0].href}
                    className={`rounded-full px-4 py-2 text-xs font-semibold transition-colors duration-150 ${
                      active
                        ? "bg-primary text-primary-foreground shadow-pulse-glow"
                        : "bg-surface-container text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                    }`}
                  >
                    {group.label}
                  </Link>
                );
              })}
            </nav>

            <form
              className="mx-auto min-w-0 max-w-lg flex-1"
              onSubmit={handleSearchSubmit}
              role="search"
            >
              <label className="relative block">
                <Search
                  className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface-variant"
                  aria-hidden="true"
                />
                <input
                  className="h-11 w-full rounded-full border border-transparent bg-surface-container pl-10 pr-12 text-xs text-on-surface transition-colors duration-150 placeholder:text-on-surface-variant/65 hover:bg-surface-container-high focus:border-primary/25 focus:outline-none focus:ring-2 focus:ring-primary/10"
                  placeholder={onSearch ? headerSearchPlaceholder : "Rechercher un avis, un produit ou un sujet…"}
                  type="search"
                  value={searchQuery}
                  onChange={(event) => handleSearchChange(event.target.value)}
                  data-testid="header-search"
                />
                <span className="absolute right-3 top-1/2 hidden -translate-y-1/2 rounded-md border border-outline-variant bg-surface px-1.5 py-0.5 font-mono text-[9px] text-on-surface-variant sm:block">
                  /
                </span>
              </label>
            </form>

            <div className="flex shrink-0 items-center gap-2">
              <TenantSwitcher />
              {headerRight}
              <Link
                href="/watchlists/new"
                className="hidden h-11 items-center gap-2 rounded-full bg-primary px-5 font-headline text-xs font-bold text-primary-foreground shadow-pulse-glow transition-transform duration-150 hover:-translate-y-0.5 md:flex"
                data-testid="header-new-watch"
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                Créer une surveillance
              </Link>
              <button
                className="relative flex h-11 w-11 items-center justify-center rounded-full border border-outline-variant bg-surface text-on-surface-variant transition-colors duration-150 hover:border-primary/30 hover:text-primary"
                data-testid="btn-notifications"
                onClick={() => toast({ title: "Aucune nouvelle notification" })}
                type="button"
                aria-label="Notifications"
              >
                <Bell className="h-[18px] w-[18px]" aria-hidden="true" />
                <span className="absolute right-2.5 top-2 h-1.5 w-1.5 rounded-full bg-error" />
              </button>
            </div>
          </div>
        </header>

        <div className="flex-1">{children}</div>
      </main>

      <MobileNavigation />
    </div>
  );
}
