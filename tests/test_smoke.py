"""
PurityProp AI — Smoke Tests (Production Validation)

These tests validate critical system paths without external dependencies.
Run: pytest tests/test_smoke.py -v
"""
import pytest
import sys
import os

# Ensure the backend module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


class TestSecurityPrimitives:
    """Verify auth security module works correctly."""

    def test_password_hash_and_verify(self):
        from app.auth.security import hash_password, verify_password
        hashed = hash_password("TestPass123!")
        assert verify_password("TestPass123!", hashed) is True
        assert verify_password("WrongPassword", hashed) is False

    def test_password_truncation_72_bytes(self):
        """Passwords > 72 bytes should still work (truncated safely)."""
        from app.auth.security import hash_password, verify_password
        long_pw = "A" * 100 + "1Xx"  # 103 chars, > 72 bytes
        hashed = hash_password(long_pw)
        assert verify_password(long_pw, hashed) is True

    def test_jwt_create_and_decode(self):
        from app.auth.security import create_access_token, decode_access_token
        token, expires_in = create_access_token(
            user_id="test-123",
            email="test@example.com",
            provider="email",
            is_verified=True,
        )
        assert isinstance(token, str)
        assert expires_in > 0

        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "test-123"
        assert payload["email"] == "test@example.com"
        assert payload["is_verified"] is True
        assert "jti" in payload  # Token has unique ID for blocklist

    def test_jwt_invalid_token(self):
        from app.auth.security import decode_access_token
        assert decode_access_token("invalid.token.here") is None
        assert decode_access_token("") is None

    def test_otp_generate_and_verify(self):
        from app.auth.security import generate_otp, verify_otp
        otp_plain, otp_hash = generate_otp()
        assert len(otp_plain) == 6
        assert otp_plain.isdigit()
        assert verify_otp(otp_plain, otp_hash) is True
        assert verify_otp("000000", otp_hash) is False

    def test_bearer_extraction(self):
        from app.auth.security import extract_bearer
        assert extract_bearer("Bearer abc123") == "abc123"
        assert extract_bearer("Bearer ") is None
        assert extract_bearer("Basic abc123") is None
        assert extract_bearer("") is None
        assert extract_bearer(None) is None


class TestTokenBlocklist:
    """Verify in-memory token blocklist works."""

    def test_block_and_check(self):
        import time
        from main import TokenBlocklist
        bl = TokenBlocklist()
        bl.block("jti-1", time.time() + 3600)  # Expires in 1 hour
        assert bl.is_blocked("jti-1") is True
        assert bl.is_blocked("jti-2") is False

    def test_expired_tokens_cleaned(self):
        import time
        from main import TokenBlocklist
        bl = TokenBlocklist()
        bl.block("jti-old", time.time() - 10)  # Already expired
        assert bl.is_blocked("jti-old") is False  # Cleaned up on check

    def test_max_size_eviction(self):
        import time
        from main import TokenBlocklist
        bl = TokenBlocklist()
        bl.MAX_SIZE = 5  # Set small max for test
        for i in range(10):
            bl.block(f"jti-{i}", time.time() + 3600)
        # Only last 5 should remain (+ 1 evicted per insert after max)
        assert bl.is_blocked("jti-9") is True
        assert bl.is_blocked("jti-0") is False


class TestConfigValidation:
    """Verify settings load correctly."""

    def test_settings_loaded(self):
        from app.config import settings
        assert settings.app_name is not None
        assert settings.database_url is not None
        assert settings.groq_api_key is not None

    def test_cors_origins_has_production(self):
        from app.config import settings
        origins = settings.get_cors_origins()
        assert "https://purityprop.com" in origins

    def test_cors_origins_has_localhost(self):
        from app.config import settings
        origins = settings.get_cors_origins()
        assert "http://localhost:5173" in origins


class TestSchemaValidation:
    """Verify Pydantic schemas enforce constraints."""

    def test_register_schema_valid(self):
        from app.auth.schemas import RegisterRequest
        req = RegisterRequest(name="Test User", email="test@test.com", password="ValidPass1")
        assert req.name == "Test User"

    def test_register_schema_weak_password(self):
        from app.auth.schemas import RegisterRequest
        with pytest.raises(Exception):
            RegisterRequest(name="Test", email="test@test.com", password="weak")

    def test_register_schema_no_uppercase(self):
        from app.auth.schemas import RegisterRequest
        with pytest.raises(Exception):
            RegisterRequest(name="Test", email="test@test.com", password="nouppercase1")

    def test_otp_schema_valid(self):
        from app.auth.schemas import VerifyEmailRequest
        req = VerifyEmailRequest(email="test@test.com", otp="123456")
        assert req.otp == "123456"

    def test_otp_schema_invalid(self):
        from app.auth.schemas import VerifyEmailRequest
        with pytest.raises(Exception):
            VerifyEmailRequest(email="test@test.com", otp="abc")
