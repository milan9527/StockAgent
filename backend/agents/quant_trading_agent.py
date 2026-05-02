"""
量化交易Agent - Quantitative Trading Agent
职责: 管理量化策略模板，自定义策略，回测验证，策略优化
参考幻方量化风格
"""
from strands import Agent, tool
from agents.model_loader import load_model
from agents.skills.market_data_skill import get_stock_kline
from agents.skills.quant_skill import (
    run_backtest,
    list_quant_templates,
    calculate_performance_metrics,
)

SYSTEM_PROMPT = """你是一位专业的量化交易Agent，参考幻方量化的方法论，擅长量化策略开发和回测。

你的核心职责:
1. 提供预置量化策略模板(双均线、MACD、布林带、RSI、多因子、海龟交易等)
2. 帮助用户自定义量化交易策略
3. 对策略进行历史回测，验证策略有效性
4. 分析回测结果，给出策略优化建议
5. 计算和展示关键绩效指标(收益率、最大回撤、夏普比率等)

量化分析框架:
- 因子研究: 价值因子、动量因子、质量因子、波动率因子
- 策略类型: 趋势跟踪、均值回归、统计套利、多因子选股
- 风险管理: 仓位控制、止损机制、分散化投资
- 绩效评估: 年化收益、最大回撤、夏普比率、Sortino比率、Calmar比率

策略代码规范:
- 必须包含 initialize(context) 和 handle_data(context, data) 函数
- params 变量包含策略参数
- handle_data 返回 {'signal': 'buy/sell/hold', 'weight': 0.25} 格式
- 使用 pandas 和 numpy 进行数据处理

你可以使用Code Interpreter执行和调试量化策略代码。

## Registry Skills
如果消息中包含 [Registry Smart Select] 推荐的skills, 优先参考这些skill的能力来完成任务。
"""


def create_quant_trading_agent(code_interpreter_tool=None) -> Agent:
    """创建量化交易Agent"""
    tools = [
        get_stock_kline,
        run_backtest,
        list_quant_templates,
        calculate_performance_metrics,
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
def quant_trading(query: str) -> str:
    """调用量化交易Agent执行量化相关操作

    Args:
        query: 量化请求，如 "用双均线策略回测贵州茅台" 或 "创建一个RSI+MACD组合策略"
    """
    agent = create_quant_trading_agent()
    response = agent(query)
    return str(response)
