"""
AgentCore Runtime Client
Backend通过此客户端调用部署在AgentCore Runtime上的Agent
"""
from __future__ import annotations

import os
import json
import boto3
from botocore.config import Config as BotoConfig
from config.settings import get_settings

settings = get_settings()


def _get_agent_arn() -> str:
    """获取Agent Runtime ARN"""
    # 1. 环境变量
    arn = os.environ.get("AGENTCORE_AGENT_ARN", "")
    if arn:
        return arn

    # 2. 从agent_id构建ARN
    agent_id = os.environ.get("AGENTCORE_AGENT_ID", "")
    if agent_id:
        return f"arn:aws:bedrock-agentcore:{settings.AWS_REGION}:632930644527:runtime/{agent_id}"

    # 3. 从yaml读取
    try:
        import yaml
        with open(".bedrock_agentcore.yaml") as f:
            config = yaml.safe_load(f)
        for name, agent in config.get("agents", {}).items():
            ac = agent.get("bedrock_agentcore", {})
            if ac.get("agent_arn"):
                return ac["agent_arn"]
            if ac.get("agent_id"):
                return f"arn:aws:bedrock-agentcore:{settings.AWS_REGION}:632930644527:runtime/{ac['agent_id']}"
    except Exception:
        pass
    return ""


def invoke_runtime_agent(
    prompt: str,
    session_id: str = "default",
    user_id: str = "anonymous",
) -> str:
    """调用AgentCore Runtime上的Agent"""
    agent_arn = _get_agent_arn()
    if not agent_arn:
        # Fallback: 本地直接调用
        return _invoke_local(prompt, session_id, user_id)

    try:
        return _invoke_runtime(agent_arn, prompt, session_id, user_id)
    except Exception as e:
        error_msg = str(e)
        print(f"[RuntimeClient] Runtime invoke failed: {error_msg}")
        # 如果Runtime调用失败，fallback到本地
        if "not found" in error_msg.lower() or "not ready" in error_msg.lower():
            print("[RuntimeClient] Falling back to local agent")
            return _invoke_local(prompt, session_id, user_id)
        raise


def _invoke_local(prompt: str, session_id: str, user_id: str) -> str:
    """本地直接调用Agent"""
    from agents.orchestrator_agent import create_orchestrator_agent
    agent = create_orchestrator_agent(session_id=session_id, actor_id=user_id)
    response = agent(prompt)
    return str(response)


def _invoke_runtime(agent_arn: str, prompt: str, session_id: str, user_id: str) -> str:
    """通过AgentCore Runtime API调用Agent"""
    client = boto3.client("bedrock-agentcore", region_name=settings.AWS_REGION,
                          config=BotoConfig(read_timeout=600, connect_timeout=10))

    payload = json.dumps({
        "prompt": prompt,
        "session_id": session_id,
        "user_id": user_id,
    })

    # Session ID must be >= 33 chars for AgentCore Runtime
    import uuid as _uuid
    if len(session_id) < 33:
        session_id = f"{session_id}-{_uuid.uuid4()}"

    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=session_id,
        runtimeUserId=user_id,
        contentType="application/json",
        accept="application/json",
        payload=payload.encode("utf-8"),
    )

    # 读取响应 - AgentCore Runtime returns 'response' as StreamingBody
    resp_body = response.get("response")
    if resp_body:
        if hasattr(resp_body, "read"):
            data = resp_body.read().decode("utf-8")
        elif isinstance(resp_body, bytes):
            data = resp_body.decode("utf-8")
        else:
            data = str(resp_body)

        try:
            parsed = json.loads(data)
            return parsed.get("response", data)
        except json.JSONDecodeError:
            return data

    return "Agent未返回响应"
