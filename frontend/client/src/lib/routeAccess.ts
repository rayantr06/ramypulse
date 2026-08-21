import type { TenantReadinessState } from "./tenantReadiness";

const PRODUCT_ROUTE_PATHS = new Set([
  "/",
  "/explorateur",
  "/campagnes",
  "/watchlists",
  "/watchlists/new",
  "/signals",
  "/actions",
  "/reports",
  "/listening-points",
  "/listening-points/new",
  "/alertes",
  "/recommandations",
]);

export function isProductRoutePath(pathname: string): boolean {
  return PRODUCT_ROUTE_PATHS.has(pathname);
}

export function shouldGateProductRoute(
  pathname: string,
  readinessState: TenantReadinessState | null,
): boolean {
  return isProductRoutePath(pathname) && readinessState !== "ready" && readinessState !== "checking";
}

export function shouldResetTenantCache(
  previousTenantId: string | null,
  nextTenantId: string | null,
): boolean {
  return previousTenantId !== nextTenantId;
}
