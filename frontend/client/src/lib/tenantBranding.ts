export interface TenantBranding {
  logoAlt: string;
  logoSrc: string | null;
}

const TENANT_BRANDING: Record<string, TenantBranding> = {
  "demo-expo-2026": {
    logoAlt: "Logo Ramy Food",
    logoSrc: "/brands/ramy-food.png",
  },
  ramy_client_001: {
    logoAlt: "Logo Ramy Food",
    logoSrc: "/brands/ramy-food.png",
  },
};

export function getTenantBranding(
  tenantId: string | null,
  tenantLabel: string,
): TenantBranding {
  if (tenantId && TENANT_BRANDING[tenantId]) {
    return TENANT_BRANDING[tenantId];
  }

  return {
    logoAlt: `Logo ${tenantLabel}`,
    logoSrc: null,
  };
}
