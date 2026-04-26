"""
投资分析路由 - 独立的投资分析模块API
支持模板化分析、Agent驱动的深度分析、Web信息获取
"""
from __future__ import annotations

import uuid
import traceback
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User, InvestmentReport
from api.auth import get_current_user
from agents.skills.market_data_skill import get_stock_realtime_quote
from agents.skills.analysis_skill import analyze_technical_indicators, generate_investment_report
from agents.skills.web_fetch_skill import web_search, search_financial_news

router = APIRouter(prefix="/api/analysis", tags=["投资分析"])


# ═══════════════════════════════════════════════════════
# 分析模板
# ═══════════════════════════════════════════════════════
ANALYSIS_TEMPLATES = [
    {
        "id": "stock-comprehensive",
        "name": "个股综合分析",
        "description": "对单只股票进行全面分析：实时行情 + 技术指标 + 趋势判断 + 投资评级",
        "category": "个股",
        "prompt_template": "请对{stock_name}({stock_code})进行全面的投资分析，包括基本面、技术面和市场情绪分析，给出投资建议。",
        "skills_used": ["行情数据", "技术分析", "投资报告"],
        "requires_agent": False,
    },
    {
        "id": "stock-deep-research",
        "name": "个股深度研究",
        "description": "使用AI Agent搜索最新新闻、公告、研报，结合行情数据进行深度研究",
        "category": "个股",
        "prompt_template": "请对{stock_name}({stock_code})进行深度研究分析。先搜索该公司最新的新闻、公告和研报，然后结合实时行情和技术指标，给出详细的投资分析报告。",
        "skills_used": ["行情数据", "技术分析", "Web搜索", "投资报告"],
        "requires_agent": True,
    },
    {
        "id": "sector-analysis",
        "name": "板块分析",
        "description": "分析某个行业板块的整体走势，筛选板块内优质标的",
        "category": "板块",
        "prompt_template": "请分析{sector}板块的整体走势和投资机会，搜索最新的行业政策和市场动态，推荐板块内3-5只优质股票并说明理由。",
        "skills_used": ["Web搜索", "行情数据", "技术分析"],
        "requires_agent": True,
    },
    {
        "id": "market-overview",
        "name": "市场全景分析",
        "description": "分析A股市场整体走势、资金流向、热点板块",
        "category": "市场",
        "prompt_template": "请分析当前A股市场的整体走势，搜索最新的市场新闻和政策动态，分析资金流向和热点板块，给出市场展望。",
        "skills_used": ["Web搜索", "行情数据"],
        "requires_agent": True,
    },
    {
        "id": "compare-stocks",
        "name": "个股对比分析",
        "description": "对比分析多只同行业股票，找出最优标的",
        "category": "对比",
        "prompt_template": "请对比分析以下股票：{stock_list}。从估值、成长性、技术形态等维度进行对比，推荐最优标的。",
        "skills_used": ["行情数据", "技术分析", "Web搜索"],
        "requires_agent": True,
    },
    {
        "id": "risk-assessment",
        "name": "风险评估",
        "description": "评估持仓或目标股票的风险水平，给出风控建议",
        "category": "风控",
        "prompt_template": "请对{stock_name}({stock_code})进行风险评估，分析下行风险、波动率、最大回撤预期，给出止损位和仓位建议。",
        "skills_used": ["行情数据", "技术分析"],
        "requires_agent": False,
    },
]


class AnalysisRequest(BaseModel):
    stock_code: str
    stock_name: str = ""
    source: str = "tencent"


class AgentAnalysisRequest(BaseModel):
    template_id: str = ""
    prompt: str = ""
    stock_code: str = ""
    stock_name: str = ""
    sector: str = ""
    stock_list: str = ""


class WebSearchRequest(BaseModel):
    query: str
    max_results: int = 5


@router.get("/templates")
async def get_analysis_templates(current_user: User = Depends(get_current_user)):
    """获取分析模板列表"""
    return {"templates": ANALYSIS_TEMPLATES}


