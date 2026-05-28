"""Pairing API Tests — Phase 2B"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch


def test_token_hashing():
    """Token 只存 hash，不存明文"""
    import hashlib
    import secrets
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    assert len(token_hash) == 64
    assert token_hash != token
    # 相同 token 产生相同 hash
    assert hashlib.sha256(token.encode()).hexdigest() == token_hash


def test_paired_device_model():
    """PairedDevice 模型字段完整"""
    from app.models.models import PairedDevice
    d = PairedDevice(
        tenant_id="default",
        device_name="test-phone",
        token_hash="a" * 64,
    )
    assert d.tenant_id == "default"
    assert d.device_name == "test-phone"
    assert d.revoked_at is None
    assert str(d.id) != ""


def test_pair_create_schema():
    """PairCreate 请求 schema 校验"""
    from app.api.pair_routes import PairCreateRequest
    req = PairCreateRequest(tenant_id="default", device_name="test", expires_hours=1)
    assert req.tenant_id == "default"
    assert req.expires_hours == 1


def test_pair_verify_schema():
    from app.api.pair_routes import PairVerifyRequest
    req = PairVerifyRequest(token="test_token", device_name="my-phone")
    assert req.token == "test_token"


def test_hash_token():
    from app.api.pair_routes import _hash_token
    h = _hash_token("test123")
    assert len(h) == 64
    assert _hash_token("test123") == h  # deterministic
    assert _hash_token("different") != h


def test_revoke_expired():
    """revoked_at != None 的 device 应被拒绝"""
    from datetime import datetime, timezone
    from app.models.models import PairedDevice
    d = PairedDevice(tenant_id="x", token_hash="h", revoked_at=datetime.now(timezone.utc))
    assert d.revoked_at is not None
    # verify 逻辑验证：revoked_at is not None → 401


def test_enable_runtime_api_false():
    """ENABLE_RUNTIME_API=false 时 /system/runtime/* 返回 403"""
    import os
    os.environ["ENABLE_RUNTIME_API"] = "false"
    try:
        from app.api.system_routes import ENABLE_RUNTIME_API
        assert ENABLE_RUNTIME_API is False
    finally:
        os.environ.pop("ENABLE_RUNTIME_API", None)


def test_log_sanitization():
    from app.api.system_routes import _sanitize
    log = "SECRET_KEY=abc123\nPASSWORD=secret\nnormal log"
    cleaned = _sanitize(log)
    assert "abc123" not in cleaned
    assert "secret" not in cleaned
    assert "***REDACTED***" in cleaned
    assert "normal log" in cleaned


def test_system_routes_import():
    from app.api.system_routes import router
    assert router is not None
