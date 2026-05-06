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

## 重要: 时效性要求
- 你的训练数据有截止日期, 不要依赖训练数据中的市场信息
- 所有市场分析、新闻搜索、行情数据必须通过工具获取实时/最新数据
- 涉及"本周"、"今日"、"最新"等时间相关请求时, 必须调用web_search或get_stock_realtime_quote获取当前数据
- 不要凭记忆回答任何市场相关问题, 必须先调用工具获取数据

## 你的直接工具
- get_stock_realtime_quote: 获取股票实时行情
- get_stock_batch_quotes: 批量获取行情
- search_stocks: 搜索股票
- browser: AgentCore Browser (速度较慢，仅在必要时使用)
- code_interpreter: AgentCore Code Interpreter (执行Python代码、生成爬虫程序)

## 你的专业子Agent(作为工具调用)
- investment_analysis: 深度投资分析(行业+公司+技术面+估值+爬虫+Web搜索)
- stock_trading: 交易策略和模拟盘
- quant_trading: 量化策略和回测

## 工具选择规则

**用户明确指定工具时:**
1. "用浏览器"/"browser" → 直接调用 browser
2. "执行代码"/"code interpreter" → 直接调用 code_interpreter
3. "用爬虫"/"爬取" → 调用 investment_analysis

**用户未指定工具时:**
4. 投资分析/研究/新闻/公司分析 → investment_analysis
5. 交易/买卖/模拟盘/策略 → stock_trading
6. 量化/回测/策略代码 → quant_trading
7. 简单行情查询 → get_stock_realtime_quote

## 严格执行规则
- **每个请求只调用1个子Agent**, 不要串联多个子Agent
- 不要重复调用同类工具
- investment_analysis已包含技术分析, 不需要再调用quant_trading
- 只有用户明确要求"回测"或"量化策略"时才调用quant_trading

## Browser使用条件
仅在: 用户明确要求 / web_search失败 / 需要JS渲染的页面

## Code Interpreter
当crawl工具数据不够时, 生成Python爬虫补充数据

## Skill Filter
如果用户消息中包含 [SKILL FILTER], 必须严格遵守:
- 只使用列出的skill对应的工具
- market-data-skill → get_stock_realtime_quote, get_stock_batch_quotes, search_stocks
- analysis-skill → investment_analysis (子Agent)
- trading-skill → stock_trading (子Agent)
- quant-skill → quant_trading (子Agent)
- web-fetch-skill, crawler-skill → investment_analysis (内含web搜索和爬虫)
- browser-crawler-skill → browser
- code-interpreter-skill → code_interpreter
- 未列出的skill对应的工具禁止调用

## Registry外部Skill使用规则
- Registry中的外部skill(如akshare, tushare)通过code_interpreter执行
- 当Registry Smart Select加载了skill内容时, 参考其中的API文档编写代码
- 优先使用Registry中推荐的专业数据接口, 而非通用web_search

## 全市场选股能力
当用户要求"在所有股票中筛选/找出"时:
- 使用code_interpreter + Registry推荐的数据skill(如akshare)
- 参考加载的skill API文档编写完整筛选脚本
- 如果code_interpreter失败, 改用 investment_analysis (web_search + crawler)
- 不要在同一个错误上重复调用

## 工具调用规则 (严格执行)
- **禁止重复调用**: 如果一个工具调用返回了错误或相同结果, 不要用相同/类似参数再次调用
- **code_interpreter**: 把完整逻辑写在一个脚本里。如果执行失败, 分析错误原因修改代码再试, 但最多重试2次
- **session冲突**: 如果code_interpreter报"session already in use", 换一个唯一的session name, 不要重复用相同name
- **失败切换**: 同一工具连续失败2次后, 换其他工具或直接基于已有数据给出结果
- **不要做重复工作**: 如果已经获取了某个数据, 不要再次获取相同数据

## 并行执行策略
- 鼓励并行调用**不同的**独立任务(如同时查询多只股票行情)
- 禁止并行调用**相同的**工具做相同的事(这是重复, 不是并行)
- code_interpreter可以并行调用, 但每个调用必须做不同的事情(如一个获取数据, 一个计算指标)

## 输出格式
- Markdown格式, 不要emoji, 专业严谨
- 数据用Markdown表格, 关键结论**加粗**, 风险用 > 引用块
- 系统会自动将Markdown转为专业HTML渲染

