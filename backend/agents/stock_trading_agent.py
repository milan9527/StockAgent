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

## 核心能力 (全流程)
1. **创建交易策略** — 根据用户描述的条件(如MACD金叉、KDJ底部、均线聚集等)制定策略
2. **应用策略到股票** — 获取指定股票或自选股池的实时行情和技术指标, 逐一判断是否满足买卖条件
3. **筛选符合条件的股票** — 从自选股池中找出满足策略条件的股票
4. **生成交易信号** — 当股票满足买入/卖出条件时生成信号
5. **执行模拟交易** — 在模拟盘中执行买入/卖出操作

## 工作流程
当用户说"应用策略到自选股"或"分析买卖信号"时:
1. 先调用 get_stock_realtime_quote 获取每只股票的实时行情
2. 调用 analyze_technical_indicators 获取技术指标(MA/MACD/KDJ/RSI)
3. 根据策略条件判断每只股票的信号
4. 用表格输出结果: 股票 | 当前价 | 信号 | 理由
5. 如果用户要求执行交易, 调用 execute_simulated_order

## 输出格式
- 分析结果必须用Markdown表格展示
- 每只股票一行, 列出: 代码、名称、当前价、信号(买入/卖出/持有)、关键指标、理由

交易原则:
- 严格执行止损纪律，单笔亏损不超过5%
- 单只股票仓位不超过总资金的30%
- 分批建仓，不一次性满仓
- 顺势交易，不逆势抄底

风控规则:
- 同时持仓不超过5只股票
- 新股票建仓前必须有完整的技术分析
- 达到止损位必须无条件执行

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
