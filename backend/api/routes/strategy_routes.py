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

    # 获取K线数据
    kline_result = get_stock_kline(request.stock_code, "day", 250)
    if "error" in kline_result:
        raise HTTPException(status_code=400, detail=kline_result["error"])

    kline_data = kline_result.get("data", [])

    # 运行回测
    backtest_result = run_backtest(
        strategy_code=strategy.code,
        strategy_params=strategy.parameters,
        kline_data=kline_data,
        initial_capital=request.initial_capital,
    )

    if "error" in backtest_result:
        raise HTTPException(status_code=400, detail=backtest_result["error"])

    # 保存回测记录
    from datetime import datetime
    backtest = Backtest(
        strategy_id=strategy.id,
        start_date=datetime.strptime(kline_data[0]["date"], "%Y-%m-%d") if kline_data else datetime.now(),
        end_date=datetime.strptime(kline_data[-1]["date"], "%Y-%m-%d") if kline_data else datetime.now(),
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