## Memory自进化 (SCOPE)
你的对话存储在AgentCore Memory中, 支持短期记忆(STM)和长期记忆(LTM)。
Memory策略:
- SessionSummarizer: 自动总结每次会话要点
- InvestmentPreferenceLearner: 学习用户投资偏好和风险承受能力
- TradingKnowledgeEvolution: 积累交易知识和市场洞察
当你发现新的市场规律、策略效果验证结果、或用户偏好变化时, 在回复中明确总结这些发现, Memory系统会自动提取并存储。
对于预测任务, 请在回复末尾添加 [预测记录] 标签, 包含预测内容和验证条件, 便于后续验证。"""


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
    """创建编排Agent, 自动集成可用的AgentCore组件"""
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

    agent_kwargs = {
        "model": load_model(temperature=0.3),
        "tools": tools,
        "system_prompt": ORCHESTRATOR_SYSTEM_PROMPT,
    }
    if session_manager:
        agent_kwargs["session_manager"] = session_manager

    return Agent(**agent_kwargs)


def _detect_task_tokens(prompt: str) -> int:
    """Detect appropriate max_tokens based on task type"""
    prompt_lower = prompt.lower()
    # Deep analysis / scheduler tasks need more tokens
    if any(kw in prompt_lower for kw in ["深度分析", "全面分析", "深度研究", "详细报告", "scheduler-", "定期任务"]):
        return 65536  # 64K for deep analysis
    # Simple queries
    if any(kw in prompt_lower for kw in ["你好", "行情", "价格", "查询"]):
        return 8192  # 8K for simple queries
    # Default
    return 16384  # 16K default


def _search_registry_skills(query: str) -> str:
    """Search AgentCore Registry for relevant skills and return context string.
    Always includes key data skills (akshare/tushare) for market-related queries.
    """
    registry_id = os.environ.get("AGENTCORE_REGISTRY_ID", "Eea8hqxihmpeJlYv")
    if not registry_id:
        return ""
    try:
        import boto3
        region = os.environ.get("AWS_REGION", "us-east-1")
        ctrl_client = boto3.client("bedrock-agentcore-control", region_name=region)
        dp_client = boto3.client("bedrock-agentcore", region_name=region)
        registry_arn = f"arn:aws:bedrock-agentcore:{region}:632930644527:registry/{registry_id}"

        # Semantic search for query-relevant skills
        response = dp_client.search_registry_records(
            registryIds=[registry_arn],
            searchQuery=query[:200],
            maxResults=5,
        )
        records = response.get("registryRecords", [])
        matched_names = {r.get("name", "") for r in records}

        # Always include key data skills for market-related queries
        MARKET_KEYWORDS = ["股票", "行情", "K线", "选股", "筛选", "分析", "指标", "市场",
                          "买卖", "信号", "策略", "回测", "涨", "跌", "均线", "MACD", "KDJ"]
        is_market_query = any(kw in query for kw in MARKET_KEYWORDS)

        # Load akshare skill content if it's a market query and not already matched
        akshare_content = ""
        if is_market_query and "akshare" not in matched_names:
            try:
                # Search specifically for akshare
                ak_resp = dp_client.search_registry_records(
                    registryIds=[registry_arn], searchQuery="akshare", maxResults=2,
                )
                ak_records = ak_resp.get("registryRecords", [])
                if ak_records:
                    records.extend(ak_records)
                    matched_names.update(r.get("name", "") for r in ak_records)
            except Exception:
                pass

        # Load full skill content for external skills (to provide API reference)
        BUILTIN = {"market-data-skill", "analysis-skill", "web-fetch-skill", "trading-skill",
                   "quant-skill", "notification-skill", "crawler-skill", "browser-crawler-skill", "code-interpreter-skill"}

        lines = ["\n[Registry Smart Select - 相关Skills:]"]
        for rec in records:
            name = rec.get("name", "")
            desc = rec.get("description", "")[:150]
            record_id = rec.get("recordId", "")

            if name in BUILTIN:
                lines.append(f"- {name} (内置): {desc}")
            else:
                lines.append(f"- {name} (外部, 通过code_interpreter使用): {desc}")
                # Load full content for external skills to provide API reference
                if record_id and is_market_query:
                    try:
                        detail = ctrl_client.get_registry_record(registryId=registry_id, recordId=record_id)
                        record_data = detail.get("registryRecord", detail)
                        descriptors = record_data.get("descriptors", {})
                        skill_md = descriptors.get("agentSkills", {}).get("skillMd", {}).get("inlineContent", "")
                        if skill_md and len(skill_md) > 50:
                            # Include skill content as API reference (up to 5KB)
                            lines.append(f"\n  [{name} API参考:]")
                            lines.append(f"  {skill_md[:5000]}")
                    except Exception:
                        pass

        if is_market_query and "akshare" not in matched_names:
            lines.append("\n注意: akshare是免费A股数据接口, 可通过code_interpreter直接import akshare as ak使用")

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

            # Dynamic token limit based on task type
            dynamic_tokens = _detect_task_tokens(prompt)
            if dynamic_tokens != 16384:
                agent.model = load_model(temperature=0.3, max_tokens=dynamic_tokens)
                print(f"[Invoke] Dynamic tokens: {dynamic_tokens}")

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
