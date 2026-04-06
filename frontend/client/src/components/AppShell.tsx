import { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { demoDisabledProps } from "@/lib/demoMode";
import { STITCH_AVATARS } from "@/lib/stitchAssets";
import { demoDisabledProps } from "@/lib/demoMode";

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
  headerRight,
  headerSearchPlaceholder = "Rechercher...",
  onSearch,
  avatarSrc = STITCH_AVATARS.dashboard.src,
  avatarAlt = STITCH_AVATARS.dashboard.alt,
  sidebarFooterAvatarSrc,
  sidebarFooterAvatarAlt,
  sidebarFooterSubtitle,
}: AppShellProps) {
  const hasSearch = Boolean(onSearch);

  return (
    <div className="bg-surface-container-lowest text-on-surface min-h-screen">
      <Sidebar
        footerAvatarSrc={sidebarFooterAvatarSrc}
        footerAvatarAlt={sidebarFooterAvatarAlt}
        footerSubtitle={sidebarFooterSubtitle}
      />
      <main className="pl-64 min-h-screen flex flex-col">
        <header
          className={`sticky top-0 z-40 bg-[#121315]/80 backdrop-blur-xl h-16 flex items-center pl-8 pr-8 shadow-[0px_24px_24px_0px_rgba(255,255,255,0.06)] ${
            hasSearch ? "justify-between" : "justify-end"
          }`}
        >
          {hasSearch ? (
            <div className="flex items-center flex-1 max-w-xl">
              <div className="relative w-full">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant/50 text-xl">
                  search
                </span>
                <input
                  className="w-full bg-surface-container-highest border-none rounded-lg pl-10 pr-4 py-2 text-sm focus:ring-1 focus:ring-primary/40 transition-all placeholder:text-on-surface-variant/40 focus:outline-none"
                  placeholder={headerSearchPlaceholder}
                  type="text"
                  onChange={(event) => onSearch?.(event.target.value)}
                  data-testid="header-search"
                />
              </div>
            </div>
          ) : null}

          <div className="flex items-center gap-6">
            {headerRight}
            {hasSearch ? (
              <>
                <div className="flex items-center gap-4 text-on-surface-variant">
                  <button
                    className="material-symbols-outlined hover:text-white transition-colors"
                    {...demoDisabledProps("language")}
                  >
                    language
                  </button>
                  <button
                    className="material-symbols-outlined hover:text-white transition-colors"
                    {...demoDisabledProps("grid_view")}
                  >
                    grid_view
                  </button>
                  <div className="relative">
                    <button
                      className="material-symbols-outlined hover:text-white transition-colors"
                      data-testid="btn-notifications"
                      {...demoDisabledProps("notifications")}
                    >
                      notifications
                    </button>
                    <span className="absolute -top-1 -right-1 w-2 h-2 bg-primary rounded-full"></span>
                  </div>
                </div>
                <div className="h-8 w-px bg-white/10"></div>
              </>
            ) : (
              <>
                <button
                  className="relative text-gray-400 hover:bg-[#1b1d20] p-2 rounded-sm transition-all duration-200"
                  data-testid="btn-notifications"
                  {...demoDisabledProps("notifications")}
                >
                  <span className="material-symbols-outlined">notifications</span>
                  <span className="absolute top-2 right-2 w-2 h-2 bg-primary rounded-full"></span>
                </button>
                <button
                  className="text-gray-400 hover:bg-[#1b1d20] p-2 rounded-sm transition-all duration-200"
                  {...demoDisabledProps("sensors")}
                >
                  <span className="material-symbols-outlined">sensors</span>
                </button>
              </>
            )}
            <div className="h-8 w-8 rounded-full bg-surface-container-high flex items-center justify-center overflow-hidden border border-outline-variant/20">
              <img
                alt={avatarAlt}
                className="w-full h-full object-cover"
                src={avatarSrc}
              />
            </div>
          </div>
        </header>

        <div className="flex-1">{children}</div>
      </main>
    </div>
  );
}
