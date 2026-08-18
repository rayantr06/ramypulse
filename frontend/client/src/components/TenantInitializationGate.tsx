import type { ComponentType } from "react";

import { TenantReadinessScreen } from "@/components/TenantReadinessScreen";
import { useTenantReadiness } from "@/lib/tenantReadiness";
import WatchOnboarding from "@/pages/WatchOnboarding";

export function TenantInitializationGate({ component: Component }: { component: ComponentType }) {
  const readiness = useTenantReadiness();

  if (readiness.state === "checking") {
    return <TenantReadinessScreen />;
  }

  if (readiness.state !== "ready") {
    return <WatchOnboarding />;
  }

  return <Component />;
}
