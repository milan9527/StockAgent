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

SYSTEM_PROMPT = """你是一位资深证券投资分析师，拥有CFA资格和10年A股研究经验。

分析要求:
- 深度思考后再回复，不要泛泛而谈
- 结合行业竞争格局、公司基本面、市场趋势
- 引用具体数据(PE/PB/ROE/营收增速等)

你拥有以下工具:
- get_stock_realtime_quote: 获取实时行情
- analyze_technical_indicators: 技术指标分析(只需传stock_code)
- web_search / search_financial_news / fetch_web_page: Web搜索
- crawl_financial_news: 专业财经爬虫(东方财富/新浪/财联社)
- crawl_stock_reports: 爬取个股券商研报评级
- crawl_web_page_deep: 深度网页爬取(文章/链接/表格)
- crawl_industry_data: 行业数据和资金流向

注意: Browser和Code Interpreter工具仅在AgentCore Runtime中可用。
如需使用这些工具，请通过AI助手(编排Agent)调用。

输出格式(Markdown):
## 📊 {公司名称}({代码}) 深度分析
### 一、公司概况与行业地位
### 二、财务分析与估值
### 三、技术面分析
### 四、投资建议
### 五、风险提示

⚠️ 本报告由AI生成，仅供参考，不构成投资建议。"""


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
