import type { ReactNode } from "react";
import { Link } from "wouter";

import AdminSourcesOps from "@/components/admin/AdminSourcesOps";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { STITCH_AVATARS } from "@/lib/stitchAssets";

function AdminShell({ children }: { children: ReactNode }) {
  return (
    <div
      className="bg-background text-on-surface font-body selection:bg-primary-container selection:text-on-primary-container min-h-screen"
      data-testid="admin-shell-canvas"
    >
      <nav className="bg-[#121315] text-[#ffb693] font-headline tracking-tight font-bold text-lg flex justify-between items-center w-full px-6 py-3 h-16 fixed top-0 z-50">
        <div className="text-xl font-black text-[#ffb693] tracking-tighter">RamyPulse Admin</div>
        <div className="hidden md:flex items-center gap-8">
          <Link href="/">
            <a className="text-gray-400 font-medium hover:text-white transition-colors duration-200 active:scale-95">
              Dashboard
            </a>
          </Link>
          <a className="text-[#ffb693] border-b-2 border-[#ffb693] pb-1 hover:text-white transition-colors duration-200 active:scale-95">
            Ingestion
          </a>
          <a
            className="text-gray-400 font-medium transition-colors duration-200 pointer-events-none opacity-50"
            title="Bientôt disponible"
          >
            Pipelines
          </a>
          <a
            className="text-gray-400 font-medium transition-colors duration-200 pointer-events-none opacity-50"
            title="Bientôt disponible"
          >
            Logs
          </a>
        </div>
        <div className="flex items-center gap-4">
          <img
            alt={STITCH_AVATARS.admin.alt}
            className="w-8 h-8 rounded-full border-2 border-primary/20 object-cover"
            src={STITCH_AVATARS.admin.src}
          />
        </div>
      </nav>

      <div className="flex min-h-screen pt-16">
        <aside className="bg-[#121315] font-body text-sm font-semibold tracking-wide flex flex-col h-[calc(100vh-4rem)] border-r border-white/5 p-4 gap-2 w-64 shrink-0 fixed top-16 left-0">
          <div className="mb-6 px-2">
            <p className="text-xs text-on-surface-variant/50 uppercase tracking-widest font-bold mb-1">
              COMMAND CENTER
            </p>
            <h2 className="text-on-surface text-base">Ramy Juice Intelligence</h2>
          </div>
          <nav className="flex-1 space-y-1">
            <a className="flex items-center gap-3 px-3 py-2 rounded-sm transition-all duration-200 ease-out text-[#ffb693] bg-[#1c1e21]">
              <span className="material-symbols-outlined">database</span>
              <span>Sources</span>
            </a>
            {[
              { label: "Connectors", icon: "alt_route" },
              { label: "Health", icon: "analytics" },
              { label: "Validation", icon: "fact_check" },
              { label: "Archive", icon: "inventory_2" },
            ].map((item) => (
              <a
                key={item.label}
                className="flex items-center gap-3 px-3 py-2 rounded-sm pointer-events-none opacity-50 text-gray-500"
              >
                <span className="material-symbols-outlined">{item.icon}</span>
                <span>{item.label}</span>
                <span className="ml-auto text-[9px] font-bold uppercase tracking-wider bg-surface-container-highest px-1.5 py-0.5 rounded text-on-surface-variant">
                  Bientôt
                </span>
              </a>
            ))}
          </nav>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  disabled
                  className="mt-4 bg-gradient-to-r from-primary to-primary-container text-on-primary-fixed px-4 py-3 rounded-lg flex items-center justify-center gap-2 font-bold shadow-lg transition-all opacity-50 cursor-not-allowed"
                >
                  <span className="material-symbols-outlined">add</span>
                  New Pipeline
                </button>
              </TooltipTrigger>
              <TooltipContent>Bientôt disponible</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </aside>

        <main className="flex-1 overflow-y-auto bg-surface-container-lowest ml-64">
          {children}
        </main>
      </div>

      <div className="fixed top-0 left-0 w-full h-full pointer-events-none z-[-1] opacity-20">
        <div className="absolute top-[10%] left-[20%] w-96 h-96 bg-primary/20 blur-[120px] rounded-full"></div>
        <div className="absolute bottom-[20%] right-[10%] w-[500px] h-[500px] bg-tertiary/10 blur-[160px] rounded-full"></div>
      </div>
    </div>
  );
}

export default function AdminSources() {
  return (
    <AdminShell>
      <AdminSourcesOps />
    </AdminShell>
  );
}
