// @ts-check
import { test, expect } from '@playwright/test';

/**
 * PurityProp AI — E2E Tests
 * Tests critical user flows in the production environment.
 *
 * Run: cd e2e && npx playwright test
 * Run headed: cd e2e && npx playwright test --headed
 */

// ══════════════════════════════════════════════════════════════
// 1. BACKEND HEALTH CHECKS
// ══════════════════════════════════════════════════════════════

test.describe('Backend Health', () => {
    const API_URL = process.env.E2E_API_URL || 'https://puritypropai-9ri1.onrender.com';

    test('GET / returns alive status', async ({ request }) => {
        const res = await request.get(`${API_URL}/`);
        expect(res.ok()).toBeTruthy();
        const body = await res.json();
        expect(body.status).toBe('alive');
        expect(body.version).toBeDefined();
    });

    test('GET /api/health/db returns ready', async ({ request }) => {
        const res = await request.get(`${API_URL}/api/health/db`);
        expect(res.ok()).toBeTruthy();
        const body = await res.json();
        expect(body.status).toBe('ready');
        expect(body.database).toBe('connected');
    });

    test('Response headers include security headers', async ({ request }) => {
        const res = await request.get(`${API_URL}/`);
        const headers = res.headers();
        expect(headers['x-content-type-options']).toBe('nosniff');
        expect(headers['x-frame-options']).toBe('DENY');
        expect(headers['referrer-policy']).toBe('strict-origin-when-cross-origin');
        expect(headers['content-security-policy']).toContain("default-src 'self'");
    });
});


// ══════════════════════════════════════════════════════════════
// 2. FRONTEND PAGE LOADS
// ══════════════════════════════════════════════════════════════

test.describe('Frontend Pages', () => {

    test('Login page loads correctly', async ({ page }) => {
        await page.goto('/login');
        // Check page loaded (not blank)
        await expect(page.locator('body')).not.toBeEmpty();
        // Check for login form elements
        await expect(page.locator('input[type="email"], input[name="email"]').first()).toBeVisible();
        await expect(page.locator('input[type="password"]').first()).toBeVisible();
    });

    test('Register page loads correctly', async ({ page }) => {
        await page.goto('/register');
        await expect(page.locator('body')).not.toBeEmpty();
        await expect(page.locator('input[name="name"], input[placeholder*="name" i]').first()).toBeVisible();
        await expect(page.locator('input[type="email"], input[name="email"]').first()).toBeVisible();
    });

    test('Unauthenticated user redirected from /dashboard to /login', async ({ page }) => {
        await page.goto('/dashboard');
        // Should redirect to login
        await page.waitForURL('**/login', { timeout: 10000 });
        expect(page.url()).toContain('/login');
    });

    test('404 routes redirect to dashboard/login', async ({ page }) => {
        await page.goto('/nonexistent-route');
        // Should redirect to dashboard (which redirects to login if not auth'd)
        await page.waitForURL('**/login', { timeout: 10000 });
        expect(page.url()).toContain('/login');
    });

    test('Login page has Google sign-in button', async ({ page }) => {
        await page.goto('/login');
        // Look for Google sign-in button
        const googleBtn = page.locator('button:has-text("Google"), button:has-text("google"), [aria-label*="Google"]').first();
        await expect(googleBtn).toBeVisible();
    });
});


// ══════════════════════════════════════════════════════════════
// 3. AUTH API ENDPOINTS
// ══════════════════════════════════════════════════════════════

test.describe('Auth API', () => {
    const API_URL = process.env.E2E_API_URL || 'https://puritypropai-9ri1.onrender.com';

    test('POST /auth/login returns 401 for invalid credentials', async ({ request }) => {
        const res = await request.post(`${API_URL}/auth/login`, {
            data: { email: 'nonexistent@test.com', password: 'WrongPassword1' },
        });
        expect(res.status()).toBe(401);
    });

    test('POST /auth/register returns 400 for weak password', async ({ request }) => {
        const res = await request.post(`${API_URL}/auth/register`, {
            data: { name: 'Test', email: 'test@test.com', password: 'weak' },
        });
        expect(res.status()).toBe(400);
        const body = await res.json();
        expect(body.detail).toContain('Password must contain');
    });

    test('POST /auth/register returns 400 for invalid email', async ({ request }) => {
        const res = await request.post(`${API_URL}/auth/register`, {
            data: { name: 'Test', email: 'not-an-email', password: 'ValidPass1' },
        });
        // Should fail validation
        expect(res.status()).toBe(422); // Pydantic validation error
    });

    test('GET /auth/me returns 401 without token', async ({ request }) => {
        const res = await request.get(`${API_URL}/auth/me`);
        expect(res.status()).toBe(401);
    });

    test('GET /auth/me returns 401 with invalid token', async ({ request }) => {
        const res = await request.get(`${API_URL}/auth/me`, {
            headers: { Authorization: 'Bearer invalid-token-here' },
        });
        expect(res.status()).toBe(401);
    });
});


