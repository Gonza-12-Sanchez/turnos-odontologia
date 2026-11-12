import { defineConfig } from '@playwright/test'

const chrome = process.env.PLAYWRIGHT_CHROME_PATH

export default defineConfig({
  testDir: './e2e',
  testIgnore: process.env.E2E_REAL_BACKEND === '1' ? [] : ['**/real-backend.spec.ts'],
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:4173',
    headless: true,
    trace: 'off',
    launchOptions: chrome ? { executablePath: chrome } : undefined,
  },
  webServer: process.env.E2E_USE_EXISTING_FRONTEND === '1' ? undefined : {
    command: 'npm run preview -- --host localhost --port 4173 --strictPort',
    port: 4173,
    reuseExistingServer: !process.env.CI,
  },
})
