import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, reporter: 'list',
  use: { baseURL: 'http://localhost:4173', headless: true, trace: 'off' },
  webServer: { command: 'npm.cmd run preview -- --host localhost --port 4173 --strictPort', port: 4173, reuseExistingServer: false },
})
