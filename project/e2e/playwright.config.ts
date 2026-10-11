// E2E 설정. make test-e2e 로만 실행 (make dev 가 떠 있어야 한다). 동결 대상.
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.ts',
  timeout: 60_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'mobile-chrome', use: { ...devices['Pixel 7'] } }],
})