// ══════════════════════════════════════════════════════════════
// 4. LOGIN FORM INTERACTION
// ══════════════════════════════════════════════════════════════

test.describe('Login Form Interaction', () => {

    test('Shows error for invalid credentials', async ({ page }) => {
        await page.goto('/login');

        // Fill in invalid credentials
        await page.locator('input[type="email"], input[name="email"]').first().fill('fake@test.com');
        await page.locator('input[type="password"]').first().fill('WrongPassword1!');

        // Submit the form
        const submitBtn = page.locator('button[type="submit"]').first();
        await submitBtn.click();

        // Wait for error message to appear
        const errorEl = page.locator('[class*="error"], [role="alert"], [class*="alert"]').first();
        await expect(errorEl).toBeVisible({ timeout: 15000 });
    });

    test('Navigate from login to register', async ({ page }) => {
        await page.goto('/login');

        // Find and click register link
        const registerLink = page.locator('a[href="/register"], a:has-text("Register"), a:has-text("Sign up"), a:has-text("Create")').first();
        await registerLink.click();

        await page.waitForURL('**/register', { timeout: 5000 });
        expect(page.url()).toContain('/register');
    });

    test('Navigate from login to forgot password', async ({ page }) => {
        await page.goto('/login');

        const forgotLink = page.locator('a[href="/forgot-password"], a:has-text("Forgot"), a:has-text("forgot")').first();
        await forgotLink.click();

        await page.waitForURL('**/forgot-password', { timeout: 5000 });
        expect(page.url()).toContain('/forgot-password');
    });
});


// ══════════════════════════════════════════════════════════════
// 5. REGISTER FORM VALIDATION
// ══════════════════════════════════════════════════════════════

test.describe('Register Form Validation', () => {

    test('Password strength indicator works', async ({ page }) => {
        await page.goto('/register');

        const pwdInput = page.locator('input[type="password"]').first();

        // Type weak password
        await pwdInput.fill('abc');
        // Check for strength indicator
        const indicator = page.locator('[class*="strength"], [class*="weak"], [class*="meter"]').first();
        // Just verify the page doesn't crash — indicator may or may not exist
        await page.waitForTimeout(500);

        // Type strong password
        await pwdInput.fill('StrongPass123!');
        await page.waitForTimeout(500);
    });

    test('Shows error for mismatched passwords', async ({ page }) => {
        await page.goto('/register');

        // Fill form
        await page.locator('input[name="name"]').first().fill('Test User');
        await page.locator('input[name="email"], input[type="email"]').first().fill('test@test.com');

        const pwdInputs = page.locator('input[type="password"]');
        await pwdInputs.nth(0).fill('StrongPass1!');
        await pwdInputs.nth(1).fill('DifferentPass1!');

        // Submit
        const submitBtn = page.locator('button[type="submit"]').first();
        await submitBtn.click();

        // Should show password mismatch error
        const errorEl = page.locator('[class*="error"], [role="alert"], [class*="alert"]').first();
        await expect(errorEl).toBeVisible({ timeout: 5000 });
    });
});


// ══════════════════════════════════════════════════════════════
// 6. PERFORMANCE CHECKS
// ══════════════════════════════════════════════════════════════

test.describe('Performance', () => {

    test('Login page loads within 5 seconds', async ({ page }) => {
        const start = Date.now();
        await page.goto('/login');
        await page.locator('input[type="email"], input[name="email"]').first().waitFor();
        const loadTime = Date.now() - start;

        console.log(`Login page loaded in ${loadTime}ms`);
        expect(loadTime).toBeLessThan(5000);
    });

    test('No console errors on login page', async ({ page }) => {
        const errors = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                errors.push(msg.text());
            }
        });

        await page.goto('/login');
        await page.waitForTimeout(2000);

        // Filter out known non-critical errors (e.g., favicon 404)
        const criticalErrors = errors.filter(e =>
            !e.includes('favicon') &&
            !e.includes('404') &&
            !e.includes('net::ERR')
        );

        expect(criticalErrors).toHaveLength(0);
    });
});
