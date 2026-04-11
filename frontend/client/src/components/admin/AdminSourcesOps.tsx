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
    <div className="p-8" data-testid="admin-ops-canvas" data-view={activeView}>
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <p className="text-on-surface-variant font-bold tracking-[0.15em] mb-1 uppercase text-[10px]">
            COMMAND CENTER
          </p>
          <h1 className="text-3xl font-headline font-extrabold tracking-tight">
            Ramy Intelligence Dashboard
          </h1>
        </div>
        <div className="text-sm text-on-surface-variant">
          Vue active: <span className="text-on-surface font-semibold">{activeViewMeta.label}</span>
        </div>
      </div>

      <div className="mb-8 flex flex-wrap gap-3">
        {ADMIN_VIEWS.map((view) => (
          <button
            key={view.id}
            onClick={() => navigateToAdminView(view.id)}
            data-testid={`admin-view-${view.id}`}
            className={`px-4 py-2 rounded-full text-sm font-bold transition-all ${activeView === view.id ? "bg-primary text-on-primary shadow-lg shadow-primary/15" : "bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high"}`}
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
