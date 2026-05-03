"""
认证路由 - 支持Cognito和本地DB
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User
from api.auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from api.schemas import LoginRequest, TokenResponse, UserResponse
from config.settings import get_settings

router = APIRouter(prefix="/api/auth", tags=["认证"])
_settings = get_settings()


class ProfileUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    risk_preference: Optional[str] = None
    phone: Optional[str] = None
    notification_email_address: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = ""


@router.get("/config")
async def get_auth_config():
    """返回认证配置信息 (前端用于显示Cognito登录/注册选项)"""
    cognito_enabled = bool(_settings.COGNITO_USER_POOL_ID and _settings.COGNITO_CLIENT_ID)
    return {
        "cognito_enabled": cognito_enabled,
        "allow_registration": cognito_enabled,
    }


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    success, error, user = await authenticate_user(request.username, request.password, db)
    if not success or not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error or "用户名或密码错误")
    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token, user_id=str(user.id), username=user.username)


@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户 - 支持Cognito和本地DB"""
    from sqlalchemy import select
    from api.auth import cognito_signup, _seed_new_user_data

    email = request.email or f"{request.username}@local"

    # If Cognito is configured, register in Cognito first
    if _settings.COGNITO_USER_POOL_ID and _settings.COGNITO_CLIENT_ID:
        cognito_result = cognito_signup(request.username, request.password, email)
        if not cognito_result.get("success"):
            raise HTTPException(status_code=400, detail=cognito_result.get("error", "注册失败"))

    # Check if user already exists in local DB
    result = await db.execute(select(User).where(User.username == request.username))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # Create local DB user
    user = User(
        username=request.username,
        email=email,
        hashed_password=get_password_hash(request.password),
        full_name=request.username,
        risk_preference="moderate",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Seed default data
    await _seed_new_user_data(user, db)

    # Auto-login: return token
    token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=token, user_id=str(user.id), username=user.username)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id), username=current_user.username,
        email=current_user.email, full_name=current_user.full_name,
        risk_preference=current_user.risk_preference,
        notification_email=current_user.notification_email,
        notification_push=current_user.notification_push,
        notification_email_address=current_user.notification_email_address or current_user.email or "",
    )


@router.put("/profile")
async def update_profile(
    request: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新用户资料"""
    if request.notification_email_address is not None:
        current_user.notification_email_address = request.notification_email_address
        # Also update all scheduled tasks' notification email
        from db.models import ScheduledTask
        from sqlalchemy import update as sql_update
        await db.execute(
            sql_update(ScheduledTask)
            .where(ScheduledTask.user_id == current_user.id)
            .values(notification_email=request.notification_email_address)
        )
    if request.email:
        # Check if email is already used by another user
        from sqlalchemy import select as _sel
        existing = await db.execute(
            _sel(User).where(User.email == request.email, User.id != current_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该邮箱已被其他用户使用")
        current_user.email = request.email
    if request.full_name:
        current_user.full_name = request.full_name
    if request.risk_preference:
        current_user.risk_preference = request.risk_preference
    if request.phone:
        current_user.phone = request.phone
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=400, detail="该邮箱已被其他用户使用")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)[:200]}")
    return {"success": True}
