import { defineConfig } from "@playwright/test";

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
    baseURL: "http://127.0.0.1:4173",
    browserName: "chromium",
    channel: "msedge",
    viewport: { width: 1600, height: 1200 },
    colorScheme: "dark",
  },
  webServer: {
    command: "npm run preview -- --host 127.0.0.1 --port 4173",
    port: 4173,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
