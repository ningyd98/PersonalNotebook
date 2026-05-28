"""Paired-Device Auth Dependency — Phase 2B

从 Authorization: Bearer <token> 读取 token，sha256 后查询 PairedDevice。
保护 App 业务接口 (kbs/documents/chat/conversations/jobs)。
"""

import hashlib
import os
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

REQUIRE_PAIR_AUTH = os.getenv("REQUIRE_PAIR_AUTH", "true").lower() not in ("false", "0", "no")
DEV_MODE_AUTH_BYPASS = os.getenv("DEV_MODE_AUTH_BYPASS", "false").lower() in ("true", "1", "yes")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def get_current_device(request: Request, db: AsyncSession = Depends(get_db)):
    """从 Authorization header 提取并验证 paired device token"""
    if not REQUIRE_PAIR_AUTH:
        return {"tenant_id": "default", "device_id": "anonymous"}

    auth = request.headers.get("Authorization", "")
    token = None
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization: Bearer <token>")

    token_hash = _hash_token(token)
    from app.models.models import PairedDevice

    result = await db.execute(
        select(PairedDevice).where(PairedDevice.token_hash == token_hash)
    )
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=401, detail="Invalid device token")
    if device.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Device token revoked")
    now = datetime.now(timezone.utc)
    expires = device.expires_at.replace(tzinfo=timezone.utc) if device.expires_at and device.expires_at.tzinfo is None else (device.expires_at or now)
    if expires < now:
        raise HTTPException(status_code=401, detail="Device token expired")

    device.last_seen_at = now
    await db.commit()

    return {"tenant_id": device.tenant_id, "device_id": str(device.id), "device_name": device.device_name}
