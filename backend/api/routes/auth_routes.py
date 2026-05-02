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
from api.auth import authenticate_user, create_access_token, get_current_user
from api.schemas import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["认证"])


class ProfileUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    risk_preference: Optional[str] = None
    phone: Optional[str] = None


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    success, error, user = await authenticate_user(request.username, request.password, db)
    if not success or not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error or "用户名或密码错误")
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
    )


@router.put("/profile")
async def update_profile(
    request: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新用户资料"""
    if request.email:
        current_user.email = request.email
    if request.full_name:
        current_user.full_name = request.full_name
    if request.risk_preference:
        current_user.risk_preference = request.risk_preference
    if request.phone:
        current_user.phone = request.phone
    await db.commit()
    return {"success": True}
