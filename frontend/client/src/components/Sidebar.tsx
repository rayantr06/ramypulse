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
    <aside className="h-screen w-64 fixed left-0 top-0 bg-[#121315] flex flex-col py-6 px-4 z-50">
      <div className="mb-10">
        <h1 className="text-xl font-black text-[#ffb693] tracking-tighter font-headline">RamyPulse</h1>
        <p className="text-[10px] uppercase tracking-widest text-gray-500 font-bold mt-1">
          Marketing Intelligence
        </p>
      </div>

      <nav className="flex-1 space-y-1">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? location === "/" || location === ""
              : location.startsWith(item.href);

          return (
            <Link key={item.href} href={item.href}>
              <a
                data-testid={`nav-${item.href.replace("/", "") || "dashboard"}`}
                className={`flex items-center gap-3 px-3 py-2 transition-colors duration-200 ${
                  isActive
                    ? "text-[#ffb693] font-bold border-r-2 border-[#ffb693] bg-[#1b1d20]"
                    : "text-gray-500 hover:text-gray-300 hover:bg-[#1b1d20]"
                }`}
              >
                <span className="material-symbols-outlined shrink-0">{item.icon}</span>
                <span className="font-headline text-sm tracking-tight">{item.label}</span>
              </a>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-6 border-t border-gray-800/50">
        <div className="flex items-center gap-3 px-3 py-2">
          <span className="material-symbols-outlined text-gray-400">account_circle</span>
          <div className="overflow-hidden">
            <p className="font-headline text-xs font-bold text-on-surface truncate">
              Ammar, Brand Manager
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
