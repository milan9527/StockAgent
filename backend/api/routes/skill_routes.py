"""
Skill管理路由 - 内置Skills展示 + 用户自定义Skills + 外部导入
"""
from __future__ import annotations

import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User, CustomSkill
from api.auth import get_current_user
from api.schemas import CustomSkillCreate, CustomSkillResponse

router = APIRouter(prefix="/api/skills", tags=["Skills管理"])


# ═══════════════════════════════════════════════════════
# 内置Skills定义
# ═══════════════════════════════════════════════════════
BUILTIN_SKILLS = [
    {
        "id": "builtin-market-data",
        "name": "行情数据技能",
        "skill_type": "market",
        "description": "多数据源实时行情(腾讯/新浪/Yahoo)、K线历史数据、股票搜索",
        "tools": ["get_stock_realtime_quote", "get_stock_batch_quotes", "get_stock_kline", "search_stocks", "list_market_data_sources"],
        "source": "builtin",
        "version": "2.0.0",
        "used_by": ["投资分析Agent", "股票交易Agent", "编排Agent"],
    },
    {
        "id": "builtin-analysis",
        "name": "投资分析技能",
        "skill_type": "analysis",
        "description": "技术指标计算(MA/MACD/RSI/BOLL)、趋势判断、投资报告生成",
        "tools": ["analyze_technical_indicators", "generate_investment_report"],
        "source": "builtin",
        "version": "1.0.0",
        "used_by": ["投资分析Agent"],
    },
    {
        "id": "builtin-web-fetch",
        "name": "Web信息获取技能",
        "skill_type": "web",
        "description": "互联网搜索、网页内容提取、财经新闻搜索",
        "tools": ["web_search", "fetch_web_page", "search_financial_news"],
        "source": "builtin",
        "version": "1.0.0",
        "used_by": ["投资分析Agent"],
    },
    {
        "id": "builtin-trading",
        "name": "交易技能",
        "skill_type": "trading",
        "description": "模拟盘交易执行、交易信号生成、仓位计算、策略条件评估",
        "tools": ["execute_simulated_order", "generate_trading_signal", "calculate_position_size", "evaluate_strategy_conditions"],
        "source": "builtin",
        "version": "1.0.0",
        "used_by": ["股票交易Agent"],
    },
    {
        "id": "builtin-quant",
        "name": "量化交易技能",
        "skill_type": "quant",
        "description": "量化策略回测引擎、预置模板(幻方量化风格)、绩效指标计算",
        "tools": ["run_backtest", "list_quant_templates", "calculate_performance_metrics"],
        "source": "builtin",
        "version": "1.0.0",
        "used_by": ["量化交易Agent"],
    },
    {
        "id": "builtin-notification",
        "name": "通知技能",
        "skill_type": "notification",
        "description": "多渠道交易信号通知(SES邮件/推送)、每日投资报告",
        "tools": ["send_trading_signal_notification", "format_daily_report"],
        "source": "builtin",
        "version": "4.0.0",
        "used_by": ["股票交易Agent"],
    },
    {
        "id": "builtin-crawler",
        "name": "专业财经爬虫技能",
        "skill_type": "web",
        "description": "东方财富/新浪/财联社新闻爬虫、个股研报、深度网页采集、行业数据",
        "tools": ["crawl_financial_news", "crawl_stock_reports", "crawl_web_page_deep", "crawl_industry_data", "list_available_crawlers"],
        "source": "builtin",
        "version": "4.0.0",
        "used_by": ["投资分析Agent"],
    },
    {
        "id": "builtin-browser",
        "name": "浏览器爬虫技能",
        "skill_type": "web",
        "description": "AgentCore Browser网页浏览、数据采集、动态页面交互、Web Bot Auth",
        "tools": ["AgentCoreBrowser.browser"],
        "source": "builtin",
        "version": "4.0.0",
        "used_by": ["投资分析Agent", "编排Agent"],
    },
    {
        "id": "builtin-code-interpreter",
        "name": "代码执行技能",
        "skill_type": "quant",
        "description": "AgentCore Code Interpreter代码执行、数据分析、可视化、量化计算",
        "tools": ["AgentCoreCodeInterpreter.code_interpreter"],
        "source": "builtin",
        "version": "4.0.0",
        "used_by": ["投资分析Agent", "量化交易Agent", "编排Agent"],
    },
]


class ImportSkillRequest(BaseModel):
    name: str
    description: str = ""
    skill_type: str = "external"
    source_type: str = "mcp"  # mcp / pip / url
    source_url: str = ""
    package_name: str = ""
    code: str = ""
    parameters_schema: dict = {}


