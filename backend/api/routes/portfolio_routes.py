"""
模拟盘路由 - 投资组合、持仓、订单管理
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User, Portfolio, Position, Order, OrderSide, OrderStatus
from api.auth import get_current_user
from api.schemas import OrderCreate, PortfolioResponse

router = APIRouter(prefix="/api/portfolio", tags=["模拟盘"])


@router.get("/", response_model=list[PortfolioResponse])
async def get_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户所有投资组合"""
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolios = result.scalars().all()

    responses = []
    for p in portfolios:
        # 获取持仓
        pos_result = await db.execute(
            select(Position).where(Position.portfolio_id == p.id)
        )
        positions = pos_result.scalars().all()

        # 获取最近订单
        order_result = await db.execute(
            select(Order)
            .where(Order.portfolio_id == p.id)
            .order_by(Order.created_at.desc())
            .limit(20)
        )
        orders = order_result.scalars().all()

        responses.append(PortfolioResponse(
            id=str(p.id),
            name=p.name,
            initial_capital=p.initial_capital,
            available_cash=p.available_cash,
            total_value=p.total_value,
            total_profit=p.total_profit,
            total_profit_pct=p.total_profit_pct,
            positions=[{
                "stock_code": pos.stock_code,
                "stock_name": pos.stock_name,
                "quantity": pos.quantity,
                "avg_cost": pos.avg_cost,
                "current_price": pos.current_price,
                "market_value": pos.market_value,
                "profit": pos.profit,
                "profit_pct": pos.profit_pct,
            } for pos in positions],
            recent_orders=[{
                "id": str(o.id),
                "stock_code": o.stock_code,
                "stock_name": o.stock_name,
                "side": o.side.value,
                "price": o.price,
                "quantity": o.quantity,
                "status": o.status.value,
                "created_at": o.created_at.isoformat(),
            } for o in orders],
        ))

    return responses


@router.post("/{portfolio_id}/order")
async def create_order(
    portfolio_id: str,
    order: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建模拟盘交易订单"""
    # 验证组合归属
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="投资组合不存在")

    # 验证订单
    if order.quantity <= 0 or order.quantity % 100 != 0:
        raise HTTPException(status_code=400, detail="委托数量必须是100的整数倍")

    total_amount = order.price * order.quantity

    if order.side == "buy":
        commission = max(total_amount * 0.0003, 5)
        total_cost = total_amount + commission
        if total_cost > portfolio.available_cash:
            raise HTTPException(status_code=400, detail="可用资金不足")

        # 扣减资金
        portfolio.available_cash -= total_cost

        # 更新持仓
        pos_result = await db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.stock_code == order.stock_code,
            )
        )
        position = pos_result.scalar_one_or_none()
        if position:
            total_cost_old = position.avg_cost * position.quantity
            position.quantity += order.quantity
            position.avg_cost = (total_cost_old + total_amount) / position.quantity
        else:
            position = Position(
                portfolio_id=portfolio.id,
                stock_code=order.stock_code,
                stock_name=order.stock_name,
                quantity=order.quantity,
                avg_cost=order.price,
                current_price=order.price,
                market_value=total_amount,
            )
            db.add(position)

    elif order.side == "sell":
        pos_result = await db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.stock_code == order.stock_code,
            )
        )
        position = pos_result.scalar_one_or_none()
        if not position or position.quantity < order.quantity:
            raise HTTPException(status_code=400, detail="持仓不足")

        commission = max(total_amount * 0.0003, 5)
        stamp_tax = total_amount * 0.001
        net_revenue = total_amount - commission - stamp_tax

        portfolio.available_cash += net_revenue
        position.quantity -= order.quantity
        if position.quantity == 0:
            await db.delete(position)
    else:
        raise HTTPException(status_code=400, detail="无效的交易方向")

    # 创建订单记录
    new_order = Order(
        portfolio_id=portfolio.id,
        stock_code=order.stock_code,
        stock_name=order.stock_name,
        side=OrderSide(order.side),
        price=order.price,
        quantity=order.quantity,
        filled_quantity=order.quantity,
        filled_price=order.price,
        status=OrderStatus.FILLED,
    )
    db.add(new_order)

    # 更新组合总值
    pos_result = await db.execute(
        select(Position).where(Position.portfolio_id == portfolio.id)
    )
    all_positions = pos_result.scalars().all()
    total_market_value = sum(p.quantity * p.current_price for p in all_positions)
    portfolio.total_value = portfolio.available_cash + total_market_value
    portfolio.total_profit = portfolio.total_value - portfolio.initial_capital
    portfolio.total_profit_pct = portfolio.total_profit / portfolio.initial_capital * 100

    await db.commit()

    return {
        "order_id": str(new_order.id),
        "status": "filled",
        "message": f"{'买入' if order.side == 'buy' else '卖出'} {order.stock_name} {order.quantity}股 成交价{order.price}",
    }
