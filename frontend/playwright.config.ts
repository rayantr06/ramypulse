import { defineConfig } from "@playwright/test";
import { buildPlaywrightRuntimeConfig } from "./playwright.runtime";

const runtime = buildPlaywrightRuntimeConfig();

export default defineConfig({
  testDir: "./tests",
  timeout: 30_000,
  expect: {
    toHaveScreenshot: {
      animations: "disabled",
      scale: "css",
      maxDiffPixels: 300,
    },
  },
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: runtime.baseURL,
    browserName: "chromium",
    channel: "msedge",
    viewport: { width: 1600, height: 1200 },
    colorScheme: "dark",
  },
  ...(runtime.webServer ? { webServer: runtime.webServer } : {}),
});
