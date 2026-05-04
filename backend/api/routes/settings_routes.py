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
    """发送测试邮件 - 使用SES (需要先验证邮箱)"""
    try:
        import boto3
        from config.settings import get_settings
        from datetime import datetime
        _s = get_settings()

        ses = boto3.client("ses", region_name=_s.AWS_REGION)

        # Check if email is verified in SES
        try:
            resp = ses.get_identity_verification_attributes(Identities=[request.to_email])
            attrs = resp.get("VerificationAttributes", {}).get(request.to_email, {})
            status = attrs.get("VerificationStatus", "")
        except Exception:
            status = ""

        if status != "Success":
            # Need to verify email first
            if status == "Pending":
                return {
                    "status": "pending",
                    "message": f"验证邮件已发送到 {request.to_email}，请查收并点击确认链接，然后重试",
                }
            # Send verification email
            ses.verify_email_identity(EmailAddress=request.to_email)
            return {
                "status": "verification_sent",
                "message": f"SES验证邮件已发送到 {request.to_email}，请查收并点击确认链接。确认后即可接收HTML格式通知邮件。",
            }

        # Email is verified — send test HTML email
        html_body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;padding:20px;margin:0;">
<div style="max-width:680px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
  <div style="background:linear-gradient(135deg,#1a2332,#2d3f52);padding:24px 32px;">
    <h1 style="color:#d4a843;margin:0;font-size:20px;">证券交易助手</h1>
    <p style="color:#9ca3af;margin:4px 0 0;font-size:13px;">邮件通知测试</p>
  </div>
  <div style="padding:24px 32px;">
    <p style="color:#374151;font-size:14px;line-height:1.7;">
      这是一封测试邮件，确认SES邮件通知服务正常工作。
    </p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
      <tr><td style="padding:8px 12px;background:#f8f9fa;color:#6b7280;font-size:13px;width:80px;border-radius:6px 0 0 0;">用户</td>
          <td style="padding:8px 12px;background:#f8f9fa;font-size:13px;font-weight:600;border-radius:0 6px 0 0;">{current_user.full_name or current_user.username}</td></tr>
      <tr><td style="padding:8px 12px;background:#f8f9fa;color:#6b7280;font-size:13px;border-radius:0 0 0 6px;">时间</td>
          <td style="padding:8px 12px;background:#f8f9fa;font-size:13px;border-radius:0 0 6px 0;">{datetime.now().strftime('%Y-%m-%d %H:%M')}</td></tr>
    </table>
    <p style="color:#059669;font-size:14px;font-weight:600;">✅ SES邮件服务配置成功！定期任务执行结果将以HTML格式发送到此邮箱。</p>
  </div>
  <div style="background:#f8f9fa;padding:16px 32px;border-top:1px solid #e5e7eb;">
    <p style="color:#9ca3af;font-size:11px;margin:0;text-align:center;">
      证券交易助手 Agent 平台 · Powered by AWS Bedrock AgentCore
    </p>
  </div>
</div></body></html>"""

        # Use verified email as sender, or the recipient as both sender and recipient
        sender = request.to_email  # In sandbox, sender must also be verified
        ses.send_email(
            Source=sender,
            Destination={"ToAddresses": [request.to_email]},
            Message={
                "Subject": {"Data": "证券交易助手 - 邮件通知测试", "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                    "Text": {"Data": f"测试邮件 - 用户: {current_user.username}, 时间: {datetime.now().isoformat()}", "Charset": "UTF-8"},
                },
            },
        )
        return {"status": "sent", "message": f"HTML测试邮件已发送到 {request.to_email}"}

    except Exception as e:
        error_msg = str(e)
        if "not verified" in error_msg.lower():
            return {"status": "error", "message": f"邮箱 {request.to_email} 尚未通过SES验证，请先点击验证链接"}
        return {"status": "error", "message": error_msg[:300]}


@router.get("/ses-status")
async def get_ses_status(current_user: User = Depends(get_current_user)):
    """检查用户通知邮箱的SES验证状态"""
    try:
        import boto3
        from config.settings import get_settings
        _s = get_settings()
        ses = boto3.client("ses", region_name=_s.AWS_REGION)

        # Get user's notification email
        email = current_user.notification_email_address or current_user.email or ""
        if not email:
            return {"email": "", "verified": False, "status": "no_email"}

        resp = ses.get_identity_verification_attributes(Identities=[email])
        attrs = resp.get("VerificationAttributes", {}).get(email, {})
        status = attrs.get("VerificationStatus", "NotStarted")

        return {
            "email": email,
            "verified": status == "Success",
            "status": status,
        }
    except Exception as e:
        return {"email": "", "verified": False, "status": "error", "error": str(e)[:200]}
