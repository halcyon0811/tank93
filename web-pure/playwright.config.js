import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.e2e.js',
  fullyParallel: false, // game tests need sequential due to shared server?
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', {open:'never'}], ['list']],
  use: {
    baseURL: 'http://127.0.0.1:8080',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'python3 -m http.server 8080',
    url: 'http://127.0.0.1:8080',
    reuseExistingServer: !process.env.CI,
    cwd: './',
  },
});
