"""
Agent对话路由 - 通过AgentCore Runtime调用Agent
对话存储在AgentCore Memory (STM + LTM)
支持Smart Select (Registry语义搜索)
"""
from __future__ import annotations

import uuid
import asyncio
import traceback
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from db.models import User
from api.auth import get_current_user
from api.schemas import ChatRequest, ChatResponse
from config.settings import get_settings

router = APIRouter(prefix="/api/chat", tags=["Agent对话"])
settings = get_settings()


class SmartSelectRequest(BaseModel):
    query: str
    max_results: int = 5


@router.post("/smart-select")
async def smart_select_skills(
    request: SmartSelectRequest,
    current_user: User = Depends(get_current_user),
):
    """使用AgentCore Registry语义搜索，根据用户消息自动选择相关Skills"""
    registry_id = settings.AGENTCORE_REGISTRY_ID
    if not registry_id:
        return {"skills": [], "message": "Registry未配置"}

    try:
        import boto3
        client = boto3.client("bedrock-agentcore", region_name=settings.AWS_REGION)
        registry_arn = f"arn:aws:bedrock-agentcore:{settings.AWS_REGION}:632930644527:registry/{registry_id}"

        response = client.search_registry_records(
            registryIds=[registry_arn],
            searchQuery=request.query,
            maxResults=request.max_results,
        )

        skills = []
        for rec in response.get("registryRecords", []):
            skills.append({
                "name": rec.get("name", ""),
                "status": rec.get("status", ""),
                "type": rec.get("descriptorType", ""),
            })

        return {"skills": skills, "query": request.query}
    except Exception as e:
        return {"skills": [], "error": str(e)[:200]}


@router.post("/", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """与Agent对话 - 通过AgentCore Runtime调用，对话存储在Memory"""
    # 使用用户ID作为session的一部分，确保Memory按用户隔离
    session_id = request.session_id or f"chat-{current_user.id}-{uuid.uuid4().hex[:8]}"

    # 确保session_id >= 33 chars (AgentCore要求)
    if len(session_id) < 33:
        session_id = f"{session_id}-{uuid.uuid4().hex}"

    context_prompt = (
        f"[用户: {current_user.full_name or current_user.username}, "
        f"风险偏好: {current_user.risk_preference}]\n\n"
        f"{request.message}"
    )

    try:
        from agents.runtime_client import invoke_runtime_agent

        response_text = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: invoke_runtime_agent(
                prompt=context_prompt,
                session_id=session_id,
                user_id=str(current_user.id),
            )
        )

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            agent_type=request.agent_type or "orchestrator",
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        error_msg = str(e)
        print(f"[Chat Error] {error_msg}\n{traceback.format_exc()}")

        if "ReadTimeout" in error_msg or "timed out" in error_msg.lower():
            error_response = "⚠️ AgentCore Runtime响应超时，请稍后重试。"
        else:
            error_response = f"⚠️ Agent调用出错: {error_msg[:300]}"

        return ChatResponse(
            response=error_response,
            session_id=session_id,
            agent_type=request.agent_type or "orchestrator",
            timestamp=datetime.now().isoformat(),
        )
