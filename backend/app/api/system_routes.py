"""
System Runtime API — Phase 2B 加固
桌面端 Core 服务生命周期管理 (仅本机可用)
"""

import os
import re
import subprocess
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

ENABLE_RUNTIME_API = os.getenv("ENABLE_RUNTIME_API", "true").lower() not in ("false", "0", "no")

SENSITIVE_KEYS = re.compile(
    r'(SECRET_KEY|PASSWORD|TOKEN|API_KEY|ACCESS_KEY|SECRET)\s*[=:]\s*\S+',
    re.IGNORECASE,
)


def _require_local(request: Request):
    if not ENABLE_RUNTIME_API:
        raise HTTPException(status_code=403, detail="Runtime API disabled (ENABLE_RUNTIME_API=false)")
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise HTTPException(status_code=403, detail="Runtime API only available from localhost")


def _sanitize(text: str) -> str:
    return SENSITIVE_KEYS.sub(lambda m: m.group(1).upper() + '=***REDACTED***', text)


@router.get("/system/status")
async def system_status(request: Request):
    """返回 Core 服务运行状态 (仅 localhost)"""
    _require_local(request)
    services = {}
    for name, check_cmd in [
        ("postgres", ["pg_isready", "-q"]),
        ("redis", ["redis-cli", "ping"]),
        ("qdrant", ["curl", "-sf", "http://localhost:6333/health"]),
        ("minio", ["curl", "-sf", "http://localhost:9000/minio/health/live"]),
    ]:
        try:
            subprocess.run(check_cmd, capture_output=True, timeout=5, check=True)
            services[name] = "running"
        except Exception:
            services[name] = "stopped"

    try:
        r = subprocess.run(["pgrep", "-f", "celery.*worker"], capture_output=True, text=True, timeout=3)
        services["celery_worker"] = "running" if r.stdout.strip() else "stopped"
    except Exception:
        services["celery_worker"] = "unknown"

    docker_ok = _check_docker()
    return {"success": True, "data": {"services": services, "docker_available": docker_ok}}


@router.post("/system/runtime/start")
async def runtime_start(request: Request):
    _require_local(request)
    try:
        r = subprocess.run(["docker", "compose", "up", "-d"], capture_output=True, text=True, timeout=120, cwd=_find_infra_dir())
        return {"success": r.returncode == 0, "data": {"output": _sanitize(r.stdout[-2000:])}}
    except FileNotFoundError:
        return {"success": False, "error": {"code": "DOCKER_NOT_FOUND", "message": "Docker not installed or not in PATH"}}
    except Exception as e:
        return {"success": False, "error": {"code": "RUNTIME_START_FAILED", "message": str(e)}}


@router.post("/system/runtime/stop")
async def runtime_stop(request: Request):
    _require_local(request)
    try:
        r = subprocess.run(["docker", "compose", "down"], capture_output=True, text=True, timeout=60, cwd=_find_infra_dir())
        return {"success": r.returncode == 0, "data": {"output": _sanitize(r.stdout[-2000:])}}
    except Exception as e:
        return {"success": False, "error": {"code": "RUNTIME_STOP_FAILED", "message": str(e)}}


@router.post("/system/runtime/restart")
async def runtime_restart(request: Request):
    await runtime_stop(request)
    return await runtime_start(request)


@router.get("/system/logs")
async def system_logs(request: Request, tail: int = 100):
    _require_local(request)
    try:
        r = subprocess.run(["docker", "compose", "logs", f"--tail={min(tail, 500)}"], capture_output=True, text=True, timeout=30, cwd=_find_infra_dir())
        return {"success": True, "data": {"logs": _sanitize(r.stdout[-5000:])}}
    except Exception as e:
        return {"success": False, "error": {"code": "LOGS_FAILED", "message": str(e)}}


def _check_docker() -> bool:
    try:
        subprocess.run(["docker", "--version"], capture_output=True, timeout=5, check=True)
        return True
    except Exception:
        return False


def _find_infra_dir() -> str:
    for root in [
        os.environ.get("PERSONAL_NOTEBOOK_ROOT", ""),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "infra"),
        os.path.join(os.getcwd(), "infra"),
        os.getcwd(),
    ]:
        if root and os.path.exists(os.path.join(root, "docker-compose.yml")):
            return root
    return os.getcwd()
