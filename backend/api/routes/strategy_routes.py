"""
策略路由 - 交易策略和量化策略管理
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User, TradingStrategy, QuantStrategy, Backtest, StrategyStatus, BacktestStatus
from api.auth import get_current_user
from api.schemas import (
    StrategyCreate, StrategyResponse,
    QuantStrategyCreate, BacktestRequest, BacktestResponse,
)
from agents.skills.quant_skill import run_backtest, list_quant_templates
from agents.skills.market_data_skill import get_stock_kline

router = APIRouter(prefix="/api/strategy", tags=["交易策略"])


# ── 交易策略 ──
@router.get("/trading", response_model=list[StrategyResponse])
async def get_trading_strategies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TradingStrategy).where(TradingStrategy.user_id == current_user.id)
    )
    strategies = result.scalars().all()
    return [StrategyResponse(
        id=str(s.id), name=s.name, description=s.description,
        strategy_type=s.strategy_type, parameters=s.parameters or {},
        indicators=s.indicators or [], buy_conditions=s.buy_conditions or [],
        sell_conditions=s.sell_conditions or [], risk_rules=s.risk_rules or {},
        status=s.status.value,
    ) for s in strategies]


@router.post("/trading", response_model=StrategyResponse)
async def create_trading_strategy(
    strategy: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_strategy = TradingStrategy(
        user_id=current_user.id,
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type,
        parameters=strategy.parameters,
        indicators=strategy.indicators,
        buy_conditions=strategy.buy_conditions,
        sell_conditions=strategy.sell_conditions,
        risk_rules=strategy.risk_rules,
        status=StrategyStatus.DRAFT,
    )
    db.add(new_strategy)
    await db.commit()
    await db.refresh(new_strategy)

    return StrategyResponse(
        id=str(new_strategy.id), name=new_strategy.name,
        description=new_strategy.description, strategy_type=new_strategy.strategy_type,
        parameters=new_strategy.parameters or {}, indicators=new_strategy.indicators or [],
        buy_conditions=new_strategy.buy_conditions or [],
        sell_conditions=new_strategy.sell_conditions or [],
        risk_rules=new_strategy.risk_rules or {}, status=new_strategy.status.value,
    )


@router.put("/trading/{strategy_id}", response_model=StrategyResponse)
async def update_trading_strategy(
    strategy_id: str,
    strategy: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TradingStrategy).where(
            TradingStrategy.id == strategy_id,
            TradingStrategy.user_id == current_user.id,
        )
    )
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="策略不存在")

    existing.name = strategy.name
    existing.description = strategy.description
    existing.strategy_type = strategy.strategy_type
    existing.parameters = strategy.parameters
    existing.indicators = strategy.indicators
    existing.buy_conditions = strategy.buy_conditions
    existing.sell_conditions = strategy.sell_conditions
    existing.risk_rules = strategy.risk_rules

    await db.commit()
    await db.refresh(existing)

    return StrategyResponse(
        id=str(existing.id), name=existing.name,
        description=existing.description, strategy_type=existing.strategy_type,
        parameters=existing.parameters or {}, indicators=existing.indicators or [],
        buy_conditions=existing.buy_conditions or [],
        sell_conditions=existing.sell_conditions or [],
        risk_rules=existing.risk_rules or {}, status=existing.status.value,
    )


# ── 量化策略 ──
@router.get("/quant/templates")
async def get_quant_templates():
    """获取预置量化策略模板"""
    return {"templates": list_quant_templates()}


@router.get("/quant")
async def get_quant_strategies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuantStrategy).where(QuantStrategy.user_id == current_user.id)
    )
    strategies = result.scalars().all()
    return {"strategies": [{
        "id": str(s.id), "name": s.name, "description": s.description,
        "template_name": s.template_name, "parameters": s.parameters,
        "status": s.status.value, "performance_metrics": s.performance_metrics,
        "code": s.code,
    } for s in strategies]}


@router.post("/quant")
async def create_quant_strategy(
    strategy: QuantStrategyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_strategy = QuantStrategy(
        user_id=current_user.id,
        name=strategy.name,
        description=strategy.description,
        template_name=strategy.template_name,
        code=strategy.code,
        parameters=strategy.parameters,
        status=StrategyStatus.DRAFT,
    )
    db.add(new_strategy)
    await db.commit()
    await db.refresh(new_strategy)

    return {
        "id": str(new_strategy.id),
        "name": new_strategy.name,
        "status": "created",
    }


@router.post("/quant/backtest")
async def run_strategy_backtest(
    request: BacktestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """运行量化策略回测"""
    # 获取策略
    result = await db.execute(
        select(QuantStrategy).where(
            QuantStrategy.id == request.strategy_id,
            QuantStrategy.user_id == current_user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="量化策略不存在")

    # 运行回测 — use strategy template_name to match the @tool function signature
    backtest_result = run_backtest(
        stock_code=request.stock_code,
        strategy_name=strategy.template_name or "dual_ma_cross",
        strategy_params=strategy.parameters or {},
        initial_capital=request.initial_capital,
        period_days=250,
    )

    if "error" in backtest_result:
        raise HTTPException(status_code=400, detail=backtest_result["error"])

    # 保存回测记录
    from datetime import datetime
    trade_log = backtest_result.get("trade_log", [])
    backtest = Backtest(
        strategy_id=strategy.id,
        start_date=datetime.strptime(trade_log[0]["date"], "%Y-%m-%d") if trade_log else datetime.now(),
        end_date=datetime.strptime(trade_log[-1]["date"], "%Y-%m-%d") if trade_log else datetime.now(),
        initial_capital=request.initial_capital,
        final_value=backtest_result.get("final_value", 0),
        total_return=backtest_result.get("total_return", 0),
        annual_return=backtest_result.get("annual_return", 0),
        max_drawdown=backtest_result.get("max_drawdown", 0),
        sharpe_ratio=backtest_result.get("sharpe_ratio", 0),
        win_rate=backtest_result.get("win_rate", 0),
        total_trades=backtest_result.get("total_trades", 0),
        trade_log=backtest_result.get("trade_log", []),
        equity_curve=backtest_result.get("equity_curve_sample", []),
        status=BacktestStatus.COMPLETED,
        completed_at=datetime.now(),
    )
    db.add(backtest)

    # 更新策略绩效指标
    strategy.performance_metrics = {
        "total_return": backtest_result.get("total_return", 0),
        "annual_return": backtest_result.get("annual_return", 0),
        "max_drawdown": backtest_result.get("max_drawdown", 0),
        "sharpe_ratio": backtest_result.get("sharpe_ratio", 0),
        "win_rate": backtest_result.get("win_rate", 0),
    }

    await db.commit()

    return backtest_result


# ═══════════════════════════════════════════════════════
# AI Agent 策略助手 (通过Runtime + Registry Smart Select)
# ═══════════════════════════════════════════════════════

from pydantic import BaseModel as _BaseModel


class AgentStrategyRequest(_BaseModel):
    prompt: str
    module: str = "trading"  # trading or quant


@router.post("/agent")
async def agent_strategy(
    request: AgentStrategyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI策略助手 - 通过AgentCore Runtime + Registry Smart Select"""
    import asyncio
    import json as _json
    import uuid
    import traceback
    from fastapi.responses import StreamingResponse
    from config.settings import get_settings
    from db.database import AsyncSessionLocal

    _settings = get_settings()

    # Registry Smart Select
    registry_context = ""
    registry_id = _settings.AGENTCORE_REGISTRY_ID
    if registry_id:
        try:
            import boto3
            client = boto3.client("bedrock-agentcore", region_name=_settings.AWS_REGION)
            registry_arn = f"arn:aws:bedrock-agentcore:{_settings.AWS_REGION}:632930644527:registry/{registry_id}"
            resp = client.search_registry_records(
                registryIds=[registry_arn], searchQuery=request.prompt[:200], maxResults=5,
            )
            records = resp.get("registryRecords", [])
            if records:
                lines = ["\n[Registry Smart Select - 相关Skills:]"]
                for rec in records:
                    lines.append(f"- {rec.get('name', '')}: {rec.get('description', '')[:100]}")
                registry_context = "\n".join(lines)
        except Exception:
            pass

    # Build context with user's watchlist
    skill_hint = "trading-skill, market-data-skill, notification-skill" if request.module == "trading" else "quant-skill, market-data-skill, code-interpreter-skill"
    try:
        from api.user_context import build_user_context
        user_ctx = await build_user_context(current_user, db)
        context = (
            f"{user_ctx}\n"
            f"[模块: {'交易策略' if request.module == 'trading' else '量化交易'}]\n"
            f"[推荐Skills: {skill_hint}]\n\n"
            f"{request.prompt}{registry_context}"
        )
    except Exception:
        context = (
            f"[用户: {current_user.full_name or current_user.username}, "
            f"风险偏好: {current_user.risk_preference}]\n"
            f"[模块: {'交易策略' if request.module == 'trading' else '量化交易'}]\n"
            f"[推荐Skills: {skill_hint}]\n\n"
            f"{request.prompt}{registry_context}"
        )

    user_id = current_user.id

    async def generate():
        yield f"data: {_json.dumps({'type': 'ping', 'elapsed': 0})}\n\n"
        loop = asyncio.get_event_loop()
        from agents.runtime_client import invoke_runtime_agent
        future = loop.run_in_executor(
            None,
            lambda: invoke_runtime_agent(
                prompt=context,
                session_id=f"{request.module}-{user_id}-{uuid.uuid4().hex[:8]}",
                user_id=str(user_id),
            )
        )
        elapsed = 0
        while not future.done():
            try:
                await asyncio.wait_for(asyncio.shield(future), timeout=10)
                break
            except asyncio.TimeoutError:
                elapsed += 10
                yield f"data: {_json.dumps({'type': 'ping', 'elapsed': elapsed})}\n\n"

        try:
            response_text = await future
        except Exception as e:
            response_text = f"Agent错误: {str(e)[:300]}"

        # Auto-save to documents
        try:
            from db.database import AsyncSessionLocal
            from db.models import Document
            async with AsyncSessionLocal() as save_db:
                doc = Document(
                    user_id=user_id,
                    title=f"[{'交易策略' if request.module == 'trading' else '量化分析'}] {request.prompt[:60]}",
                    category="strategy" if request.module == "trading" else "quant",
                    content=response_text,
                    file_type="md",
                    file_size=len(response_text.encode("utf-8")),
                    tags=[request.module],
                    source="agent",
                )
                save_db.add(doc)
                await save_db.commit()
        except Exception:
            pass

        result = _json.dumps({"type": "result", "response": response_text}, ensure_ascii=False)
        yield f"data: {result}\n\n"

    return StreamingResponse(
        generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