# ── 内置Skills ──
@router.get("/builtin")
async def get_builtin_skills(current_user: User = Depends(get_current_user)):
    """获取所有内置Skills"""
    return {"skills": BUILTIN_SKILLS}


# ── 所有Skills (内置 + 自定义) ──
@router.get("/all")
async def get_all_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有Skills (内置 + 用户自定义)"""
    result = await db.execute(
        select(CustomSkill).where(CustomSkill.user_id == current_user.id)
    )
    custom = result.scalars().all()

    custom_list = [{
        "id": str(s.id),
        "name": s.name,
        "skill_type": s.skill_type,
        "description": s.description,
        "tools": [],
        "source": "custom",
        "version": s.version,
        "used_by": [],
        "code": s.code,
        "is_published": s.is_published,
    } for s in custom]

    return {
        "builtin": BUILTIN_SKILLS,
        "custom": custom_list,
        "total": len(BUILTIN_SKILLS) + len(custom_list),
    }


# ── 用户自定义Skills CRUD ──
@router.get("/", response_model=list[CustomSkillResponse])
async def get_custom_skills(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomSkill).where(CustomSkill.user_id == current_user.id)
    )
    skills = result.scalars().all()
    return [CustomSkillResponse(
        id=str(s.id), name=s.name, description=s.description,
        skill_type=s.skill_type, code=s.code,
        is_published=s.is_published, version=s.version,
    ) for s in skills]


@router.post("/", response_model=CustomSkillResponse)
async def create_skill(
    skill: CustomSkillCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_skill = CustomSkill(
        user_id=current_user.id,
        name=skill.name,
        description=skill.description,
        skill_type=skill.skill_type,
        code=skill.code,
        parameters_schema=skill.parameters_schema,
    )
    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)
    return CustomSkillResponse(
        id=str(new_skill.id), name=new_skill.name,
        description=new_skill.description, skill_type=new_skill.skill_type,
        code=new_skill.code, is_published=new_skill.is_published,
        version=new_skill.version,
    )


@router.put("/{skill_id}", response_model=CustomSkillResponse)
async def update_skill(
    skill_id: str, skill: CustomSkillCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomSkill).where(CustomSkill.id == skill_id, CustomSkill.user_id == current_user.id)
    )
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Skill不存在")
    existing.name = skill.name
    existing.description = skill.description
    existing.skill_type = skill.skill_type
    existing.code = skill.code
    existing.parameters_schema = skill.parameters_schema
    await db.commit()
    await db.refresh(existing)
    return CustomSkillResponse(
        id=str(existing.id), name=existing.name, description=existing.description,
        skill_type=existing.skill_type, code=existing.code,
        is_published=existing.is_published, version=existing.version,
    )


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomSkill).where(CustomSkill.id == skill_id, CustomSkill.user_id == current_user.id)
    )
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Skill不存在")
    await db.delete(existing)
    await db.commit()
    return {"message": "Skill已删除"}


# ── 导入外部Skill ──

def _publish_to_registry(skill_name: str, skill_description: str, skill_code: str, skill_version: str = "1.0.0") -> dict:
    """Helper: publish a skill to AgentCore Registry as DRAFT (needs approval)"""
    from config.settings import get_settings
    _settings = get_settings()
    registry_id = _settings.AGENTCORE_REGISTRY_ID
    if not registry_id:
        return {"registry": "not_configured"}
    try:
        import boto3, time
        client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")
        safe_name = skill_name.replace(" ", "-").lower()[:60]
        md = f"---\nname: {safe_name}\ndescription: {skill_description[:200]}\n---\n\n# {skill_name}\n\n{skill_description}\n"
        if skill_code:
            md += f"\n## Code\n```\n{skill_code[:3000]}\n```\n"

        r = client.create_registry_record(
            registryId=registry_id, name=safe_name, descriptorType="AGENT_SKILLS",
            descriptors={"agentSkills": {"skillMd": {"inlineContent": md}}},
            recordVersion=skill_version, description=skill_description[:200],
        )
        record_id = r["recordArn"].split("/")[-1]
        time.sleep(2)
        client.submit_registry_record_for_approval(registryId=registry_id, recordId=record_id)
        return {"registry": "submitted", "record_id": record_id, "status": "PENDING_APPROVAL"}
    except Exception as e:
        return {"registry": "error", "detail": str(e)[:150]}


@router.post("/import")
async def import_external_skill(
    request: ImportSkillRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """导入外部Skill并自动提交到Registry审批"""
    new_skill = CustomSkill(
        user_id=current_user.id,
        name=request.name,
        description=f"[{request.source_type.upper()}] {request.description}",
        skill_type=request.skill_type or "external",
        code=request.code or f"# 外部Skill: {request.source_type}\n# Source: {request.source_url or request.package_name}\n",
        parameters_schema={
            "source_type": request.source_type,
            "source_url": request.source_url,
            "package_name": request.package_name,
        },
    )
    db.add(new_skill)
    await db.commit()
    await db.refresh(new_skill)

    # Auto-publish to Registry
    reg_result = _publish_to_registry(request.name, request.description, new_skill.code)
    if reg_result.get("record_id"):
        new_skill.registry_record_id = reg_result["record_id"]
        await db.commit()

    return {
        "id": str(new_skill.id),
        "name": new_skill.name,
        "source_type": request.source_type,
        "message": f"外部Skill '{request.name}' 导入成功，已提交Registry审批",
        "registry": reg_result,
    }


@router.post("/{skill_id}/publish")
async def publish_skill(
    skill_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发布Skill到AgentCore Registry (需要审批)"""
    result = await db.execute(
        select(CustomSkill).where(CustomSkill.id == skill_id, CustomSkill.user_id == current_user.id)
    )
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill不存在")

    # Publish to AgentCore Registry
    registry_id = os.environ.get("AGENTCORE_REGISTRY_ID", "")
    if not registry_id:
        # Just mark as published locally
        skill.is_published = True
        await db.commit()
        return {"message": f"Skill '{skill.name}' 已标记为发布(Registry未配置)", "skill_id": str(skill.id)}

    try:
        import boto3
        client = boto3.client("bedrock-agentcore-control", region_name="us-east-1")

        md_content = f"---\nname: {skill.name}\ndescription: {skill.description}\n---\n\n# {skill.name}\n\n{skill.description}\n\n## Code\n```python\n{skill.code[:2000]}\n```"

        r = client.create_registry_record(
            registryId=registry_id,
            name=skill.name.replace(" ", "-").lower(),
            descriptorType="AGENT_SKILLS",
            descriptors={"agentSkills": {"skillMd": {"inlineContent": md_content}}},
            recordVersion=skill.version,
            description=skill.description[:200],
        )
        record_id = r["recordArn"].split("/")[-1]

        # Submit for approval (not auto-approved)
        import time
        time.sleep(2)
        client.submit_registry_record_for_approval(registryId=registry_id, recordId=record_id)

        skill.is_published = True
        skill.registry_record_id = record_id
        await db.commit()

        return {
            "message": f"Skill '{skill.name}' 已提交到Registry，等待审批",
            "skill_id": str(skill.id),
            "record_id": record_id,
            "status": "PENDING_APPROVAL",
        }
    except Exception as e:
        return {"error": f"Registry发布失败: {str(e)[:200]}"}


