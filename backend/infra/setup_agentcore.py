"""
AgentCore 基础设施初始化脚本
创建 Memory, Browser, Code Interpreter, Registry 资源
"""
import boto3
import json
import uuid
import time
from config.settings import get_settings

settings = get_settings()


def setup_agentcore_memory():
    """创建AgentCore Memory资源 - 存储短期和长期记忆"""
    print("📦 创建 AgentCore Memory...")

    # 使用CLI创建(推荐)
    import subprocess
    result = subprocess.run(
        [
            "agentcore", "memory", "create", "securities_trading_memory",
            "--description", "证券交易助手Agent平台记忆存储 - 短期对话记忆和长期投资策略学习",
            "--strategies", json.dumps([
                {
                    "summaryMemoryStrategy": {
                        "name": "SessionSummarizer",
                        "namespaces": ["/summaries/{actorId}/{sessionId}"]
                    }
                },
                {
                    "userPreferenceMemoryStrategy": {
                        "name": "InvestmentPreferenceLearner",
                        "namespaces": ["/preferences/{actorId}"]
                    }
                },
                {
                    "semanticMemoryStrategy": {
                        "name": "TradingKnowledgeExtractor",
                        "namespaces": ["/knowledge/{actorId}"]
                    }
                }
            ]),
            "--region", settings.AWS_REGION,
            "--wait",
        ],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"⚠️ Memory创建失败: {result.stderr}")
    return result.stdout


def setup_agentcore_browser():
    """创建AgentCore Browser - Public模式，启用Web Bot Auth"""
    print("🌐 创建 AgentCore Browser (Public + Web Bot Auth)...")

    client = boto3.client("bedrock-agentcore-control", region_name=settings.AWS_REGION)

    try:
        response = client.create_browser(
            name="SecuritiesTradingBrowser",
            description="证券交易助手浏览器 - 用于获取最新市场数据、新闻和研报",
            networkConfiguration={
                "networkMode": "PUBLIC"
            },
            browserSigning={
                "enabled": True  # 启用Web Bot Auth
            },
            clientToken=str(uuid.uuid4()),
        )
        browser_id = response.get("browserId")
        print(f"✅ Browser创建成功: {browser_id}")
        print(f"   状态: {response.get('status')}")
        return browser_id
    except Exception as e:
        print(f"⚠️ Browser创建失败: {e}")
        return None


def setup_agentcore_code_interpreter():
    """创建AgentCore Code Interpreter - Public模式"""
    print("💻 创建 AgentCore Code Interpreter (Public)...")

    client = boto3.client("bedrock-agentcore-control", region_name=settings.AWS_REGION)

    try:
        response = client.create_code_interpreter(
            name="SecuritiesTradingCodeInterpreter",
            description="证券交易助手代码解释器 - 用于投资分析、量化策略回测等代码执行",
            networkConfiguration={
                "networkMode": "PUBLIC"
            },
            clientToken=str(uuid.uuid4()),
        )
        ci_id = response.get("codeInterpreterId")
        print(f"✅ Code Interpreter创建成功: {ci_id}")
        print(f"   状态: {response.get('status')}")
        return ci_id
    except Exception as e:
        print(f"⚠️ Code Interpreter创建失败: {e}")
        return None


def setup_agentcore_registry():
    """创建AgentCore Registry - 统一管理Skills"""
    print("📋 创建 AgentCore Registry...")

    client = boto3.client("bedrock-agentcore-control", region_name=settings.AWS_REGION)

    try:
        response = client.create_registry(
            name="SecuritiesTradingRegistry",
            description="证券交易助手Skill注册中心 - 管理所有Agent Skills和MCP工具",
        )
        registry_arn = response.get("registryArn")
        print(f"✅ Registry创建成功: {registry_arn}")
        return registry_arn
    except Exception as e:
        print(f"⚠️ Registry创建失败: {e}")
        return None


