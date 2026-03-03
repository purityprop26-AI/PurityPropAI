/**
 * Keep-Alive Utility — Prevents Render free-tier cold starts
 * 
 * Pings the backend /health endpoint every 13 minutes while the app is active.
 * Render free tier sleeps after 15 min of inactivity, so 13 min keeps it alive.
 * 
 * Also provides a warmup function for pre-login server wake-up.
 */

const API_URL = (import.meta.env.VITE_API_URL || '').trim();
const KEEP_ALIVE_INTERVAL = 13 * 60 * 1000; // 13 minutes

let intervalId = null;

/**
 * Ping the backend health endpoint. Returns true if server is awake.
 */
export async function pingServer() {
    try {
        const res = await fetch(`${API_URL}/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(10000), // 10s timeout
        });
        return res.ok;
    } catch {
        return false;
    }
}

/**
 * Pre-warm the backend before login attempt.
 * Tries up to 3 pings with 2s gaps to wake the server.
 * Returns true once server responds, false after all retries fail.
 */
export async function warmupServer() {
    for (let i = 0; i < 3; i++) {
        const alive = await pingServer();
        if (alive) return true;
        // Wait 2s before retry
        await new Promise(r => setTimeout(r, 2000));
    }
    return false;
}

/**
 * Start keep-alive interval. Call once when app mounts.
 * Silently pings /health every 13 minutes.
 */
export function startKeepAlive() {
    if (intervalId) return; // Already running

    // Initial ping
    pingServer();

    // Schedule recurring pings
    intervalId = setInterval(() => {
        pingServer();
    }, KEEP_ALIVE_INTERVAL);
}

/**
 * Stop keep-alive interval. Call on app unmount.
 */
export function stopKeepAlive() {
    if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
    }
}