@router.post("/import-url")
async def import_skill_from_url(
    url: str = "",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从URL导入外部Skill (GitHub等)"""
    import httpx as hx

    if not url:
        raise HTTPException(status_code=400, detail="请提供URL")

    try:
        # Fetch content from URL
        # Support GitHub URLs - convert to raw
        raw_url = url
        if "github.com" in url and "/blob/" in url:
            raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        elif "github.com" in url and "/tree/" in url:
            # Try to fetch SKILL.md
            raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/tree/", "/") + "/SKILL.md"

        resp = hx.get(raw_url, timeout=15, follow_redirects=True,
                      headers={"User-Agent": "SecuritiesTradingBot/1.0"})
        content = resp.text

        # Parse name from content or URL
        name = url.split("/")[-1].replace(".py", "").replace(".md", "")
        if "---" in content:
            # Try parse YAML frontmatter
            parts = content.split("---")
            if len(parts) >= 3:
                import re
                name_match = re.search(r"name:\s*(.+)", parts[1])
                if name_match:
                    name = name_match.group(1).strip()

        new_skill = CustomSkill(
            user_id=current_user.id,
            name=name,
            description=f"[URL导入] {url}",
            skill_type="external",
            code=content[:10000],
            parameters_schema={"source_url": url, "source_type": "url"},
        )
        db.add(new_skill)
        await db.commit()
        await db.refresh(new_skill)

        # Auto-publish to Registry
        reg_result = _publish_to_registry(name, f"[URL导入] {url}", content[:3000])
        if reg_result.get("record_id"):
            new_skill.registry_record_id = reg_result["record_id"]
            await db.commit()

        return {
            "id": str(new_skill.id),
            "name": name,
            "message": f"从URL导入成功: {name}，已提交Registry审批",
            "content_length": len(content),
            "registry": reg_result,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)[:200]}")
