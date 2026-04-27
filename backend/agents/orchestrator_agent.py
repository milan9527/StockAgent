"""
编排Agent - Securities Trading Orchestrator
运行在AgentCore Runtime，集成Memory/Browser/CodeInterpreter
OTEL SDK instrumented for trace/span
"""
from __future__ import annotations

import os
import time
from strands import Agent
from bedrock_agentcore import BedrockAgentCoreApp

# ── OTEL Tracing Setup ──
from opentelemetry import trace
from opentelemetry.trace import StatusCode

tracer = trace.get_tracer("securities-trading-agent", "1.0.0")

from agents.model_loader import load_model
from agents.investment_analyst_agent import investment_analysis
from agents.stock_trading_agent import stock_trading
from agents.quant_trading_agent import quant_trading
from agents.skills.market_data_skill import (
    get_stock_realtime_quote,
    get_stock_batch_quotes,
    search_stocks,
)

ORCHESTRATOR_SYSTEM_PROMPT = """你是证券交易助手平台的总编排Agent。

## 你的直接工具
- get_stock_realtime_quote: 获取股票实时行情
- get_stock_batch_quotes: 批量获取行情
- search_stocks: 搜索股票
- browser: **AgentCore Browser** (速度较慢，仅在必要时使用)
- code_interpreter: **AgentCore Code Interpreter** - 执行Python代码、数据分析、生成爬虫程序

## 你的专业子Agent(作为工具调用)
- investment_analysis: 深度投资分析(行业+公司+技术面+估值+爬虫+Web搜索)
- stock_trading: 交易策略和模拟盘
- quant_trading: 量化策略和回测

## ⚠️ 工具选择规则(按优先级)

**最高优先级 - 用户明确指定工具:**
1. 用户明确说"用浏览器"、"browser" → 直接调用 browser 工具
2. 用户明确说"执行代码"、"code interpreter"、"运行代码" → 直接调用 code_interpreter 工具
3. 用户说"用爬虫"、"爬取"、"crawler" → 先调用 investment_analysis(内含crawl工具)，如果数据不够全面，再用 code_interpreter 生成专业爬虫程序补充

**普通优先级 - 用户未指定工具:**
4. 涉及投资分析/深度研究/新闻搜索/公司分析 → 调用 investment_analysis
5. 涉及交易/买卖/模拟盘/策略 → 调用 stock_trading
6. 涉及量化/回测/策略代码 → 调用 quant_trading
7. 简单行情查询 → 直接用 get_stock_realtime_quote

## 🐍 Code Interpreter 爬虫能力
当内置crawl工具数据不够全面时，使用 code_interpreter 生成并执行Python爬虫程序:
- 用 requests + BeautifulSoup 爬取目标网站
- 可爬取东方财富、新浪财经、同花顺、证券时报等财经网站
- 可解析HTML提取新闻标题、内容、时间等结构化数据
- 可同时爬取多个数据源进行汇总
- 示例: 用户说"用爬虫获取固态电池最新动态" → 先用investment_analysis的crawl工具，然后用code_interpreter生成爬虫程序补充更多数据源

## 🌐 Browser使用条件(速度较慢，谨慎使用)
browser 仅在以下情况使用:
- 用户**明确要求**使用浏览器
- web_search/crawler获取的信息**不足或失败**，需要补充
- 目标网页需要**JavaScript渲染**或**登录**

**默认优先使用** investment_analysis 的 web_search/crawler，速度更快。回复用中文Markdown格式。"""