def register_skills_to_registry(registry_id: str):
    """将平台Skills注册到Registry"""
    print("📝 注册Skills到Registry...")

    client = boto3.client("bedrock-agentcore-control", region_name=settings.AWS_REGION)

    skills = [
        {
            "name": "market-data-skill",
            "description": "行情数据技能 - 获取A股实时行情、K线数据、股票搜索(腾讯证券API)",
            "version": "1.0.0",
            "markdown": """---
name: market-data-skill
description: 行情数据技能，使用腾讯证券API获取A股实时和历史行情数据
---

# 行情数据技能

## 功能
- 获取股票实时行情(腾讯证券API)
- 批量获取多只股票行情
- 获取K线历史数据(日/周/月)
- 股票代码/名称搜索

## 数据源
腾讯证券API (https://qt.gtimg.cn)
""",
        },
        {
            "name": "analysis-skill",
            "description": "投资分析技能 - 技术指标计算、投资报告生成",
            "version": "1.0.0",
            "markdown": """---
name: analysis-skill
description: 投资分析技能，计算技术指标并生成投资报告
---

# 投资分析技能

## 功能
- 计算技术指标(MA, MACD, RSI, BOLL)
- 趋势判断
- 生成综合投资报告
- 投资评级和建议
""",
        },
        {
            "name": "trading-skill",
            "description": "交易技能 - 模拟盘交易、信号生成、仓位计算",
            "version": "1.0.0",
            "markdown": """---
name: trading-skill
description: 交易技能，支持模拟盘交易执行和交易信号生成
---

# 交易技能

## 功能
- 模拟盘交易执行(买入/卖出)
- 交易信号生成
- 仓位大小计算
- 策略条件评估
""",
        },
        {
            "name": "quant-skill",
            "description": "量化交易技能 - 策略回测、绩效评估、量化模板",
            "version": "1.0.0",
            "markdown": """---
name: quant-skill
description: 量化交易技能，提供策略回测和绩效评估功能
---

# 量化交易技能

## 功能
- 量化策略回测引擎
- 预置策略模板(幻方量化风格)
- 绩效指标计算(夏普、最大回撤等)
- 策略代码执行
""",
        },
        {
            "name": "notification-skill",
            "description": "通知技能 - 交易信号推送、每日报告",
            "version": "1.0.0",
            "markdown": """---
name: notification-skill
description: 通知技能，支持邮件、推送等多渠道交易信号通知
---

# 通知技能

## 功能
- 交易信号邮件通知
- 推送通知(WebSocket)
- 每日投资报告格式化
""",
        },
    ]

    for skill in skills:
        try:
            response = client.create_registry_record(
                registryId=registry_id,
                name=skill["name"],
                descriptorType="AgentSkills",
                descriptors={
                    "agentSkills": {
                        "markdown": skill["markdown"],
                    }
                },
                recordVersion=skill["version"],
                description=skill["description"],
            )
            record_id = response.get("recordId")
            print(f"  ✅ {skill['name']} 注册成功: {record_id}")

            # 提交审批
            client.submit_registry_record_for_approval(
                registryId=registry_id,
                recordId=record_id,
            )
        except Exception as e:
            print(f"  ⚠️ {skill['name']} 注册失败: {e}")


def setup_agentcore_observability():
    """配置AgentCore Observability - OTEL日志"""
    print("📊 配置 AgentCore Observability (OTEL)...")
    print("   AgentCore默认输出OTEL兼容的遥测数据到CloudWatch")
    print("   包括: Agent执行追踪、工具调用指标、延迟和错误率")
    print("   可在CloudWatch控制台查看Observability Dashboard")
    print("   ✅ Observability已默认启用")


def run_full_setup():
    """运行完整的AgentCore基础设施初始化"""
    print("=" * 60)
    print("🚀 证券交易助手Agent平台 - AgentCore基础设施初始化")
    print(f"   区域: {settings.AWS_REGION}")
    print(f"   环境: {settings.ENV}")
    print("=" * 60)

    # 1. Memory
    setup_agentcore_memory()
    print()

    # 2. Browser
    browser_id = setup_agentcore_browser()
    print()

    # 3. Code Interpreter
    ci_id = setup_agentcore_code_interpreter()
    print()

    # 4. Registry
    registry_arn = setup_agentcore_registry()
    if registry_arn:
        # 等待Registry就绪
        print("   等待Registry就绪...")
        time.sleep(10)
        # 提取registry_id
        registry_id = registry_arn.split("/")[-1] if registry_arn else ""
        if registry_id:
            register_skills_to_registry(registry_id)
    print()

    # 5. Observability
    setup_agentcore_observability()
    print()

    print("=" * 60)
    print("✅ AgentCore基础设施初始化完成!")
    print()
    print("请将以下ID更新到环境配置文件:")
    if browser_id:
        print(f"  AGENTCORE_BROWSER_ID={browser_id}")
    if ci_id:
        print(f"  AGENTCORE_CODE_INTERPRETER_ID={ci_id}")
    print("=" * 60)


if __name__ == "__main__":
    run_full_setup()
