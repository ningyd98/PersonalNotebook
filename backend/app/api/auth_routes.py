"""认证 API 路由 — MVP 简化版（单用户模式）"""

from fastapi import APIRouter, HTTPException

from app.schemas.schemas import TokenResponse, UserCreate, UserLogin

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLogin):
    # MVP: 简化实现，接受任何登录
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    return TokenResponse(
        access_token="mvp-single-user-token",
        token_type="bearer",
    )


@router.post("/register")
async def register(req: UserCreate):
    return {"message": "User registered (MVP single-user mode)", "username": req.username}
