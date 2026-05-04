"""
用户上下文注入 - 将用户自选股等信息注入到Agent提示词中
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import User, Watchlist, WatchlistItem


async def build_user_context(user: User, db: AsyncSession) -> str:
    """构建用户上下文字符串，包含当前日期和自选股列表，注入到Agent提示词中"""
    from datetime import datetime

    parts = [
        f"[当前日期: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}]",
        f"[用户: {user.full_name or user.username}, "
        f"风险偏好: {user.risk_preference}]",
    ]

    # 获取用户默认股票池
    try:
        wl_result = await db.execute(
            select(Watchlist).where(
                Watchlist.user_id == user.id,
                Watchlist.is_default == True,
            ).limit(1)
        )
        default_wl = wl_result.scalar_one_or_none()
        if default_wl:
            items_result = await db.execute(
                select(WatchlistItem).where(WatchlistItem.watchlist_id == default_wl.id)
            )
            items = items_result.scalars().all()
            if items:
                stock_list = ", ".join([f"{i.stock_name}({i.stock_code})" for i in items])
                parts.append(f"[自选股池: {stock_list}]")
    except Exception as e:
        print(f"[UserContext] Failed to get watchlist for {user.username}: {e}")

    return "\n".join(parts)
