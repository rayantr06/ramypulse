const PRODUCT_ROUTE_PATHS = new Set([
  "/",
  "/explorateur",
  "/campagnes",
  "/watchlists",
  "/alertes",
  "/recommandations",
]);

export function isProductRoutePath(pathname: string): boolean {
  return PRODUCT_ROUTE_PATHS.has(pathname);
}

export function shouldGateProductRoute(pathname: string, tenantId: string | null): boolean {
  return isProductRoutePath(pathname) && !tenantId;
}

export function shouldResetTenantCache(
  previousTenantId: string | null,
  nextTenantId: string | null,
): boolean {
  return previousTenantId !== nextTenantId;
}