@router.post("/stock")
async def analyze_stock(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对单只股票进行快速技术分析（不需要LLM）"""
    quote = get_stock_realtime_quote(request.stock_code, request.source)
    if "error" in quote:
        return {"error": quote["error"]}

    technical = analyze_technical_indicators(request.stock_code)

    stock_name = request.stock_name or quote.get("name", request.stock_code)
    report = generate_investment_report(
        stock_code=request.stock_code,
        stock_name=stock_name,
        quote_data=quote,
        technical_data=technical,
    )

    db_report = InvestmentReport(
        user_id=current_user.id,
        title=f"{stock_name}({request.stock_code}) 投资分析报告",
        report_type="stock",
        content=str(report),
        summary=f"评分:{report.get('composite_score', 0)} 建议:{report.get('recommendation', '')}",
        stock_codes=[request.stock_code],
        recommendations=[report.get("recommendation", "")],
    )
    db.add(db_report)
    await db.commit()

    return {
        "quote": quote,
        "technical": technical,
        "report": report,
        "report_id": str(db_report.id),
    }


@router.post("/agent")
async def agent_analysis(
    request: AgentAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """使用AI Agent进行深度分析（需要LLM）"""
    try:
        import asyncio
        from config.settings import get_settings
        _settings = get_settings()

        # 构建prompt
        prompt = request.prompt
        if not prompt and request.template_id:
            tmpl = next((t for t in ANALYSIS_TEMPLATES if t["id"] == request.template_id), None)
            if tmpl:
                prompt = tmpl["prompt_template"].format(
                    stock_code=request.stock_code or "未指定",
                    stock_name=request.stock_name or "未指定",
                    sector=request.sector or "未指定",
                    stock_list=request.stock_list or "未指定",
                )

        if not prompt:
            return {"error": "请提供分析需求或选择分析模板"}

        context = (
            f"[用户: {current_user.full_name or current_user.username}, "
            f"风险偏好: {current_user.risk_preference}]\n\n{prompt}"
        )

        # 通过AgentCore Runtime调用 (run in thread to not block async)
        from agents.runtime_client import invoke_runtime_agent
        response_text = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: invoke_runtime_agent(
                prompt=context,
                session_id=f"analysis-{current_user.id}",
                user_id=str(current_user.id),
            )
        )

        # 保存报告
        db_report = InvestmentReport(
            user_id=current_user.id,
            title=f"AI深度分析: {request.stock_name or request.sector or '市场分析'}",
            report_type="agent",
            content=response_text,
            summary=response_text[:200],
            stock_codes=[request.stock_code] if request.stock_code else [],
        )
        db.add(db_report)
        await db.commit()

        return {
            "response": response_text,
            "report_id": str(db_report.id),
            "template_id": request.template_id,
        }

    except Exception as e:
        error_msg = str(e)
        print(f"[Agent Analysis Error] {error_msg}\n{traceback.format_exc()}")

        if "ValidationException" in error_msg or "AccessDenied" in error_msg:
            return {
                "error": "LLM模型调用失败，请检查AWS Bedrock模型访问权限",
                "detail": error_msg[:300],
            }
        return {"error": f"分析失败: {error_msg[:300]}"}


@router.get("/reports")
async def get_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InvestmentReport)
        .where(InvestmentReport.user_id == current_user.id)
        .order_by(InvestmentReport.created_at.desc())
        .limit(50)
    )
    reports = result.scalars().all()
    return {"reports": [{
        "id": str(r.id),
        "title": r.title,
        "report_type": r.report_type,
        "summary": r.summary,
        "content": r.content,
        "stock_codes": r.stock_codes,
        "recommendations": r.recommendations,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    } for r in reports]}


@router.post("/web-search")
async def do_web_search(
    request: WebSearchRequest,
    current_user: User = Depends(get_current_user),
):
    results = web_search(request.query, request.max_results)
    return {"results": results}


@router.post("/news")
async def get_financial_news(
    request: WebSearchRequest,
    current_user: User = Depends(get_current_user),
):
    results = search_financial_news(request.query)
    return {"results": results}
