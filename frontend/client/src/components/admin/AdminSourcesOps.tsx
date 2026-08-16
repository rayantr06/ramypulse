import { useEffect, useState } from "react";

import { readAdminSourcesView, type AdminSourcesView } from "@/lib/adminSourcesViewModel";
import { AdminCampaignOpsView } from "./AdminCampaignOpsView";
import { AdminCredentialsView } from "./AdminCredentialsView";
import { AdminSchedulerView } from "./AdminSchedulerView";
import { AdminSourcesView as AdminSourcesViewPanel } from "./AdminSourcesView";

const ADMIN_VIEWS: Array<{ id: AdminSourcesView; label: string }> = [
  { id: "sources", label: "Sources" },
  { id: "credentials", label: "Credentials" },
  { id: "campaign-ops", label: "Campaign Ops" },
  { id: "scheduler", label: "Scheduler" },
];

function currentHashLocation() {
  return typeof window === "undefined"
    ? "#/admin-sources?view=sources"
    : window.location.hash || "#/admin-sources?view=sources";
}

function navigateToAdminView(view: AdminSourcesView) {
  if (typeof window === "undefined") return;

  const oldURL = window.location.href;
  const url = new URL(oldURL);
  url.search = "";
  url.hash = `/admin-sources?view=${view}`;
  const newURL = url.toString();

  history.pushState(history.state, "", newURL);

  const event =
    typeof HashChangeEvent !== "undefined"
      ? new HashChangeEvent("hashchange", { oldURL, newURL })
      : new Event("hashchange");
  dispatchEvent(event);
}

export default function AdminSourcesOps() {
  const [activeView, setActiveView] = useState<AdminSourcesView>(() =>
    readAdminSourcesView(currentHashLocation()),
  );

  useEffect(() => {
    const syncViewFromHash = () => {
      setActiveView(readAdminSourcesView(currentHashLocation()));
    };

    syncViewFromHash();
    if (typeof window === "undefined") return;

    window.addEventListener("hashchange", syncViewFromHash);
    return () => window.removeEventListener("hashchange", syncViewFromHash);
  }, []);

  const activeViewMeta = ADMIN_VIEWS.find((view) => view.id === activeView) ?? ADMIN_VIEWS[0];

  return (
    <div className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8" data-testid="admin-ops-canvas" data-view={activeView}>
      <div className="mb-7 flex flex-col justify-between gap-4 border-b border-outline-variant/55 pb-6 sm:flex-row sm:items-end">
        <div className="signal-rail pl-4">
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
            Opérations & qualité des données
          </p>
          <h1 className="font-headline text-2xl font-extrabold tracking-tight text-on-surface sm:text-3xl">
            Centre de contrôle des sources
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-on-surface-variant">
            Supervisez les connecteurs, les accès et les cycles d’ingestion qui alimentent les analyses.
          </p>
        </div>
        <div className="flex items-center gap-2 self-start rounded-lg border border-outline-variant/60 bg-surface-container px-3 py-2 text-xs text-on-surface-variant sm:self-auto">
          <span className="h-2 w-2 rounded-full bg-success" />
          Vue active <span className="font-semibold text-on-surface">{activeViewMeta.label}</span>
        </div>
      </div>

      <div className="mb-8 flex w-fit max-w-full flex-wrap gap-1 rounded-xl border border-outline-variant/60 bg-surface-container-low p-1.5">
        {ADMIN_VIEWS.map((view) => (
          <button
            key={view.id}
            onClick={() => navigateToAdminView(view.id)}
            data-testid={`admin-view-${view.id}`}
            className={`rounded-lg px-4 py-2 text-xs font-bold transition-colors ${activeView === view.id ? "bg-primary text-on-primary shadow-pulse-glow" : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"}`}
          >
            {view.label}
          </button>
        ))}
      </div>

      {activeView === "sources" ? (
        <AdminSourcesViewPanel />
      ) : activeView === "credentials" ? (
        <AdminCredentialsView />
      ) : activeView === "campaign-ops" ? (
        <AdminCampaignOpsView />
      ) : (
        <AdminSchedulerView />
      )}
    </div>
  );
}
