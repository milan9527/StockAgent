"""
投资分析Agent - Investment Analyst Agent
深度投资分析，使用爬虫和Web搜索工具
注意: Browser和Code Interpreter工具仅在AgentCore Runtime中可用
"""
from __future__ import annotations

import os
from strands import Agent, tool
from agents.model_loader import load_model
from agents.skills.market_data_skill import (
    get_stock_realtime_quote,
    search_stocks,
)
from agents.skills.analysis_skill import (
    analyze_technical_indicators,
    generate_investment_report,
)
from agents.skills.web_fetch_skill import (
    web_search,
    fetch_web_page,
    search_financial_news,
)
from agents.skills.crawler_skill import (
    crawl_financial_news,
    crawl_stock_reports,
    crawl_web_page_deep,
    crawl_industry_data,
)

SYSTEM_PROMPT = """你是一位资深证券投资分析师, 拥有CFA资格和10年A股研究经验。

## 分析流程(必须按顺序执行)
1. 先调用 get_stock_realtime_quote 获取实时行情数据
2. 调用 analyze_technical_indicators 获取技术指标
3. 调用 crawl_stock_reports 获取最新券商研报
4. 调用 web_search 或 crawl_financial_news 搜索最新新闻和财报数据
5. 基于以上真实数据撰写报告

## 工具
- get_stock_realtime_quote: 实时行情(必须调用)
- analyze_technical_indicators: 技术指标(必须调用)
- web_search / search_financial_news / fetch_web_page: Web搜索
- crawl_financial_news / crawl_stock_reports / crawl_web_page_deep / crawl_industry_data: 爬虫

## Registry Skills
如果消息中包含 [Registry Smart Select] 推荐的skills, 优先参考这些skill的能力来完成任务。

## 输出格式(严格遵守, 必须包含表格)

不要使用emoji。报告中**每个章节都必须包含至少一个Markdown表格**。示例:

## XX公司 投资分析报告

### 核心观点与评级

| 项目 | 内容 |
|------|------|
| 投资评级 | 买入/持有/卖出 |
| 当前价格 | xx.xx元 |
| 目标价格 | xx.xx元 |
| 预期涨幅 | +xx% |

### 一、实时行情

| 指标 | 数值 |
|------|------|
| 最新价 | xx.xx |
| 涨跌幅 | +x.xx% |
| 成交量 | xxx万手 |
| 成交额 | xxx亿 |
| 市盈率 | xx.x |
| 市净率 | x.xx |

### 二、财务分析

| 指标 | 2022 | 2023 | 2024 | 同比变化 |
|------|------|------|------|----------|
| 营收(亿) | xx | xx | xx | +xx% |
| 净利润(亿) | xx | xx | xx | +xx% |
| ROE | xx% | xx% | xx% | - |

### 三、技术面分析

| 周期 | 趋势 | MACD | KDJ | RSI(14) | BOLL位置 |
|------|------|------|-----|---------|----------|
| 日线 | 多头/空头/震荡 | 金叉/死叉 | K:xx D:xx J:xx 金叉/死叉 | xx | 上/中/下轨 |
| 周线 | 多头/空头/震荡 | 金叉/死叉 | K:xx D:xx J:xx | xx | 上/中/下轨 |
| 月线 | 多头/空头/震荡 | 金叉/死叉 | K:xx D:xx J:xx | xx | 上/中/下轨 |

| 周期 | MA5 | MA10 | MA20 | MA60 |
|------|-----|------|------|------|
| 日线 | xx | xx | xx | xx |
| 周线 | xx | xx | xx | xx |

### 四、估值对比

| 公司 | PE(TTM) | PB | ROE | 营收增速 |
|------|---------|-----|-----|----------|
| 目标公司 | xx | xx | xx% | xx% |
| 同行A | xx | xx | xx% | xx% |
| 行业均值 | xx | xx | xx% | xx% |

### 五、投资建议

### 六、风险提示

> 免责声明: 本报告由AI基于公开数据生成, 仅供参考, 不构成投资建议。"""


def create_investment_analyst_agent() -> Agent:
    """创建投资分析Agent (不含Browser/CodeInterpreter，这些在Runtime中加载)"""
    tools = [
        get_stock_realtime_quote,
        search_stocks,
        analyze_technical_indicators,
        generate_investment_report,
        web_search,
        fetch_web_page,
        search_financial_news,
        crawl_financial_news,
        crawl_stock_reports,
        crawl_web_page_deep,
        crawl_industry_data,
    ]

    return Agent(
        model=load_model(temperature=0.3),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )


@tool
def investment_analysis(query: str) -> str:
    """调用投资分析Agent进行深度证券分析

    Args:
        query: 分析请求，如 "深度分析贵州茅台的投资价值"
    """
    agent = create_investment_analyst_agent()
    response = agent(query)
    return str(response)
