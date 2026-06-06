import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration.
 *
 * The `webServer` block starts:
 *   1. The FastAPI backend on port 8000.
 *   2. The Vite dev server (which proxies /api → backend) on port 5173.
 *
 * Tests hit http://localhost:5173 so Vite serves the React app and
 * forwards API calls to the running backend.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    viewport: { width: 1280, height: 800 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: '/home/s/kill-prop/.venv/bin/uvicorn backend.main:app --port 8000',
      port: 8000,
      timeout: 30_000,
      reuseExistingServer: true,
    },
    {
      command: 'npm run dev --prefix frontend',
      port: 5173,
      timeout: 30_000,
      reuseExistingServer: true,
    },
  ],
});
