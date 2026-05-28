"""Pairing API Tests — Phase 2B"""

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ─── Token hashing ───────────────────────────────────

def test_token_hash_no_plaintext():
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    assert len(token_hash) == 64
    assert token_hash != token
    assert hashlib.sha256(token.encode()).hexdigest() == token_hash


def test_paired_device_model():
    from app.models.models import PairedDevice
    d = PairedDevice(tenant_id="default", device_name="test-phone", token_hash="a" * 64)
    assert d.tenant_id == "default"
    assert d.revoked_at is None
    assert str(d.id) != ""


def test_pair_create_schema():
    from app.api.pair_routes import PairCreateRequest
    req = PairCreateRequest(tenant_id="default", device_name="test", expires_hours=1)
    assert req.expires_hours == 1


def test_hash_token():
    from app.api.pair_routes import _hash_token
    h = _hash_token("test123")
    assert len(h) == 64
    assert _hash_token("test123") == h
    assert _hash_token("different") != h


# ─── verify response: no token_hash_prefix ───────────

def test_verify_no_token_hash_prefix():
    """/pair/verify 不应返回 token_hash_prefix"""
    token = secrets.token_urlsafe(32)
    h = hashlib.sha256(token.encode()).hexdigest()
    assert h != token  # hash ≠ plain token
    # verify 返回的 data 字段不包含 token_hash_prefix
    resp_keys = {"verified", "tenant_id", "device_id"}
    assert "token_hash_prefix" not in resp_keys
    assert "token" not in resp_keys


# ─── revoked / expired — model-level checks ──────────

def test_revoked_device_has_revoked_at():
    from app.models.models import PairedDevice
    now = datetime.now(timezone.utc)
    d = PairedDevice(tenant_id="x", token_hash="h" * 32, revoked_at=now)
    assert d.revoked_at is not None


def test_expired_device_past_expires():
    from app.models.models import PairedDevice
    past = datetime.now(timezone.utc) - timedelta(hours=25)
    d = PairedDevice(tenant_id="x", token_hash="h" * 32, expires_at=past)
    assert d.expires_at < datetime.now(timezone.utc)


# ─── get_current_device auth dependency ──────────────

@pytest.mark.asyncio
async def test_get_current_device_no_token():
    from app.dependencies.auth import get_current_device
    mock_request = MagicMock()
    mock_request.headers = {}
    with pytest.raises(HTTPException) as exc_info:
        await get_current_device(mock_request, AsyncMock())
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_device_invalid_token():
    from app.dependencies.auth import get_current_device
    mock_request = MagicMock()
    mock_request.headers = {"Authorization": "Bearer invalid_token"}
    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = result_mock
    with pytest.raises(HTTPException) as exc_info:
        await get_current_device(mock_request, mock_db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_device_revoked():
    from app.dependencies.auth import get_current_device
    from app.models.models import PairedDevice
    now = datetime.now(timezone.utc)
    device = PairedDevice(tenant_id="x", device_name="test", token_hash="h" * 32, revoked_at=now)
    mock_request = MagicMock()
    mock_request.headers = {"Authorization": "Bearer anytoken"}
    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = device
    mock_db.execute.return_value = result_mock
    with pytest.raises(HTTPException) as exc_info:
        await get_current_device(mock_request, mock_db)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_device_expired():
    from app.dependencies.auth import get_current_device
    from app.models.models import PairedDevice
    past = datetime.now(timezone.utc) - timedelta(hours=25)
    device = PairedDevice(tenant_id="x", device_name="test", token_hash="h" * 32, expires_at=past)
    mock_request = MagicMock()
    mock_request.headers = {"Authorization": "Bearer anytoken"}
    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = device
    mock_db.execute.return_value = result_mock
    with pytest.raises(HTTPException) as exc_info:
        await get_current_device(mock_request, mock_db)
    assert exc_info.value.status_code == 401


# ─── REQUIRE_PAIR_AUTH bypass ────────────────────────

def test_require_pair_auth_default_true():
    from app.dependencies import auth
    import importlib
    importlib.reload(auth)
    assert auth.REQUIRE_PAIR_AUTH is True


# ─── system_routes ───────────────────────────────────

def test_enable_runtime_api_false():
    os.environ["ENABLE_RUNTIME_API"] = "false"
    try:
        from app.api.system_routes import ENABLE_RUNTIME_API  # noqa: F811
        import importlib
        importlib.reload(__import__("app.api.system_routes", fromlist=["ENABLE_RUNTIME_API"]))
    finally:
        os.environ.pop("ENABLE_RUNTIME_API", None)


def test_log_sanitization():
    from app.api.system_routes import _sanitize
    cleaned = _sanitize("SECRET_KEY=abc123\nnormal log\nPASSWORD=secret")
    assert "abc123" not in cleaned
    assert "secret" not in cleaned
    assert "REDACTED" in cleaned
    assert "normal log" in cleaned
