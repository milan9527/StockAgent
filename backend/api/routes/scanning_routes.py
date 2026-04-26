"""
Skill安全扫描路由 - LLM驱动的多维度风险评估
参考 AgentcoreRegistrySkillHub 的扫描模式
使用Claude Sonnet 4.6分析Skill内容，评估安全/合规/兼容/许可风险
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User, CustomSkill
from api.auth import get_current_user

router = APIRouter(prefix="/api/scanning", tags=["Skill扫描"])

SCAN_DIMENSIONS = {
    "security": {
        "name": "安全扫描",
        "description": "检查硬编码密钥、输入验证、注入风险、不安全模式、依赖风险",
        "prompt": """分析以下Skill代码的安全风险。检查:
1. 硬编码密钥/密码/Token
2. 输入验证缺失(SQL注入、命令注入、路径遍历)
3. 不安全的网络请求(无TLS、无超时)
4. 危险函数调用(eval、exec、subprocess)
5. 敏感数据泄露风险

返回JSON格式:
{"score": 0-100, "findings": [{"severity": "critical/high/medium/low/info", "title": "标题", "description": "描述"}]}
分数越高越安全。""",
    },
    "compliance": {
        "name": "合规扫描",
        "description": "检查GDPR/数据处理、审计日志、访问控制",
        "prompt": """分析以下Skill代码的合规性。检查:
1. 个人数据处理(GDPR相关)
2. 审计日志记录
3. 访问控制和权限检查
4. 数据加密和传输安全
5. 错误处理和信息泄露

返回JSON格式:
{"score": 0-100, "findings": [{"severity": "critical/high/medium/low/info", "title": "标题", "description": "描述"}]}""",
    },
    "compatibility": {
        "name": "兼容性扫描",
        "description": "检查协议版本、Schema验证、依赖冲突",
        "prompt": """分析以下Skill代码的兼容性。检查:
1. Python版本兼容性
2. 依赖库版本冲突风险
3. API接口稳定性
4. 错误处理健壮性
5. 跨平台兼容性

返回JSON格式:
{"score": 0-100, "findings": [{"severity": "critical/high/medium/low/info", "title": "标题", "description": "描述"}]}""",
    },
    "license": {
        "name": "许可证扫描",
        "description": "检查许可证类型、Copyleft风险、依赖许可证",
        "prompt": """分析以下Skill代码的许可证风险。检查:
1. 代码中引用的第三方库许可证
2. Copyleft风险(GPL等)
3. 商业使用限制
4. 数据使用限制
5. 出口管制风险

返回JSON格式:
{"score": 0-100, "findings": [{"severity": "critical/high/medium/low/info", "title": "标题", "description": "描述"}]}""",
    },
}


class ScanRequest(BaseModel):
    skill_id: str
    scan_types: list[str] = ["security", "compliance", "compatibility", "license"]


def _invoke_claude_for_scan(skill_content: str, scan_prompt: str) -> dict:
    """调用Claude进行扫描分析"""
    import boto3
    from botocore.config import Config as BotoConfig

    client = boto3.client("bedrock-runtime", region_name="us-east-1",
                          config=BotoConfig(read_timeout=120))

    prompt = f"""{scan_prompt}

Skill代码内容:
```
{skill_content[:8000]}
```

请严格返回JSON格式，不要包含其他文本。"""

    try:
        response = client.converse(
            modelId="us.anthropic.claude-sonnet-4-6",
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 2048, "temperature": 0.1},
        )
        text = response["output"]["message"]["content"][0]["text"]
        # Extract JSON from response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"score": 50, "findings": [{"severity": "info", "title": "解析失败", "description": "LLM返回格式异常"}]}
    except Exception as e:
        return {"score": 50, "findings": [{"severity": "info", "title": "扫描失败", "description": str(e)[:200]}]}


@router.get("/dimensions")
async def get_scan_dimensions(current_user: User = Depends(get_current_user)):
    """获取扫描维度列表"""
    return {"dimensions": [
        {"id": k, "name": v["name"], "description": v["description"]}
        for k, v in SCAN_DIMENSIONS.items()
    ]}


@router.post("/scan")
async def scan_skill(
    request: ScanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对Skill进行LLM安全扫描"""
    import asyncio

    # 获取Skill
    result = await db.execute(
        select(CustomSkill).where(CustomSkill.id == request.skill_id)
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill不存在")

    if not skill.code:
        return {"error": "Skill没有代码内容，无法扫描"}

    # 对每个维度进行扫描
    scan_results = {}
    overall_score = 0

    for scan_type in request.scan_types:
        if scan_type not in SCAN_DIMENSIONS:
            continue
        dim = SCAN_DIMENSIONS[scan_type]

        # Run LLM scan in thread pool
        result_data = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda st=scan_type: _invoke_claude_for_scan(skill.code, SCAN_DIMENSIONS[st]["prompt"])
        )

        scan_results[scan_type] = {
            "dimension": dim["name"],
            "score": result_data.get("score", 50),
            "findings": result_data.get("findings", []),
            "scanned_at": datetime.now().isoformat(),
        }
        overall_score += result_data.get("score", 50)

    if scan_results:
        overall_score = overall_score // len(scan_results)

    return {
        "skill_id": request.skill_id,
        "skill_name": skill.name,
        "overall_score": overall_score,
        "risk_level": "低风险" if overall_score >= 70 else "中风险" if overall_score >= 40 else "高风险",
        "results": scan_results,
        "scanned_at": datetime.now().isoformat(),
    }


@router.post("/scan-builtin/{skill_name}")
async def scan_builtin_skill(
    skill_name: str,
    current_user: User = Depends(get_current_user),
):
    """扫描内置Skill"""
    import asyncio
    import os

    # 读取内置Skill源文件
    skill_file_map = {
        "market-data-skill": "agents/skills/market_data_skill.py",
        "analysis-skill": "agents/skills/analysis_skill.py",
        "web-fetch-skill": "agents/skills/web_fetch_skill.py",
        "trading-skill": "agents/skills/trading_skill.py",
        "quant-skill": "agents/skills/quant_skill.py",
        "notification-skill": "agents/skills/notification_skill.py",
    }

    filepath = skill_file_map.get(skill_name)
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"内置Skill '{skill_name}' 不存在")

    with open(filepath) as f:
        code = f.read()

    scan_results = {}
    overall_score = 0

    for scan_type, dim in SCAN_DIMENSIONS.items():
        result_data = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda st=scan_type: _invoke_claude_for_scan(code, SCAN_DIMENSIONS[st]["prompt"])
        )
        scan_results[scan_type] = {
            "dimension": dim["name"],
            "score": result_data.get("score", 50),
            "findings": result_data.get("findings", []),
        }
        overall_score += result_data.get("score", 50)

    overall_score = overall_score // max(len(scan_results), 1)

    return {
        "skill_name": skill_name,
        "overall_score": overall_score,
        "risk_level": "低风险" if overall_score >= 70 else "中风险" if overall_score >= 40 else "高风险",
        "results": scan_results,
    }