def _build_browser_tool():
    browser_id = os.environ.get("AGENTCORE_BROWSER_ID", "SecuritiesTradingBrowser-F6aHtUeGkj")
    if not browser_id:
        return None
    try:
        from strands_tools.browser import AgentCoreBrowser
        region = os.environ.get("AWS_REGION", "us-east-1")
        print(f"[Browser] Initializing with id={browser_id}, region={region}")
        tool = AgentCoreBrowser(region=region, identifier=browser_id).browser
        print(f"[Browser] Successfully loaded: {getattr(tool, 'name', 'browser')}")
        return tool
    except Exception as e:
        print(f"[Browser] init failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def _build_code_interpreter_tool():
    ci_id = os.environ.get("AGENTCORE_CODE_INTERPRETER_ID", "SecuritiesTradingCodeInterpreter-wGp9YodWEL")
    if not ci_id:
        return None
    try:
        from strands_tools.code_interpreter import AgentCoreCodeInterpreter
        region = os.environ.get("AWS_REGION", "us-east-1")
        print(f"[CodeInterpreter] Initializing with id={ci_id}, region={region}")
        tool = AgentCoreCodeInterpreter(region=region, identifier=ci_id).code_interpreter
        print(f"[CodeInterpreter] Successfully loaded: {getattr(tool, 'name', 'code_interpreter')}")
        return tool
    except Exception as e:
        print(f"[CodeInterpreter] init failed: {e}")
        import traceback
        traceback.print_exc()
        return None


@tracer.start_as_current_span("create_orchestrator_agent")
def create_orchestrator_agent(session_id: str = "default", actor_id: str = "system") -> Agent:
    """创建编排Agent，自动集成可用的AgentCore组件"""
    span = trace.get_current_span()
    span.set_attribute("agent.name", "SecuritiesTradingAgent")
    span.set_attribute("agent.session_id", session_id)
    span.set_attribute("agent.actor_id", actor_id)

    tools = [investment_analysis, stock_trading, quant_trading,
             get_stock_realtime_quote, get_stock_batch_quotes, search_stocks]

    loaded_tools = []
    with tracer.start_as_current_span("load_agentcore_tools"):
        browser_tool = _build_browser_tool()
        if browser_tool:
            tools.append(browser_tool)
            loaded_tools.append("browser")
            span.add_event("browser_loaded")
        else:
            print(f"[AgentCore] Browser NOT loaded. AGENTCORE_BROWSER_ID={os.environ.get('AGENTCORE_BROWSER_ID', '<not set>')}")

        ci_tool = _build_code_interpreter_tool()
        if ci_tool:
            tools.append(ci_tool)
            loaded_tools.append("code_interpreter")
            span.add_event("code_interpreter_loaded")
        else:
            print(f"[AgentCore] CodeInterpreter NOT loaded. AGENTCORE_CODE_INTERPRETER_ID={os.environ.get('AGENTCORE_CODE_INTERPRETER_ID', '<not set>')}")

    print(f"[AgentCore] Tools loaded: {len(tools)} total, AgentCore tools: {loaded_tools}")
    span.set_attribute("agent.tools_count", len(tools))
    span.set_attribute("agent.agentcore_tools", str(loaded_tools))

    # Memory
    session_manager = None
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "")
    if memory_id:
        with tracer.start_as_current_span("load_memory") as mem_span:
            try:
                from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
                from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
                config = AgentCoreMemoryConfig(memory_id=memory_id, session_id=session_id, actor_id=actor_id)
                session_manager = AgentCoreMemorySessionManager(
                    agentcore_memory_config=config, region_name=os.environ.get("AWS_REGION", "us-east-1"))
                mem_span.set_attribute("memory.id", memory_id)
                mem_span.set_status(StatusCode.OK)
            except Exception as e:
                mem_span.set_status(StatusCode.ERROR, str(e))

    agent_kwargs = {"model": load_model(temperature=0.3), "tools": tools, "system_prompt": ORCHESTRATOR_SYSTEM_PROMPT}
    if session_manager:
        agent_kwargs["session_manager"] = session_manager

    return Agent(**agent_kwargs)


def _search_registry_skills(query: str) -> str:
    """Search AgentCore Registry for relevant skills and return context string"""
    registry_id = os.environ.get("AGENTCORE_REGISTRY_ID", "Eea8hqxihmpeJlYv")
    if not registry_id:
        return ""
    try:
        import boto3
        client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        registry_arn = f"arn:aws:bedrock-agentcore:{os.environ.get('AWS_REGION', 'us-east-1')}:632930644527:registry/{registry_id}"
        response = client.search_registry_records(
            registryIds=[registry_arn],
            searchQuery=query[:200],
            maxResults=5,
        )
        records = response.get("registryRecords", [])
        if not records:
            return ""
        lines = ["\n[Registry Smart Select - 以下Skills与用户请求最相关，优先使用:]"]
        for rec in records:
            lines.append(f"- {rec.get('name', '')}: {rec.get('description', '')[:100]}")
        return "\n".join(lines)
    except Exception as e:
        print(f"[Registry Search] error: {e}")
        return ""


# ── AgentCore Runtime 入口 ──
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict):
    """AgentCore Runtime入口点 - SecuritiesTradingAgent + Registry Smart Select"""
    with tracer.start_as_current_span("agent_invoke") as span:
        start = time.time()
        prompt = payload.get("prompt", "你好")
        session_id = payload.get("session_id", "default")
        user_id = payload.get("user_id", "anonymous")

        span.set_attribute("request.prompt_length", len(prompt))
        span.set_attribute("request.session_id", session_id)
        span.set_attribute("request.user_id", user_id)

        try:
            # Smart Select: search Registry for relevant skills
            with tracer.start_as_current_span("registry_smart_select") as ss_span:
                registry_context = _search_registry_skills(prompt)
                if registry_context:
                    ss_span.set_attribute("smart_select.matched", True)
                    ss_span.set_attribute("smart_select.context_length", len(registry_context))

            # Append Registry context to prompt
            enhanced_prompt = prompt
            if registry_context:
                enhanced_prompt = f"{prompt}\n{registry_context}"

            print(f"[Invoke] prompt={prompt[:100]}... session={session_id} user={user_id}")
            agent = create_orchestrator_agent(session_id=session_id, actor_id=user_id)
            print(f"[Invoke] Agent created with {len(agent.tool_registry.registry)} tools: {list(agent.tool_registry.registry.keys())}")

            with tracer.start_as_current_span("agent_run") as run_span:
                response = agent(enhanced_prompt)
                response_text = str(response)
                run_span.set_attribute("response.length", len(response_text))

            span.set_attribute("response.duration_ms", int((time.time() - start) * 1000))
            span.set_status(StatusCode.OK)

            return {"response": response_text, "session_id": session_id, "user_id": user_id}

        except Exception as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            return {"response": f"⚠️ Agent错误: {str(e)}", "session_id": session_id, "user_id": user_id}


if __name__ == "__main__":
    app.run()
