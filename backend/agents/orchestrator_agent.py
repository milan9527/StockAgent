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

你拥有以下工具(直接可用):
- get_stock_realtime_quote: 获取股票实时行情
- get_stock_batch_quotes: 批量获取行情
- search_stocks: 搜索股票
- browser: **AgentCore Browser** - 用于浏览网页、采集动态页面数据。当用户要求"用浏览器"或需要JavaScript渲染的页面时，必须使用此工具。
- code_interpreter: **AgentCore Code Interpreter** - 用于执行Python代码、数据分析、可视化。当用户要求"执行代码"或需要复杂计算时，必须使用此工具。

你管理三个专业子Agent(作为工具调用):
- investment_analysis: 深度投资分析(行业+公司+技术面+估值+爬虫+Web搜索)
- stock_trading: 交易策略和模拟盘
- quant_trading: 量化策略和回测

工具选择规则:
1. 用户明确说"用浏览器"或"browser" → 直接调用 browser 工具
2. 用户明确说"执行代码"或"code interpreter" → 直接调用 code_interpreter 工具
3. 涉及投资分析/研究/新闻搜索 → 调用 investment_analysis
4. 涉及交易/买卖/模拟盘 → 调用 stock_trading
5. 涉及量化/回测/策略代码 → 调用 quant_trading
6. 简单行情查询 → 直接用 get_stock_realtime_quote

回复用中文Markdown格式。"""


def _build_browser_tool():
    browser_id = os.environ.get("AGENTCORE_BROWSER_ID", "")
    if not browser_id:
        return None
    try:
        from strands_tools.browser import AgentCoreBrowser
        return AgentCoreBrowser(region=os.environ.get("AWS_REGION", "us-east-1"), identifier=browser_id).browser
    except Exception as e:
        print(f"[Browser] init failed: {e}")
        return None


def _build_code_interpreter_tool():
    ci_id = os.environ.get("AGENTCORE_CODE_INTERPRETER_ID", "")
    if not ci_id:
        return None
    try:
        from strands_tools.code_interpreter import AgentCoreCodeInterpreter
        return AgentCoreCodeInterpreter(region=os.environ.get("AWS_REGION", "us-east-1"), identifier=ci_id).code_interpreter
    except Exception as e:
        print(f"[CodeInterpreter] init failed: {e}")
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

    with tracer.start_as_current_span("load_agentcore_tools"):
        browser_tool = _build_browser_tool()
        if browser_tool:
            tools.append(browser_tool)
            span.add_event("browser_loaded")

        ci_tool = _build_code_interpreter_tool()
        if ci_tool:
            tools.append(ci_tool)
            span.add_event("code_interpreter_loaded")

    span.set_attribute("agent.tools_count", len(tools))

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
    registry_id = os.environ.get("AGENTCORE_REGISTRY_ID", "")
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

            agent = create_orchestrator_agent(session_id=session_id, actor_id=user_id)

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
