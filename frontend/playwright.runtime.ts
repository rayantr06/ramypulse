type PlaywrightRuntimeEnv = Record<string, string | undefined>;

type PlaywrightRuntimeConfig = {
  baseURL: string;
  webServer?: {
    command: string;
    port: number;
    reuseExistingServer: boolean;
    timeout: number;
  };
};

const DEFAULT_PREVIEW_PORT = 4173;
const DEFAULT_BASE_URL = `http://127.0.0.1:${DEFAULT_PREVIEW_PORT}`;

export function buildPlaywrightRuntimeConfig(
  env: PlaywrightRuntimeEnv = process.env,
): PlaywrightRuntimeConfig {
  const overrideBaseUrl = env.PLAYWRIGHT_BASE_URL?.trim();

  if (overrideBaseUrl) {
    return {
      baseURL: overrideBaseUrl,
    };
  }

  return {
    baseURL: DEFAULT_BASE_URL,
    webServer: {
      command: `npm run preview -- --host 127.0.0.1 --port ${DEFAULT_PREVIEW_PORT}`,
      port: DEFAULT_PREVIEW_PORT,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  };
}
