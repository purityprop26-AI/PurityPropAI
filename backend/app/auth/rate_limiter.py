"""
Auth v2 — In-Memory Sliding Window Rate Limiter

No Redis required — uses Python dict with automatic eviction.
Thread-safe for asyncio (single-threaded event loop).

Limits enforced:
  • Login attempts     : 5 per 60 seconds per IP
  • OTP attempts       : 5 per 15 minutes per user_id
  • Register           : 3 per 60 seconds per IP
  • Resend OTP         : 2 per 10 minutes per email
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Tuple


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter backed by in-memory deque per key.
    Automatically evicts expired entries on each check.
    """

    def __init__(self):
        # key → deque of timestamps (float, seconds since epoch)
        self._windows: dict[str, deque] = defaultdict(deque)

    def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> Tuple[bool, int]:
        """
        Check if *key* is within rate limit.

        Returns:
            (allowed: bool, retry_after_seconds: int)
        """
        now = time.monotonic()
        cutoff = now - window_seconds
        dq = self._windows[key]

        # Evict expired entries
        while dq and dq[0] < cutoff:
            dq.popleft()

        if len(dq) >= limit:
            # Oldest entry tells us when window resets
            retry_after = int(dq[0] - cutoff) + 1
            return False, retry_after

        dq.append(now)
        return True, 0

    def reset(self, key: str) -> None:
        """Manually clear a key (e.g., on successful login)."""
        self._windows.pop(key, None)

    def purge_expired(self, window_seconds: int = 900) -> int:
        """
        Remove all keys whose windows have fully expired.
        Call periodically to prevent unbounded memory growth.
        Returns number of keys removed.
        """
        now = time.monotonic()
        cutoff = now - window_seconds
        stale = [k for k, dq in self._windows.items() if not dq or dq[-1] < cutoff]
        for k in stale:
            del self._windows[k]
        return len(stale)


# ── Module-level singleton ─────────────────────────────────────────────
_limiter = SlidingWindowRateLimiter()


def check_login_rate(ip: str) -> Tuple[bool, int]:
    """5 attempts / 60 seconds per IP."""
    return _limiter.check(f"login:{ip}", limit=5, window_seconds=60)


def check_otp_rate(user_id: str) -> Tuple[bool, int]:
    """5 attempts / 900 seconds (15 min) per user."""
    return _limiter.check(f"otp:{user_id}", limit=5, window_seconds=900)


def check_register_rate(ip: str) -> Tuple[bool, int]:
    """3 registrations / 60 seconds per IP."""
    return _limiter.check(f"register:{ip}", limit=3, window_seconds=60)


def check_resend_rate(email: str) -> Tuple[bool, int]:
    """2 resends / 600 seconds (10 min) per email."""
    return _limiter.check(f"resend:{email}", limit=2, window_seconds=600)


def check_reset_rate(email: str) -> Tuple[bool, int]:
    """2 password reset requests / 600 seconds (10 min) per email."""
    return _limiter.check(f"reset:{email}", limit=2, window_seconds=600)


def reset_login_rate(ip: str) -> None:
    _limiter.reset(f"login:{ip}")

