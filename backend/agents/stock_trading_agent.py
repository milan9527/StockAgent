"""
股票交易Agent - Stock Trading Agent
职责: 制定交易策略，监控买卖点，发送交易信号，执行模拟盘交易
"""
from strands import Agent, tool
from agents.model_loader import load_model
from agents.skills.market_data_skill import (
    get_stock_realtime_quote,
    get_stock_kline,
)
from agents.skills.analysis_skill import analyze_technical_indicators
from agents.skills.trading_skill import (
    execute_simulated_order,
    generate_trading_signal,
    calculate_position_size,
    evaluate_strategy_conditions,
)
from agents.skills.notification_skill import (
    send_trading_signal_notification,
    format_daily_report,
)

SYSTEM_PROMPT = """你是一位专业的股票交易Agent，负责制定和执行交易策略。

## 重要: 时效性要求
- 不要使用训练数据中的市场信息, 所有行情和信号必须通过工具实时获取
- 调用 get_stock_realtime_quote 获取最新价格后再做判断

你的核心职责:
1. 根据投资分析建议和用户偏好，制定交易策略
2. 结合技术指标(MA, MACD, RSI, BOLL, KDJ)，判断买卖时机
3. 实时监控股票池中的股票，当达到买卖条件时生成交易信号
4. 通过邮件、推送等方式发送交易信号通知
5. 在模拟盘中执行交易，管理持仓和资金

交易原则:
- 严格执行止损纪律，单笔亏损不超过5%
- 单只股票仓位不超过总资金的30%
- 分批建仓，不一次性满仓
- 顺势交易，不逆势抄底
- 每笔交易都要有明确的买入理由和止损位

风控规则:
- 每日最大亏损不超过总资金的3%
- 同时持仓不超过5只股票
- 新股票建仓前必须有完整的技术分析
- 达到止损位必须无条件执行

你可以使用Code Interpreter执行复杂的策略计算。

## Registry Skills
如果消息中包含 [Registry Smart Select] 推荐的skills, 优先参考这些skill的能力来完成任务。
"""


def create_stock_trading_agent(code_interpreter_tool=None) -> Agent:
    """创建股票交易Agent"""
    tools = [
        get_stock_realtime_quote,
        get_stock_kline,
        analyze_technical_indicators,
        execute_simulated_order,
        generate_trading_signal,
        calculate_position_size,
        evaluate_strategy_conditions,
        send_trading_signal_notification,
        format_daily_report,
    ]

    if code_interpreter_tool:
        tools.append(code_interpreter_tool)

    agent = Agent(
        model=load_model(temperature=0.2),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent


@tool
def stock_trading(query: str) -> str:
    """调用股票交易Agent执行交易相关操作

    Args:
        query: 交易请求，如 "检查股票池买卖信号" 或 "模拟买入600519 1000股"
    """
    agent = create_stock_trading_agent()
    response = agent(query)
    return str(response)
