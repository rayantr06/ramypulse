import { ReactNode } from "react";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
  headerRight?: ReactNode;
  headerSearchPlaceholder?: string;
  onSearch?: (query: string) => void;
}

export function AppShell({
  children,
  title,
  subtitle,
  headerRight,
  headerSearchPlaceholder = "Rechercher...",
  onSearch,
}: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-surface-container-lowest">
      <Sidebar />
      <main className="pl-64 flex-1 flex flex-col min-h-screen">
        {/* Top Nav */}
        <header className="sticky top-0 z-40 bg-[#121315]/80 backdrop-blur-xl h-16 flex items-center justify-between pl-8 pr-8 shadow-[0px_24px_24px_0px_rgba(255,255,255,0.06)] border-b border-white/[0.03]">
          <div className="flex items-center gap-4 flex-1">
            {onSearch && (
              <div className="relative w-full max-w-md">
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-lg">
                  search
                </span>
                <input
                  className="w-full bg-surface-container-highest border-none text-sm px-10 py-2 rounded-sm focus:ring-1 focus:ring-primary/40 placeholder:text-gray-500 focus:outline-none transition-all"
                  placeholder={headerSearchPlaceholder}
                  type="text"
                  onChange={(e) => onSearch(e.target.value)}
                  data-testid="header-search"
                />
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            {headerRight}
            <button
              className="relative text-gray-400 hover:bg-surface-container p-2 rounded-sm transition-all duration-200"
              data-testid="btn-notifications"
            >
              <span className="material-symbols-outlined">notifications</span>
              <span className="absolute top-2 right-2 w-2 h-2 bg-primary rounded-full"></span>
            </button>
            <button className="text-gray-400 hover:bg-surface-container p-2 rounded-sm transition-all duration-200">
              <span className="material-symbols-outlined">sensors</span>
            </button>
            <div className="h-8 w-8 rounded-full bg-surface-container-high flex items-center justify-center overflow-hidden border border-outline-variant/20 ml-1">
              <span className="material-symbols-outlined text-sm text-gray-400">person</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1">
          {children}
        </div>

        {/* Footer */}
        <footer className="px-8 py-4 flex justify-between items-center text-[10px] text-gray-600 font-bold uppercase tracking-widest border-t border-white/[0.03]">
          <div className="flex gap-4">
            <span>API Status: Normal</span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span>
              Temps Réel
            </span>
          </div>
          <div>© 2024 RamyPulse Intelligence Unit</div>
        </footer>
      </main>
    </div>
  );
}
