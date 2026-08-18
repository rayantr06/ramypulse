import { useQuery } from "@tanstack/react-query";

import { isV3LiveMode } from "@/lib/demoMode";
import { useTenantId } from "@/lib/tenantContext";
import { v3Api } from "@/lib/v3Api";
import {
  V3_DEMO_ACTIONS,
  V3_DEMO_CASES,
  V3_DEMO_MENTIONS,
  V3_DEMO_MONITORS,
  V3_DEMO_NOTIFICATIONS,
  V3_DEMO_OBSERVATIONS,
  V3_DEMO_OVERVIEW,
  V3_DEMO_REPORTS,
  V3_DEMO_SIGNALS,
} from "@/lib/v3DemoData";

export function useV3Context() {
  const tenantId = useTenantId();
  return {
    organizationId: tenantId ?? "demo-expo-2026",
    live: isV3LiveMode(),
  };
}

export function useV3Overview() {
  const { organizationId, live } = useV3Context();
  return useQuery({
    queryKey: ["/api/v3/analytics/overview", { clientId: organizationId }],
    queryFn: () => live ? v3Api.overview(organizationId) : Promise.resolve(V3_DEMO_OVERVIEW),
  });
}

export function useV3Signals() {
  const { organizationId, live } = useV3Context();
  return useQuery({
    queryKey: ["/api/v3/signals", { clientId: organizationId }],
    queryFn: () => live ? v3Api.signals(organizationId) : Promise.resolve(V3_DEMO_SIGNALS),
  });
}

export function useV3Mentions() {
  const { organizationId, live } = useV3Context();
  return useQuery({
    queryKey: ["/api/v3/mentions", { clientId: organizationId }],
    queryFn: () => live ? v3Api.mentions(organizationId) : Promise.resolve(V3_DEMO_MENTIONS),
  });
}

export function useV3Observations() {
  const { organizationId, live } = useV3Context();
  return useQuery({
    queryKey: ["/api/v3/observations", { clientId: organizationId }],
    queryFn: () => live ? v3Api.observations(organizationId) : Promise.resolve(V3_DEMO_OBSERVATIONS),
  });
}

export function useV3Monitors() {
  const { organizationId, live } = useV3Context();
  return useQuery({
    queryKey: ["/api/v3/monitors", { clientId: organizationId }],
    queryFn: () => live ? v3Api.monitors(organizationId) : Promise.resolve(V3_DEMO_MONITORS),
  });
}

export function useV3Cases() {
  const { organizationId, live } = useV3Context();
  return useQuery({
    queryKey: ["/api/v3/cases", { clientId: organizationId }],
    queryFn: () => live ? v3Api.cases(organizationId) : Promise.resolve(V3_DEMO_CASES),
  });
}

export function useV3Actions() {
  const { organizationId, live } = useV3Context();
  return useQuery({
    queryKey: ["/api/v3/actions", { clientId: organizationId }],
    queryFn: () => live ? v3Api.actions(organizationId) : Promise.resolve(V3_DEMO_ACTIONS),
  });
}

export function useV3Reports() {
  const { organizationId, live } = useV3Context();
  return useQuery({
    queryKey: ["/api/v3/reports", { clientId: organizationId }],
    queryFn: () => live ? v3Api.reports(organizationId) : Promise.resolve(V3_DEMO_REPORTS),
  });
}

export function useV3Notifications() {
  const { organizationId, live } = useV3Context();
  return useQuery({
    queryKey: ["/api/v3/notifications", { clientId: organizationId }],
    queryFn: () => live ? v3Api.notifications(organizationId) : Promise.resolve(V3_DEMO_NOTIFICATIONS),
  });
}
