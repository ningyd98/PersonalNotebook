"""Pairing API — Phase 2B 持久化设备配对"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import PairedDevice

router = APIRouter()


class PairCreateRequest(BaseModel):
    tenant_id: str = "default"
    device_name: Optional[str] = "Unpaired device"
    expires_hours: int = Field(default=24, ge=1, le=168)
    core_base_url: str = "http://HOST:8000"
    metadata_json: Optional[dict] = None


class PairVerifyRequest(BaseModel):
    token: str
    device_name: Optional[str] = None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@router.post("/pair/create")
async def create_pair_token(req: PairCreateRequest, db: AsyncSession = Depends(get_db)):
    """桌面端生成配对 Token。数据库只保存 sha256(token)，明文 token 只返回一次。"""
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    now = _utcnow()
    expires_at = now + timedelta(hours=req.expires_hours)

    device = PairedDevice(
        tenant_id=req.tenant_id, device_name=req.device_name,
        token_hash=token_hash, expires_at=expires_at,
        metadata_json=req.metadata_json,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    pairing_content = {
        "type": "personal_notebook_pairing",
        "core_base_url": req.core_base_url,
        "tenant_id": req.tenant_id,
        "device_id": str(device.id),
        "token": token,
        "expires_at": expires_at.isoformat(),
    }
    return {
        "success": True, "device_id": str(device.id), "tenant_id": req.tenant_id,
        "token": token, "expires_at": expires_at.isoformat(),
        "pairing_content": pairing_content,
        "data": {"device_id": str(device.id), "tenant_id": req.tenant_id,
                 "token": token, "expires_at": expires_at.isoformat(),
                 "pairing_content": pairing_content},
    }


@router.post("/pair/verify")
async def verify_pair_token(req: PairVerifyRequest, db: AsyncSession = Depends(get_db)):
    """移动端验证配对 Token。revoke / expired 后必须 401。不返回 token_hash。"""
    token_hash = _hash_token(req.token)
    now = _utcnow()
    result = await db.execute(select(PairedDevice).where(PairedDevice.token_hash == token_hash))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=401, detail="Invalid pairing token")
    if device.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Pairing token revoked")
    if _as_aware(device.expires_at) < now:
        raise HTTPException(status_code=401, detail="Pairing token expired")
    if req.device_name:
        device.device_name = req.device_name
    device.last_seen_at = now
    await db.commit()
    await db.refresh(device)
    return {"success": True, "verified": True, "tenant_id": device.tenant_id,
            "device_id": str(device.id), "data": {"verified": True,
            "tenant_id": device.tenant_id, "device_id": str(device.id)}}


@router.get("/devices")
async def list_devices(request: Request, db: AsyncSession = Depends(get_db)):
    """列出设备列表 — 仅 localhost。不返回 token_hash。"""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise HTTPException(status_code=403, detail="Device list only available from localhost")
    result = await db.execute(select(PairedDevice).order_by(PairedDevice.created_at.desc()))
    devices = [{"device_id": str(d.id), "tenant_id": d.tenant_id, "device_name": d.device_name,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "expires_at": d.expires_at.isoformat() if d.expires_at else None,
                "revoked_at": d.revoked_at.isoformat() if d.revoked_at else None,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None}
               for d in result.scalars().all()]
    return {"success": True, "devices": devices, "data": {"devices": devices}}


@router.delete("/devices/{device_id}")
async def revoke_device(device_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """按 device_id (UUID) 撤销设备。仅 localhost。"""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise HTTPException(status_code=403, detail="Device revocation only available from localhost")
    try:
        did = uuid.UUID(device_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid device_id UUID")
    result = await db.execute(select(PairedDevice).where(PairedDevice.id == did))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.revoked_at = _utcnow()
    await db.commit()
    return {"success": True, "revoked": True, "device_id": str(device.id)}
