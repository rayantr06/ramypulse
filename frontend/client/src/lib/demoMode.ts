export function isDemoMode(): boolean {
  const env = (
    import.meta as ImportMeta & {
      env?: Record<string, string | boolean | undefined>;
    }
  ).env;

  return env?.VITE_RAMYPULSE_DEMO_MODE === "true";
}

export function isV3LiveMode(): boolean {
  const env = (
    import.meta as ImportMeta & {
      env?: Record<string, string | boolean | undefined>;
    }
  ).env;
  return env?.VITE_LIDAL_V3_API_ENABLED === "true" && !isDemoMode();
}
