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


class TestEmailRequest(BaseModel):
    to_email: str


@router.post("/test-email")
async def test_email(request: TestEmailRequest, current_user: User = Depends(get_current_user)):
    """发送测试通知 - 使用SNS (自动创建Topic并订阅邮箱)"""
    try:
        import boto3
        from config.settings import get_settings
        _s = get_settings()

        sns = boto3.client("sns", region_name=_s.AWS_REGION)

        # Get or create SNS topic
        topic_arn = _s.SNS_TOPIC_ARN
        if not topic_arn:
            resp = sns.create_topic(Name="securities-trading-notifications")
            topic_arn = resp["TopicArn"]

        # Check if email is already subscribed
        subs = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        subscribed = any(
            s["Endpoint"] == request.to_email and s["Protocol"] == "email" and s["SubscriptionArn"] != "PendingConfirmation"
            for s in subs.get("Subscriptions", [])
        )
        pending = any(
            s["Endpoint"] == request.to_email and s["SubscriptionArn"] == "PendingConfirmation"
            for s in subs.get("Subscriptions", [])
        )

        if not subscribed and not pending:
            # Subscribe email
            sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=request.to_email)
            return {
                "status": "subscription_sent",
                "message": f"订阅确认邮件已发送到 {request.to_email}, 请查收并点击确认链接, 然后重试发送测试",
                "topic_arn": topic_arn,
            }

        if pending:
            return {
                "status": "pending",
                "message": f"{request.to_email} 订阅待确认, 请查收邮件并点击确认链接",
            }

        # Send test notification
        sns.publish(
            TopicArn=topic_arn,
            Subject="证券交易助手 - 通知测试",
            Message=f"这是一封测试通知, 确认SNS邮件通知服务正常工作。\n\n用户: {current_user.username}\n时间: {__import__('datetime').datetime.now().isoformat()}",
        )
        return {"status": "sent", "message": f"测试通知已发送到 {request.to_email}", "topic_arn": topic_arn}

    except Exception as e:
        return {"status": "error", "message": str(e)[:300]}
