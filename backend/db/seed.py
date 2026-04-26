"""
数据库初始化种子数据 - Database Seed Data
包含A股常用股票、预置量化模板、默认用户等
"""
import asyncio
import uuid
from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy import text
from db.database import engine, AsyncSessionLocal, Base
from db.models import (
    User, Stock, MarketType, Watchlist, WatchlistItem,
    Portfolio, QuantStrategy, TradingStrategy, StrategyStatus,
    CustomSkill,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── A股核心股票数据 ──
SEED_STOCKS = [
    # 上证50核心成分股
    {"code": "600519", "name": "贵州茅台", "market": "sh", "industry": "白酒", "sector": "消费"},
    {"code": "601318", "name": "中国平安", "market": "sh", "industry": "保险", "sector": "金融"},
    {"code": "600036", "name": "招商银行", "market": "sh", "industry": "银行", "sector": "金融"},
    {"code": "601166", "name": "兴业银行", "market": "sh", "industry": "银行", "sector": "金融"},
    {"code": "600276", "name": "恒瑞医药", "market": "sh", "industry": "医药", "sector": "医疗"},
    {"code": "600900", "name": "长江电力", "market": "sh", "industry": "电力", "sector": "公用事业"},
    {"code": "601888", "name": "中国中免", "market": "sh", "industry": "旅游", "sector": "消费"},
    {"code": "600309", "name": "万华化学", "market": "sh", "industry": "化工", "sector": "材料"},
    {"code": "603259", "name": "药明康德", "market": "sh", "industry": "CXO", "sector": "医疗"},
    {"code": "600030", "name": "中信证券", "market": "sh", "industry": "证券", "sector": "金融"},
    {"code": "601012", "name": "隆基绿能", "market": "sh", "industry": "光伏", "sector": "新能源"},
    {"code": "600887", "name": "伊利股份", "market": "sh", "industry": "乳制品", "sector": "消费"},
    {"code": "601398", "name": "工商银行", "market": "sh", "industry": "银行", "sector": "金融"},
    {"code": "600000", "name": "浦发银行", "market": "sh", "industry": "银行", "sector": "金融"},
    {"code": "600048", "name": "保利发展", "market": "sh", "industry": "房地产", "sector": "地产"},
    # 深证核心股票
    {"code": "000858", "name": "五粮液", "market": "sz", "industry": "白酒", "sector": "消费"},
    {"code": "000333", "name": "美的集团", "market": "sz", "industry": "家电", "sector": "消费"},
    {"code": "000001", "name": "平安银行", "market": "sz", "industry": "银行", "sector": "金融"},
    {"code": "002714", "name": "牧原股份", "market": "sz", "industry": "养殖", "sector": "农业"},
    {"code": "000651", "name": "格力电器", "market": "sz", "industry": "家电", "sector": "消费"},
    {"code": "002475", "name": "立讯精密", "market": "sz", "industry": "电子", "sector": "科技"},
    {"code": "300750", "name": "宁德时代", "market": "sz", "industry": "电池", "sector": "新能源"},
    {"code": "300059", "name": "东方财富", "market": "sz", "industry": "互联网金融", "sector": "金融"},
    {"code": "002594", "name": "比亚迪", "market": "sz", "industry": "汽车", "sector": "新能源"},
    {"code": "000568", "name": "泸州老窖", "market": "sz", "industry": "白酒", "sector": "消费"},
    {"code": "002304", "name": "洋河股份", "market": "sz", "industry": "白酒", "sector": "消费"},
    {"code": "300760", "name": "迈瑞医疗", "market": "sz", "industry": "医疗器械", "sector": "医疗"},
    {"code": "002415", "name": "海康威视", "market": "sz", "industry": "安防", "sector": "科技"},
    {"code": "000725", "name": "京东方A", "market": "sz", "industry": "面板", "sector": "科技"},
    {"code": "002230", "name": "科大讯飞", "market": "sz", "industry": "人工智能", "sector": "科技"},
]


# ── 预置量化策略模板 (参考幻方量化风格) ──
QUANT_TEMPLATES = [
    {
        "name": "双均线交叉策略",
        "description": "经典双均线交叉策略，短期均线上穿长期均线买入，下穿卖出。适合趋势行情。",
        "template_name": "dual_ma_cross",
        "parameters": {
            "short_period": 5,
            "long_period": 20,
            "position_size": 0.3,
            "stop_loss_pct": 0.05,
        },
        "code": """
# 双均线交叉策略 - Dual Moving Average Crossover
import pandas as pd
import numpy as np

def initialize(context):
    context.short_period = params.get('short_period', 5)
    context.long_period = params.get('long_period', 20)
    context.position_size = params.get('position_size', 0.3)
    context.stop_loss_pct = params.get('stop_loss_pct', 0.05)

def handle_data(context, data):
    close = data['close']
    short_ma = close.rolling(context.short_period).mean()
    long_ma = close.rolling(context.long_period).mean()

    if short_ma.iloc[-1] > long_ma.iloc[-1] and short_ma.iloc[-2] <= long_ma.iloc[-2]:
        return {'signal': 'buy', 'weight': context.position_size}
    elif short_ma.iloc[-1] < long_ma.iloc[-1] and short_ma.iloc[-2] >= long_ma.iloc[-2]:
        return {'signal': 'sell', 'weight': 1.0}
    return {'signal': 'hold'}
""",
    },
    {
        "name": "MACD动量策略",
        "description": "基于MACD指标的动量策略，结合MACD金叉死叉和柱状图变化判断买卖时机。",
        "template_name": "macd_momentum",
        "parameters": {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "position_size": 0.25,
        },
        "code": """
# MACD动量策略 - MACD Momentum Strategy
import pandas as pd
import numpy as np

def initialize(context):
    context.fast = params.get('fast_period', 12)
    context.slow = params.get('slow_period', 26)
    context.signal = params.get('signal_period', 9)
    context.position_size = params.get('position_size', 0.25)

def handle_data(context, data):
    close = data['close']
    ema_fast = close.ewm(span=context.fast).mean()
    ema_slow = close.ewm(span=context.slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=context.signal).mean()
    histogram = macd_line - signal_line

    if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:
        if histogram.iloc[-1] > 0:
            return {'signal': 'buy', 'weight': context.position_size}
    elif macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]:
        return {'signal': 'sell', 'weight': 1.0}
    return {'signal': 'hold'}
""",
    },
    {
        "name": "布林带突破策略",
        "description": "基于布林带的均值回归策略，价格触及下轨买入，触及上轨卖出。适合震荡行情。",
        "template_name": "bollinger_breakout",
        "parameters": {
            "period": 20,
            "num_std": 2.0,
            "position_size": 0.2,
        },
        "code": """
# 布林带突破策略 - Bollinger Bands Breakout
import pandas as pd
import numpy as np

def initialize(context):
    context.period = params.get('period', 20)
    context.num_std = params.get('num_std', 2.0)
    context.position_size = params.get('position_size', 0.2)

def handle_data(context, data):
    close = data['close']
    ma = close.rolling(context.period).mean()
    std = close.rolling(context.period).std()
    upper = ma + context.num_std * std
    lower = ma - context.num_std * std
    current = close.iloc[-1]

    if current <= lower.iloc[-1]:
        return {'signal': 'buy', 'weight': context.position_size}
    elif current >= upper.iloc[-1]:
        return {'signal': 'sell', 'weight': 1.0}
    return {'signal': 'hold'}
""",
    },
    {
        "name": "RSI超买超卖策略",
        "description": "基于RSI指标的超买超卖策略，RSI低于30买入，高于70卖出。",
        "template_name": "rsi_overbought_oversold",
        "parameters": {
            "rsi_period": 14,
            "oversold": 30,
            "overbought": 70,
            "position_size": 0.25,
        },
        "code": """
# RSI超买超卖策略 - RSI Overbought/Oversold
import pandas as pd
import numpy as np

def initialize(context):
    context.period = params.get('rsi_period', 14)
    context.oversold = params.get('oversold', 30)
    context.overbought = params.get('overbought', 70)
    context.position_size = params.get('position_size', 0.25)

def compute_rsi(series, period):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def handle_data(context, data):
    close = data['close']
    rsi = compute_rsi(close, context.period)
    current_rsi = rsi.iloc[-1]

    if current_rsi < context.oversold:
        return {'signal': 'buy', 'weight': context.position_size}
    elif current_rsi > context.overbought:
        return {'signal': 'sell', 'weight': 1.0}
    return {'signal': 'hold'}
""",
    },
    {
        "name": "多因子选股策略",
        "description": "参考幻方量化多因子模型，综合市值、估值、动量、质量等因子进行选股和权重分配。",
        "template_name": "multi_factor",
        "parameters": {
            "factors": ["pe_ratio", "pb_ratio", "roe", "momentum_20d", "volatility_20d"],
            "factor_weights": {"pe_ratio": -0.2, "pb_ratio": -0.15, "roe": 0.3, "momentum_20d": 0.2, "volatility_20d": -0.15},
            "top_n": 10,
            "rebalance_days": 20,
        },
        "code": """
# 多因子选股策略 - Multi-Factor Stock Selection (幻方量化风格)
import pandas as pd
import numpy as np

def initialize(context):
    context.factors = params.get('factors', [])
    context.weights = params.get('factor_weights', {})
    context.top_n = params.get('top_n', 10)
    context.rebalance_days = params.get('rebalance_days', 20)
    context.day_count = 0

def compute_factor_scores(data, factors, weights):
    scores = pd.DataFrame(index=data.index)
    for factor in factors:
        if factor in data.columns:
            ranked = data[factor].rank(pct=True)
            scores[factor] = ranked * weights.get(factor, 0)
    return scores.sum(axis=1)

def handle_data(context, data):
    context.day_count += 1
    if context.day_count % context.rebalance_days != 0:
        return {'signal': 'hold'}

    composite = compute_factor_scores(data, context.factors, context.weights)
    top_stocks = composite.nlargest(context.top_n)
    weights = top_stocks / top_stocks.sum()

    return {
        'signal': 'rebalance',
        'target_weights': weights.to_dict(),
    }
""",
    },
    {
        "name": "海龟交易策略",
        "description": "经典海龟交易法则，基于唐奇安通道突破，结合ATR进行仓位管理和止损。",
        "template_name": "turtle_trading",
        "parameters": {
            "entry_period": 20,
            "exit_period": 10,
            "atr_period": 20,
            "risk_per_trade": 0.01,
        },
        "code": """
# 海龟交易策略 - Turtle Trading System
import pandas as pd
import numpy as np

def initialize(context):
    context.entry_period = params.get('entry_period', 20)
    context.exit_period = params.get('exit_period', 10)
    context.atr_period = params.get('atr_period', 20)
    context.risk_per_trade = params.get('risk_per_trade', 0.01)

def compute_atr(high, low, close, period):
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def handle_data(context, data):
    high = data['high']
    low = data['low']
    close = data['close']

    entry_high = high.rolling(context.entry_period).max()
    exit_low = low.rolling(context.exit_period).min()
    atr = compute_atr(high, low, close, context.atr_period)

    current = close.iloc[-1]
    current_atr = atr.iloc[-1]

    if current > entry_high.iloc[-2]:
        unit_size = (context.risk_per_trade * 1000000) / (current_atr * 100)
        return {'signal': 'buy', 'quantity': int(unit_size) * 100, 'stop_loss': current - 2 * current_atr}
    elif current < exit_low.iloc[-2]:
        return {'signal': 'sell', 'weight': 1.0}
    return {'signal': 'hold'}
""",
    },
]


async def seed_database():
    """初始化数据库并写入种子数据"""
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 检查是否已有数据
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        if count and count > 0:
            print("数据库已有数据，跳过种子数据初始化")
            return

        print("开始初始化种子数据...")

        # 1. 创建默认用户
        demo_user = User(
            id=uuid.uuid4(),
            username="demo",
            email="demo@securities-trading.com",
            hashed_password=pwd_context.hash("demo123456"),
            full_name="演示用户",
            risk_preference="moderate",
            notification_email=True,
            notification_push=True,
        )
        session.add(demo_user)

        admin_user = User(
            id=uuid.uuid4(),
            username="admin",
            email="admin@securities-trading.com",
            hashed_password=pwd_context.hash("admin123456"),
            full_name="管理员",
            risk_preference="moderate",
        )
        session.add(admin_user)

        # 2. 写入股票基础数据
        for s in SEED_STOCKS:
            stock = Stock(
                code=s["code"],
                name=s["name"],
                market=MarketType(s["market"]),
                industry=s["industry"],
                sector=s["sector"],
            )
            session.add(stock)

        # 3. 创建默认股票池
        default_watchlist = Watchlist(
            user_id=demo_user.id,
            name="核心股票池",
            description="投资分析Agent推荐的核心股票池",
            is_default=True,
        )
        session.add(default_watchlist)
        await session.flush()

        # 添加默认股票池中的股票
        default_pool_codes = [
            ("600519", "贵州茅台", "白酒龙头，品牌护城河深厚"),
            ("300750", "宁德时代", "动力电池全球龙头"),
            ("000858", "五粮液", "高端白酒第二品牌"),
            ("601318", "中国平安", "综合金融龙头"),
            ("002594", "比亚迪", "新能源汽车龙头"),
        ]
        for code, name, reason in default_pool_codes:
            item = WatchlistItem(
                watchlist_id=default_watchlist.id,
                stock_code=code,
                stock_name=name,
                added_reason=reason,
            )
            session.add(item)

        # 4. 创建模拟盘
        portfolio = Portfolio(
            user_id=demo_user.id,
            name="默认模拟盘",
            initial_capital=1000000.0,
            available_cash=1000000.0,
            total_value=1000000.0,
        )
        session.add(portfolio)

        # 5. 写入预置量化策略模板
        for tmpl in QUANT_TEMPLATES:
            qs = QuantStrategy(
                user_id=demo_user.id,
                name=tmpl["name"],
                description=tmpl["description"],
                template_name=tmpl["template_name"],
                code=tmpl["code"],
                parameters=tmpl["parameters"],
                status=StrategyStatus.DRAFT,
            )
            session.add(qs)

        # 6. 创建默认交易策略
        default_strategy = TradingStrategy(
            user_id=demo_user.id,
            name="均线+MACD综合策略",
            description="结合均线趋势和MACD动量的综合交易策略",
            strategy_type="technical",
            parameters={
                "ma_short": 5,
                "ma_long": 20,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
            },
            indicators=["MA", "MACD", "RSI", "BOLL"],
            buy_conditions=[
                "短期均线上穿长期均线",
                "MACD金叉且柱状图为正",
                "RSI在30-50区间",
            ],
            sell_conditions=[
                "短期均线下穿长期均线",
                "MACD死叉",
                "RSI超过70",
                "止损线触发(-5%)",
            ],
            risk_rules={
                "max_position_pct": 0.3,
                "stop_loss_pct": 0.05,
                "take_profit_pct": 0.15,
                "max_daily_loss_pct": 0.03,
            },
            status=StrategyStatus.ACTIVE,
        )
        session.add(default_strategy)

        await session.commit()
        print("✅ 种子数据初始化完成!")
        print(f"   - 用户: 2 (demo/demo123456, admin/admin123456)")
        print(f"   - 股票: {len(SEED_STOCKS)}")
        print(f"   - 量化模板: {len(QUANT_TEMPLATES)}")
        print(f"   - 默认股票池: 1 (含{len(default_pool_codes)}只股票)")
        print(f"   - 模拟盘: 1 (初始资金100万)")


if __name__ == "__main__":
    asyncio.run(seed_database())
