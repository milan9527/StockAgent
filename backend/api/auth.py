"""
认证模块 - 支持本地DB认证和Amazon Cognito
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from db.models import User
from config.settings import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def authenticate_cognito(username: str, password: str) -> dict:
    """Authenticate via Amazon Cognito"""
    import boto3
    client = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)

    try:
        response = client.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )

        # Handle NEW_PASSWORD_REQUIRED challenge
        if response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            # Auto-respond with the same password for first login
            challenge_response = client.respond_to_auth_challenge(
                ClientId=settings.COGNITO_CLIENT_ID,
                ChallengeName="NEW_PASSWORD_REQUIRED",
                Session=response["Session"],
                ChallengeResponses={"USERNAME": username, "NEW_PASSWORD": password},
            )
            return {
                "success": True,
                "id_token": challenge_response["AuthenticationResult"]["IdToken"],
                "access_token": challenge_response["AuthenticationResult"]["AccessToken"],
            }

        return {
            "success": True,
            "id_token": response["AuthenticationResult"]["IdToken"],
            "access_token": response["AuthenticationResult"]["AccessToken"],
        }
    except client.exceptions.NotAuthorizedException:
        return {"success": False, "error": "用户名或密码错误"}
    except client.exceptions.UserNotFoundException:
        return {"success": False, "error": "用户不存在"}
    except client.exceptions.InvalidPasswordException as e:
        return {"success": False, "error": f"密码不符合要求: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def authenticate_user(username: str, password: str, db: AsyncSession) -> tuple[bool, str, Optional[User]]:
    """Authenticate user - try Cognito first, fallback to local DB"""

    # Try Cognito if configured
    if settings.COGNITO_USER_POOL_ID and settings.COGNITO_CLIENT_ID:
        cognito_result = authenticate_cognito(username, password)
        if cognito_result["success"]:
            # Ensure user exists in local DB (sync from Cognito)
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            if not user:
                # Extract email from Cognito ID token if available
                email = f"{username}@cognito.local"
                try:
                    id_token = cognito_result.get("id_token", "")
                    if id_token:
                        claims = jwt.get_unverified_claims(id_token)
                        email = claims.get("email", email)
                except Exception:
                    pass
                user = User(
                    username=username,
                    email=email,
                    hashed_password=get_password_hash(password),
                    full_name=username,
                    risk_preference="moderate",
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                # Seed default data for new Cognito user
                await _seed_new_user_data(user, db)
            else:
                # User exists but may not have seed data (created before seed code was deployed)
                await _ensure_user_has_seed_data(user, db)
            return True, "", user
        # If Cognito auth fails, don't fallback — return the error
        return False, cognito_result.get("error", "认证失败"), None

    # Local DB auth (when Cognito not configured)
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return False, "用户名或密码错误", None
    return True, "", user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


def cognito_signup(username: str, password: str, email: str) -> dict:
    """Register a new user in Cognito"""
    if not settings.COGNITO_USER_POOL_ID or not settings.COGNITO_CLIENT_ID:
        return {"success": False, "error": "Cognito未配置"}
    try:
        import boto3
        client = boto3.client("cognito-idp", region_name=settings.COGNITO_REGION)
        client.sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=username,
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email},
            ],
        )
        # Auto-confirm for development (admin confirm)
        try:
            client.admin_confirm_sign_up(
                UserPoolId=settings.COGNITO_USER_POOL_ID,
                Username=username,
            )
        except Exception:
            pass  # May need email verification in production
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _seed_new_user_data(user, db):
    """为新用户创建默认数据: 股票池、模拟盘、定期任务、量化策略、交易策略"""
    from db.models import (
        Watchlist, WatchlistItem, Portfolio, ScheduledTask,
        QuantStrategy, TradingStrategy, StrategyStatus,
    )

    try:
        # 默认股票池
        watchlist = Watchlist(
            user_id=user.id,
            name="核心股票池",
            description="投资分析Agent推荐的核心股票池",
            is_default=True,
        )
        db.add(watchlist)
        await db.flush()

        for code, name, reason in [
            ("600519", "贵州茅台", "白酒龙头，品牌护城河深厚"),
            ("300750", "宁德时代", "动力电池全球龙头"),
            ("000858", "五粮液", "高端白酒第二品牌"),
            ("601318", "中国平安", "综合金融龙头"),
            ("002594", "比亚迪", "新能源汽车龙头"),
        ]:
            db.add(WatchlistItem(
                watchlist_id=watchlist.id, stock_code=code,
                stock_name=name, added_reason=reason,
            ))

        # 模拟盘
        db.add(Portfolio(
            user_id=user.id, name="默认模拟盘",
            initial_capital=1000000.0, available_cash=1000000.0, total_value=1000000.0,
        ))

        # 预置量化策略 (用于回测)
        QUANT_STRATEGIES = [
            {
                "name": "双均线交叉策略",
                "description": "经典双均线交叉策略，短期均线上穿长期均线买入，下穿卖出",
                "template_name": "dual_ma_cross",
                "parameters": {"short_period": 5, "long_period": 20, "position_size": 0.3, "stop_loss_pct": 0.05},
                "code": "import pandas as pd\nimport numpy as np\n\ndef initialize(context):\n    context.short_period = params.get('short_period', 5)\n    context.long_period = params.get('long_period', 20)\n    context.position_size = params.get('position_size', 0.3)\n\ndef handle_data(context, data):\n    close = data['close']\n    short_ma = close.rolling(context.short_period).mean()\n    long_ma = close.rolling(context.long_period).mean()\n    if short_ma.iloc[-1] > long_ma.iloc[-1] and short_ma.iloc[-2] <= long_ma.iloc[-2]:\n        return {'signal': 'buy', 'weight': context.position_size}\n    elif short_ma.iloc[-1] < long_ma.iloc[-1] and short_ma.iloc[-2] >= long_ma.iloc[-2]:\n        return {'signal': 'sell', 'weight': 1.0}\n    return {'signal': 'hold'}\n",
            },
            {
                "name": "MACD动量策略",
                "description": "基于MACD指标的动量策略，MACD金叉买入，死叉卖出",
                "template_name": "macd_momentum",
                "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9, "position_size": 0.25},
                "code": "import pandas as pd\nimport numpy as np\n\ndef initialize(context):\n    context.fast = params.get('fast_period', 12)\n    context.slow = params.get('slow_period', 26)\n    context.signal = params.get('signal_period', 9)\n    context.position_size = params.get('position_size', 0.25)\n\ndef handle_data(context, data):\n    close = data['close']\n    ema_fast = close.ewm(span=context.fast).mean()\n    ema_slow = close.ewm(span=context.slow).mean()\n    macd_line = ema_fast - ema_slow\n    signal_line = macd_line.ewm(span=context.signal).mean()\n    if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:\n        return {'signal': 'buy', 'weight': context.position_size}\n    elif macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]:\n        return {'signal': 'sell', 'weight': 1.0}\n    return {'signal': 'hold'}\n",
            },
            {
                "name": "RSI超买超卖策略",
                "description": "RSI低于30买入，高于70卖出",
                "template_name": "rsi_overbought_oversold",
                "parameters": {"rsi_period": 14, "oversold": 30, "overbought": 70, "position_size": 0.25},
                "code": "import pandas as pd\nimport numpy as np\n\ndef initialize(context):\n    context.period = params.get('rsi_period', 14)\n    context.oversold = params.get('oversold', 30)\n    context.overbought = params.get('overbought', 70)\n    context.position_size = params.get('position_size', 0.25)\n\ndef compute_rsi(series, period):\n    delta = series.diff()\n    gain = delta.where(delta > 0, 0).rolling(period).mean()\n    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()\n    rs = gain / loss\n    return 100 - (100 / (1 + rs))\n\ndef handle_data(context, data):\n    close = data['close']\n    rsi = compute_rsi(close, context.period)\n    if rsi.iloc[-1] < context.oversold:\n        return {'signal': 'buy', 'weight': context.position_size}\n    elif rsi.iloc[-1] > context.overbought:\n        return {'signal': 'sell', 'weight': 1.0}\n    return {'signal': 'hold'}\n",
            },
            {
                "name": "布林带突破策略",
                "description": "价格触及下轨买入，触及上轨卖出",
                "template_name": "bollinger_breakout",
                "parameters": {"period": 20, "num_std": 2.0, "position_size": 0.2},
                "code": "import pandas as pd\nimport numpy as np\n\ndef initialize(context):\n    context.period = params.get('period', 20)\n    context.num_std = params.get('num_std', 2.0)\n    context.position_size = params.get('position_size', 0.2)\n\ndef handle_data(context, data):\n    close = data['close']\n    ma = close.rolling(context.period).mean()\n    std = close.rolling(context.period).std()\n    upper = ma + context.num_std * std\n    lower = ma - context.num_std * std\n    current = close.iloc[-1]\n    if current <= lower.iloc[-1]:\n        return {'signal': 'buy', 'weight': context.position_size}\n    elif current >= upper.iloc[-1]:\n        return {'signal': 'sell', 'weight': 1.0}\n    return {'signal': 'hold'}\n",
            },
        ]
        for qs in QUANT_STRATEGIES:
            db.add(QuantStrategy(
                user_id=user.id, name=qs["name"], description=qs["description"],
                template_name=qs["template_name"], code=qs["code"],
                parameters=qs["parameters"], status=StrategyStatus.DRAFT,
            ))

        # 默认交易策略
        db.add(TradingStrategy(
            user_id=user.id,
            name="均线+MACD综合策略",
            description="结合均线趋势和MACD动量的综合交易策略",
            strategy_type="technical",
            parameters={"ma_short": 5, "ma_long": 20},
            indicators=["MA", "MACD", "RSI", "BOLL"],
            buy_conditions=["短期均线上穿长期均线", "MACD金叉且柱状图为正", "RSI在30-50区间"],
            sell_conditions=["短期均线下穿长期均线", "MACD死叉", "RSI超过70", "止损线触发(-5%)"],
            risk_rules={"max_position_pct": 0.3, "stop_loss_pct": 0.05, "take_profit_pct": 0.15},
            status=StrategyStatus.ACTIVE,
        ))

        # 预置定期任务
        SEED_TASKS = [
            {"name": "每日走势预测", "description": "每个工作日14:30, 预测自选股和大盘明日走势",
             "prompt": "分析自选股池中所有股票和大盘的当前走势, 结合技术指标、资金流向和市场情绪, 预测明日走势方向和可能的涨跌幅区间。请在回复末尾添加 [预测记录] 标签。",
             "cron_expression": "cron(30 6 ? * MON-FRI *)"},
            {"name": "每周预测验证与自我改进", "description": "每周一9:00, 验证上周预测结果, 分析预测准确率, 自我改进",
             "prompt": "回顾上周的所有预测记录, 对比实际走势验证预测准确率。分析成功和失败原因, 总结经验教训, 提出改进方向。",
             "cron_expression": "cron(0 1 ? * MON *)"},
            {"name": "每日A股市场分析", "description": "每个工作日北京时间15点, 全面分析A股市场",
             "prompt": "全面分析今日A股市场走势, 包括指数表现、热点板块和资金流向, 结合技术指标分析趋势, 给出操作建议。",
             "cron_expression": "cron(0 7 ? * MON-FRI *)"},
            {"name": "每周买卖信号检查", "description": "每周一早上9点, 检查自选股池中所有股票的买卖信号",
             "prompt": "检查自选股池中所有股票的技术指标和买卖信号, 标记达到买入或卖出条件的股票, 生成信号报告。",
             "cron_expression": "cron(0 1 ? * MON *)"},
            {"name": "每日收盘绩效报告", "description": "每天收盘后16点, 生成今日投资组合绩效报告",
             "prompt": "生成今日投资组合绩效报告, 包括持仓盈亏、收益率, 分析表现最好和最差的持仓, 给出调仓建议。",
             "cron_expression": "cron(0 8 ? * MON-FRI *)"},
            {"name": "每周市场周报", "description": "每周五下午3点, 搜索本周A股市场重大新闻和政策变化, 生成周报",
             "prompt": "搜索本周A股市场重大新闻和政策变化, 分析对市场的影响, 总结本周市场表现, 展望下周走势。",
             "cron_expression": "cron(0 7 ? * FRI *)"},
        ]
        for st in SEED_TASKS:
            db.add(ScheduledTask(
                user_id=user.id, name=st["name"], description=st["description"],
                prompt=st["prompt"], cron_expression=st["cron_expression"],
                timezone="Asia/Shanghai", agent_type="orchestrator",
                notification_email=user.email or "", is_active=True,
            ))

        await db.commit()
        print(f"[Auth] Seeded default data for new user: {user.username}")
    except Exception as e:
        print(f"[Auth] Failed to seed data for {user.username}: {e}")
        try:
            await db.rollback()
        except Exception:
            pass


async def _ensure_user_has_seed_data(user, db):
    """Check if existing user has seed data, create if missing.
    This handles users created before the seed code was deployed.
    """
    from db.models import Watchlist, ScheduledTask, Portfolio, QuantStrategy

    try:
        result = await db.execute(select(Watchlist).where(Watchlist.user_id == user.id).limit(1))
        has_watchlist = result.scalar_one_or_none() is not None

        result = await db.execute(select(ScheduledTask).where(ScheduledTask.user_id == user.id).limit(1))
        has_tasks = result.scalar_one_or_none() is not None

        result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id).limit(1))
        has_portfolio = result.scalar_one_or_none() is not None

        result = await db.execute(select(QuantStrategy).where(QuantStrategy.user_id == user.id).limit(1))
        has_quant = result.scalar_one_or_none() is not None

        if not has_watchlist or not has_tasks or not has_portfolio or not has_quant:
            print(f"[Auth] User {user.username} missing seed data (wl={has_watchlist} tasks={has_tasks} port={has_portfolio} quant={has_quant}), seeding...")
            if not has_watchlist and not has_portfolio and not has_quant:
                # Full seed
                await _seed_new_user_data(user, db)
            else:
                # Partial seed — only add missing quant strategies
                if not has_quant:
                    await _seed_quant_strategies(user, db)
    except Exception as e:
        print(f"[Auth] Error checking seed data for {user.username}: {e}")


async def _seed_quant_strategies(user, db):
    """Seed only quant strategies and trading strategy for existing user"""
    from db.models import QuantStrategy, TradingStrategy, StrategyStatus

    try:
        QUANT_STRATEGIES = [
            {"name": "双均线交叉策略", "description": "短期均线上穿长期均线买入，下穿卖出",
             "template_name": "dual_ma_cross",
             "parameters": {"short_period": 5, "long_period": 20, "position_size": 0.3, "stop_loss_pct": 0.05},
             "code": "import pandas as pd\nimport numpy as np\n\ndef initialize(context):\n    context.short_period = params.get('short_period', 5)\n    context.long_period = params.get('long_period', 20)\n    context.position_size = params.get('position_size', 0.3)\n\ndef handle_data(context, data):\n    close = data['close']\n    short_ma = close.rolling(context.short_period).mean()\n    long_ma = close.rolling(context.long_period).mean()\n    if short_ma.iloc[-1] > long_ma.iloc[-1] and short_ma.iloc[-2] <= long_ma.iloc[-2]:\n        return {'signal': 'buy', 'weight': context.position_size}\n    elif short_ma.iloc[-1] < long_ma.iloc[-1] and short_ma.iloc[-2] >= long_ma.iloc[-2]:\n        return {'signal': 'sell', 'weight': 1.0}\n    return {'signal': 'hold'}\n"},
            {"name": "MACD动量策略", "description": "MACD金叉买入，死叉卖出",
             "template_name": "macd_momentum",
             "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9, "position_size": 0.25},
             "code": "import pandas as pd\nimport numpy as np\n\ndef initialize(context):\n    context.fast = params.get('fast_period', 12)\n    context.slow = params.get('slow_period', 26)\n    context.signal = params.get('signal_period', 9)\n    context.position_size = params.get('position_size', 0.25)\n\ndef handle_data(context, data):\n    close = data['close']\n    ema_fast = close.ewm(span=context.fast).mean()\n    ema_slow = close.ewm(span=context.slow).mean()\n    macd_line = ema_fast - ema_slow\n    signal_line = macd_line.ewm(span=context.signal).mean()\n    if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:\n        return {'signal': 'buy', 'weight': context.position_size}\n    elif macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]:\n        return {'signal': 'sell', 'weight': 1.0}\n    return {'signal': 'hold'}\n"},
            {"name": "RSI超买超卖策略", "description": "RSI低于30买入，高于70卖出",
             "template_name": "rsi_overbought_oversold",
             "parameters": {"rsi_period": 14, "oversold": 30, "overbought": 70, "position_size": 0.25},
             "code": "import pandas as pd\nimport numpy as np\n\ndef initialize(context):\n    context.period = params.get('rsi_period', 14)\n    context.oversold = params.get('oversold', 30)\n    context.overbought = params.get('overbought', 70)\n    context.position_size = params.get('position_size', 0.25)\n\ndef compute_rsi(series, period):\n    delta = series.diff()\n    gain = delta.where(delta > 0, 0).rolling(period).mean()\n    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()\n    rs = gain / loss\n    return 100 - (100 / (1 + rs))\n\ndef handle_data(context, data):\n    close = data['close']\n    rsi = compute_rsi(close, context.period)\n    if rsi.iloc[-1] < context.oversold:\n        return {'signal': 'buy', 'weight': context.position_size}\n    elif rsi.iloc[-1] > context.overbought:\n        return {'signal': 'sell', 'weight': 1.0}\n    return {'signal': 'hold'}\n"},
            {"name": "布林带突破策略", "description": "价格触及下轨买入，触及上轨卖出",
             "template_name": "bollinger_breakout",
             "parameters": {"period": 20, "num_std": 2.0, "position_size": 0.2},
             "code": "import pandas as pd\nimport numpy as np\n\ndef initialize(context):\n    context.period = params.get('period', 20)\n    context.num_std = params.get('num_std', 2.0)\n    context.position_size = params.get('position_size', 0.2)\n\ndef handle_data(context, data):\n    close = data['close']\n    ma = close.rolling(context.period).mean()\n    std = close.rolling(context.period).std()\n    upper = ma + context.num_std * std\n    lower = ma - context.num_std * std\n    current = close.iloc[-1]\n    if current <= lower.iloc[-1]:\n        return {'signal': 'buy', 'weight': context.position_size}\n    elif current >= upper.iloc[-1]:\n        return {'signal': 'sell', 'weight': 1.0}\n    return {'signal': 'hold'}\n"},
        ]
        for qs in QUANT_STRATEGIES:
            db.add(QuantStrategy(
                user_id=user.id, name=qs["name"], description=qs["description"],
                template_name=qs["template_name"], code=qs["code"],
                parameters=qs["parameters"], status=StrategyStatus.DRAFT,
            ))

        # Check if user has trading strategy
        result = await db.execute(select(TradingStrategy).where(TradingStrategy.user_id == user.id).limit(1))
        if not result.scalar_one_or_none():
            db.add(TradingStrategy(
                user_id=user.id, name="均线+MACD综合策略",
                description="结合均线趋势和MACD动量的综合交易策略",
                strategy_type="technical",
                parameters={"ma_short": 5, "ma_long": 20},
                indicators=["MA", "MACD", "RSI", "BOLL"],
                buy_conditions=["短期均线上穿长期均线", "MACD金叉", "RSI在30-50区间"],
                sell_conditions=["短期均线下穿长期均线", "MACD死叉", "RSI超过70", "止损-5%"],
                risk_rules={"max_position_pct": 0.3, "stop_loss_pct": 0.05},
                status=StrategyStatus.ACTIVE,
            ))

        await db.commit()
        print(f"[Auth] Seeded quant strategies for {user.username}")
    except Exception as e:
        print(f"[Auth] Failed to seed quant for {user.username}: {e}")
        try:
            await db.rollback()
        except Exception:
            pass
