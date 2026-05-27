"""Pairing API — Phase 2A-App 移动端配对认证"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

# In-memory store (MVP — replace with DB table for production)
_pairing_tokens: dict[str, dict] = {}


class PairCreateRequest(BaseModel):
    tenant_id: str = "default"


class PairVerifyRequest(BaseModel):
    token: str


@router.post("/pair/create")
async def create_pair_token(req: PairCreateRequest):
    """桌面端生成配对 Token + 二维码内容"""
    token = secrets.token_urlsafe(24)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    _pairing_tokens[token] = {
        "tenant_id": req.tenant_id,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.utcnow().isoformat(),
    }
    return {
        "success": True,
        "data": {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "pairing_content": {
                "type": "personal_notebook_pairing",
                "core_base_url": "http://HOST:8000",
                "tenant_id": req.tenant_id,
                "token": token,
                "expires_at": expires_at.isoformat(),
            },
        },
    }


@router.post("/pair/verify")
async def verify_pair_token(req: PairVerifyRequest):
    """移动端验证配对 Token"""
    entry = _pairing_tokens.get(req.token)
    if not entry:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    expires = datetime.fromisoformat(entry["expires_at"])
    if datetime.utcnow() > expires:
        del _pairing_tokens[req.token]
        raise HTTPException(status_code=401, detail="Token expired")
    return {
        "success": True,
        "data": {"tenant_id": entry["tenant_id"], "verified": True},
    }


@router.get("/devices")
async def list_devices():
    """列出当前活跃配对"""
    return {
        "success": True,
        "data": {
            "devices": [
                {"token_hash": secrets.token_hex(8), "created_at": v["created_at"]}
                for v in _pairing_tokens.values()
            ],
        },
    }


@router.delete("/devices/{token_hash}")
async def revoke_device(token_hash: str):
    """撤销配对"""
    # Find and remove matching token
    to_remove = [k for k in _pairing_tokens if secrets.token_hex(8) == token_hash]
    for k in to_remove:
        del _pairing_tokens[k]
    return {"success": True, "message": f"Revoked {len(to_remove)} device(s)"}
