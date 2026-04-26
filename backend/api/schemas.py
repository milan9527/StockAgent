"""
API请求/响应模型 - Pydantic Schemas
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ── 认证 ──
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    risk_preference: str
    notification_email: bool
    notification_push: bool

    class Config:
        from_attributes = True


# ── Agent对话 ──
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    agent_type: Optional[str] = "orchestrator"  # orchestrator, analyst, trader, quant

class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_type: str
    timestamp: str


# ── 行情 ──
class StockQuoteResponse(BaseModel):
    code: str
    name: str = ""
    current_price: float = 0
    prev_close: float = 0
    open: float = 0
    high: float = 0
    low: float = 0
    volume: float = 0
    amount: float = 0
    change_pct: float = 0
    change_amount: float = 0
    pe_ratio: float = 0
    total_market_cap: float = 0
    tencent_link: str = ""


# ── 股票池 ──
class WatchlistItemCreate(BaseModel):
    stock_code: str
    stock_name: str = ""
    added_reason: str = ""
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None

class WatchlistResponse(BaseModel):
    id: str
    name: str
    description: str
    items: list[dict] = []

    class Config:
        from_attributes = True


# ── 模拟盘 ──
class OrderCreate(BaseModel):
    stock_code: str
    stock_name: str = ""
    side: str  # buy / sell
    price: float
    quantity: int

class PortfolioResponse(BaseModel):
    id: str
    name: str
    initial_capital: float
    available_cash: float
    total_value: float
    total_profit: float
    total_profit_pct: float
    positions: list[dict] = []
    recent_orders: list[dict] = []

    class Config:
        from_attributes = True


# ── 交易策略 ──
class StrategyCreate(BaseModel):
    name: str
    description: str = ""
    strategy_type: str = "technical"
    parameters: dict = {}
    indicators: list[str] = []
    buy_conditions: list[str] = []
    sell_conditions: list[str] = []
    risk_rules: dict = {}

class StrategyResponse(BaseModel):
    id: str
    name: str
    description: str
    strategy_type: str
    parameters: dict
    indicators: list
    buy_conditions: list
    sell_conditions: list
    risk_rules: dict
    status: str

    class Config:
        from_attributes = True


# ── 量化策略 ──
class QuantStrategyCreate(BaseModel):
    name: str
    description: str = ""
    template_name: str = ""
    code: str = ""
    parameters: dict = {}

class BacktestRequest(BaseModel):
    strategy_id: str
    stock_code: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 1000000.0

class BacktestResponse(BaseModel):
    id: str
    strategy_id: str
    initial_capital: float
    final_value: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    status: str
    equity_curve: list = []

    class Config:
        from_attributes = True


# ── 自定义Skill ──
class CustomSkillCreate(BaseModel):
    name: str
    description: str = ""
    skill_type: str = "analysis"
    code: str = ""
    parameters_schema: dict = {}

class CustomSkillResponse(BaseModel):
    id: str
    name: str
    description: str
    skill_type: str
    code: str
    is_published: bool
    version: str

    class Config:
        from_attributes = True
