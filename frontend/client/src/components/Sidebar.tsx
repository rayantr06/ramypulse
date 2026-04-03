import { Link, useLocation } from "wouter";

interface NavItem {
  href: string;
  label: string;
  icon: string;
}

const navItems: NavItem[] = [
  { href: "/", label: "Tableau de bord", icon: "dashboard" },
  { href: "/explorateur", label: "Explorateur", icon: "explore" },
  { href: "/campagnes", label: "Campagnes", icon: "campaign" },
  { href: "/watchlists", label: "Watchlists", icon: "visibility" },
  { href: "/alertes", label: "Alertes", icon: "notifications_active" },
  { href: "/recommandations", label: "Recommandations", icon: "auto_awesome" },
  { href: "/admin-sources", label: "Admin Sources", icon: "settings_input_component" },
];

export function Sidebar() {
  const [location] = useLocation();

  return (
    <aside className="h-screen w-64 fixed left-0 top-0 bg-[#121315] flex flex-col py-6 px-4 z-50 border-r border-white/[0.03]">
      {/* Logo */}
      <div className="mb-10 px-2">
        <div className="flex items-center gap-3">
          {/* SVG Logo mark */}
          <svg
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            aria-label="RamyPulse logo"
            className="shrink-0"
          >
            <rect width="28" height="28" rx="4" fill="#ffb693" fillOpacity="0.12" />
            <circle cx="14" cy="14" r="9" stroke="#ffb693" strokeWidth="1.5" strokeDasharray="20 8" />
            <circle cx="14" cy="14" r="4" fill="#ffb693" />
            <path d="M14 8 L14 5" stroke="#ffb693" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M14 20 L14 23" stroke="#ffb693" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M8 14 L5 14" stroke="#ffb693" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M20 14 L23 14" stroke="#ffb693" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <div>
            <h1 className="text-lg font-black text-[#ffb693] tracking-tighter font-headline uppercase leading-none">
              RamyPulse
            </h1>
            <p className="text-[9px] uppercase tracking-widest text-gray-500 font-bold mt-0.5">
              Marketing Intelligence
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? location === "/" || location === ""
              : location.startsWith(item.href);

          return (
            <Link key={item.href} href={item.href}>
              <a
                data-testid={`nav-${item.href.replace("/", "") || "dashboard"}`}
                className={`flex items-center gap-3 px-3 py-2.5 text-sm transition-all duration-200 group ${
                  isActive
                    ? "text-[#ffb693] font-bold border-r-2 border-[#ffb693] bg-[#1b1d20]"
                    : "text-gray-500 hover:text-gray-200 hover:bg-[#1b1d20] font-medium"
                }`}
              >
                <span
                  className="material-symbols-outlined text-xl shrink-0"
                  style={
                    isActive
                      ? { fontVariationSettings: "'FILL' 1" }
                      : { fontVariationSettings: "'FILL' 0" }
                  }
                >
                  {item.icon}
                </span>
                <span className="font-headline tracking-tight">{item.label}</span>
              </a>
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="mt-auto pt-4 border-t border-white/5">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-sm text-gray-400">account_circle</span>
          </div>
          <div className="overflow-hidden flex-1">
            <p className="text-xs font-bold text-on-surface truncate font-headline">Ammar</p>
            <p className="text-[10px] text-on-surface-variant">Brand Manager</p>
          </div>
          <button className="text-gray-500 hover:text-gray-300 transition-colors">
            <span className="material-symbols-outlined text-sm">settings</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
