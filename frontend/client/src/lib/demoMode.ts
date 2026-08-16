export function isDemoMode(): boolean {
  const env = (
    import.meta as ImportMeta & {
      env?: Record<string, string | boolean | undefined>;
    }
  ).env;

  return env?.VITE_RAMYPULSE_DEMO_MODE === "true";
}
