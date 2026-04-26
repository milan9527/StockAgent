"""
系统设置路由 - LLM切换、Max Tokens、数据源管理
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from db.models import User
from api.auth import get_current_user
from agents.model_loader import (
    list_available_models, set_active_model_key, get_active_model_key,
    get_runtime_max_tokens, set_runtime_max_tokens,
)
from agents.skills.market_data_skill import list_market_data_sources

router = APIRouter(prefix="/api/settings", tags=["系统设置"])


class SwitchModelRequest(BaseModel):
    model_key: str


class UpdateMaxTokensRequest(BaseModel):
    max_tokens: int


@router.get("/models")
async def get_models(current_user: User = Depends(get_current_user)):
    """获取可用LLM模型列表"""
    return {
        "models": list_available_models(),
        "active": get_active_model_key(),
        "max_tokens": get_runtime_max_tokens(),
    }


@router.post("/models/switch")
async def switch_model(
    request: SwitchModelRequest,
    current_user: User = Depends(get_current_user),
):
    """切换LLM模型"""
    ok = set_active_model_key(request.model_key)
    if not ok:
        raise HTTPException(status_code=400, detail=f"未知模型: {request.model_key}")
    return {"message": f"已切换到 {request.model_key}", "active": get_active_model_key()}


@router.post("/models/max-tokens")
async def update_max_tokens(
    request: UpdateMaxTokensRequest,
    current_user: User = Depends(get_current_user),
):
    """更新Max Tokens设置"""
    if request.max_tokens < 1024 or request.max_tokens > 128000:
        raise HTTPException(status_code=400, detail="max_tokens 范围: 1024 - 128000")
    set_runtime_max_tokens(request.max_tokens)
    return {"message": f"Max Tokens 已更新为 {request.max_tokens}", "max_tokens": request.max_tokens}


@router.get("/data-sources")
async def get_data_sources(current_user: User = Depends(get_current_user)):
    """获取可用行情数据源"""
    return {"sources": list_market_data_sources()}
