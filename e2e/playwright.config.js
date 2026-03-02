// @ts-check
import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'https://purity-prop-ai.vercel.app';
const API_URL = process.env.E2E_API_URL || 'https://puritypropai-9ri1.onrender.com';

export default defineConfig({
    testDir: './tests',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: process.env.CI ? 'github' : 'html',
    timeout: 60_000, // 60s per test (Render cold start can take 30s+)

    use: {
        baseURL: BASE_URL,
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
    },

    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],

    // Store API URL for use in tests
    metadata: {
        apiUrl: API_URL,
    },
});
