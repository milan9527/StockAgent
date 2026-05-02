"""
AgentCore Registry Skill Updater
Updates all 9 builtin skills in AgentCore Registry with SKILL.md content
following the agentskills.io specification.

Usage:
    python -m agents.skills.update_registry
"""
from __future__ import annotations

import os
import sys
import boto3
from botocore.exceptions import ClientError

# ═══════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════

REGISTRY_ID = os.environ.get("AGENTCORE_REGISTRY_ID", "Eea8hqxihmpeJlYv")
AWS_REGION = "us-east-1"
SKILL_VERSION = "5.0.0"

# ═══════════════════════════════════════════════════════════════════
# SKILL.md definitions for all 9 builtin skills
# ═══════════════════════════════════════════════════════════════════

SKILLS: list[dict] = [
    # ── 1. market-data-skill ──────────────────────────────────────
    {
        "name": "market-data-skill",
        "description": (
            "Multi-source real-time stock quote skill for China A-share market. "
            "Retrieves live quotes from Tencent, Sina, and Yahoo Finance APIs. "
            "Supports K-line history (daily/weekly/monthly), stock code and name search, "
            "batch quotes for multiple stocks, market index data (SSE/SZSE/CSI300), "
            "and Level-2 order book depth. Use this skill whenever the agent needs "
            "current or historical market price data for any A-share stock."
        ),
        "markdown": """\
---
name: market-data-skill
description: "Multi-source real-time stock quote skill for China A-share market. Retrieves live quotes from Tencent, Sina, and Yahoo Finance APIs. Supports K-line history, stock search, batch quotes, market indices, and order book depth."
compatibility: "Requires AWS Bedrock AgentCore Runtime, Python 3.12"
metadata:
  version: "5.0.0"
  author: "Securities Trading Agent Platform"
  category: "finance"
---

# Market Data Skill

## Overview
Provides comprehensive A-share market data through multiple data source adapters (Tencent Securities, Sina Finance, Yahoo Finance). Automatically normalizes stock codes with market prefixes (sh/sz) and falls back across sources for reliability.

## Tools
- get_stock_realtime_quote: Fetch real-time quote for a single stock (price, change, volume, PE, market cap). Supports source selection (tencent/sina/yahoo).
- get_stock_batch_quotes: Fetch real-time quotes for multiple stocks in a single call. Efficient for watchlist and portfolio views.
- get_stock_kline: Retrieve K-line (candlestick) history data. Supports daily, weekly, and monthly periods with configurable count.
- search_stocks: Search stocks by code or name keyword. Returns matching stock codes, names, and market info.
- get_market_indices: Fetch major market indices (SSE Composite, SZSE Component, CSI 300, ChiNext) with current values and changes.
- get_stock_order_book: Retrieve Level-2 order book with 5-level bid/ask depth for a given stock.
- list_market_data_sources: List all available data source adapters and their capabilities.

## Usage
Use this skill when the user asks about stock prices, market trends, historical data, or needs to look up stock codes. Always prefer batch quotes when multiple stocks are needed. Default data source is Tencent; switch to Sina or Yahoo for K-line history or international comparison.

## Examples
- "Get the current price of Kweichow Moutai (600519)" -> get_stock_realtime_quote("600519")
- "Show me daily K-line for 000858 last 60 days" -> get_stock_kline("000858", "day", 60)
- "Search for stocks related to new energy" -> search_stocks("new energy")
- "How are the major indices doing today?" -> get_market_indices()
""",
    },
    # ── 2. analysis-skill ─────────────────────────────────────────
    {
        "name": "analysis-skill",
        "description": (
            "Multi-timeframe technical analysis skill for A-share stocks. "
            "Computes MA, MACD, RSI, KDJ, and Bollinger Bands across daily, weekly, "
            "and monthly timeframes. Generates comprehensive investment reports with "
            "composite scoring, trend assessment, and buy/sell/hold recommendations. "
            "Use this skill when the agent needs to analyze a stock technically or "
            "produce an investment analysis report."
        ),
        "markdown": """\
---
name: analysis-skill
description: "Multi-timeframe technical analysis skill. Computes MA/MACD/RSI/KDJ/BOLL across daily, weekly, and monthly timeframes. Generates investment reports with composite scoring and recommendations."
compatibility: "Requires AWS Bedrock AgentCore Runtime, Python 3.12, numpy"
metadata:
  version: "5.0.0"
  author: "Securities Trading Agent Platform"
  category: "finance"
---

# Analysis Skill

## Overview
Performs comprehensive technical indicator analysis across multiple timeframes (daily, weekly, monthly). Calculates moving averages (MA5/10/20/60), MACD with golden/death cross detection, RSI overbought/oversold levels, KDJ oscillator signals, and Bollinger Band positioning. Generates investment reports with a composite score (0-100) and actionable recommendations.

## Tools
- analyze_technical_indicators: Run full multi-timeframe technical analysis on a stock. Returns trend direction, MA alignment, MACD/RSI/KDJ/BOLL signals for each timeframe plus a summary.
- generate_investment_report: Produce a formatted investment analysis report combining real-time quote data with technical indicators. Outputs composite score, recommendation (buy/hold/sell), and risk warnings.

## Usage
Use this skill after fetching market data to provide the user with technical analysis insights. Call analyze_technical_indicators first, then generate_investment_report to combine quote data with technical signals into a readable report.

## Examples
- "Analyze the technical indicators for 600519" -> analyze_technical_indicators("600519")
- "Generate an investment report for Wuliangye" -> generate_investment_report("000858", "Wuliangye", quote_data, technical_data)
""",
    },
    # ── 3. web-fetch-skill ────────────────────────────────────────
    {
        "name": "web-fetch-skill",
        "description": (
            "Web information retrieval skill with search engine and page extraction. "
            "Searches the internet via DuckDuckGo and Bing for latest information. "
            "Extracts clean text content from web pages with boilerplate removal. "
            "Provides specialized financial news search across multiple queries. "
            "Use this skill when the agent needs to find current information, news, "
            "or read web page content from the open internet."
        ),
        "markdown": """\
---
name: web-fetch-skill
description: "Web information retrieval skill. Searches the internet via DuckDuckGo and Bing, extracts clean text from web pages, and provides specialized financial news search."
compatibility: "Requires AWS Bedrock AgentCore Runtime, Python 3.12, httpx"
metadata:
  version: "5.0.0"
  author: "Securities Trading Agent Platform"
  category: "finance"
---

# Web Fetch Skill

## Overview
General-purpose web information retrieval skill. Uses DuckDuckGo HTML search as primary source with Bing as fallback. Extracts clean article text from web pages by removing scripts, styles, navigation, and boilerplate. Includes a specialized financial news search that queries multiple angles (news, analyst reports, earnings announcements) for comprehensive coverage.

## Tools
- web_search: Search the internet using DuckDuckGo and Bing. Returns titles, URLs, and snippets. Configurable max results (default 8).
- fetch_web_page: Fetch and extract clean text content from a URL. Removes HTML tags, scripts, styles, and common boilerplate. Configurable max length (default 5000 chars).
- search_financial_news: Specialized financial news search. Queries multiple angles (latest news, analyst reports, earnings) and deduplicates results. Returns up to 12 results.

## Usage
Use web_search for general information queries. Use fetch_web_page to read the full content of a specific URL found via search. Use search_financial_news when the user asks about company news, market events, or analyst opinions.

## Examples
- "Search for latest semiconductor industry news" -> web_search("semiconductor industry latest news")
- "Read this article" -> fetch_web_page("https://example.com/article")
- "Find news about CATL" -> search_financial_news("CATL")
""",
    },
    # ── 4. trading-skill ──────────────────────────────────────────
    {
        "name": "trading-skill",
        "description": (
            "Simulated trading execution skill for A-share paper trading. "
            "Executes buy/sell orders with realistic commission, stamp tax, and "
            "transfer fee calculations. Generates trading signals with confidence "
            "scores, target prices, and stop-loss levels. Calculates position sizing "
            "based on risk preference. Evaluates strategy conditions against technical "
            "indicators. Use this skill when the agent needs to execute trades, "
            "generate signals, or manage positions."
        ),
        "markdown": """\
---
name: trading-skill
description: "Simulated trading execution skill. Executes paper trades with realistic fee calculations, generates trading signals, calculates position sizing, and evaluates strategy conditions."
compatibility: "Requires AWS Bedrock AgentCore Runtime, Python 3.12"
metadata:
  version: "5.0.0"
  author: "Securities Trading Agent Platform"
  category: "finance"
---

# Trading Skill

## Overview
Provides simulated (paper) trading capabilities for A-share stocks. Executes orders with realistic Chinese market fee structures (commission at 0.03% min 5 CNY, stamp tax at 0.1% sell-side, transfer fee at 0.002%). Generates trading signals with confidence scoring and risk/reward analysis. Calculates position sizes based on conservative/moderate/aggressive risk profiles. Evaluates multi-indicator strategy conditions to produce buy/sell/hold decisions.

## Tools
- execute_simulated_order: Execute a simulated buy/sell order. Validates quantity (must be multiple of 100), calculates all fees, returns order confirmation with total cost breakdown.
- generate_trading_signal: Create a trading signal with stock info, signal type (buy/sell/hold), target price, stop-loss, confidence level, and computed risk/reward ratio.
- calculate_position_size: Compute recommended position size given available cash, stock price, and risk preference. Returns suggested shares (rounded to 100-lot) and estimated cost.
- evaluate_strategy_conditions: Evaluate technical indicator conditions (MA trend, MACD cross, RSI levels, Bollinger position) and produce a composite buy/sell/hold decision with supporting signals.

## Usage
Use execute_simulated_order when the user confirms a trade. Use generate_trading_signal to propose trades based on analysis. Use calculate_position_size before executing to determine appropriate trade size. Use evaluate_strategy_conditions to check if a stock meets strategy entry/exit criteria.

## Examples
- "Buy 500 shares of 600519 at 1680" -> execute_simulated_order("portfolio-1", "600519", "Moutai", "buy", 1680.0, 500)
- "Generate a buy signal for 000858" -> generate_trading_signal("000858", "Wuliangye", "buy", 155.0, 170.0, 148.0, 0.75, "MACD golden cross")
- "How many shares should I buy with 100k?" -> calculate_position_size(100000, 155.0, "moderate")
""",
    },
    # ── 5. quant-skill ────────────────────────────────────────────
    {
        "name": "quant-skill",
        "description": (
            "Quantitative strategy backtesting engine for A-share stocks. "
            "Runs user-defined Python strategy code against historical K-line data. "
            "Provides preset strategy templates (dual MA cross, MACD momentum, "
            "Bollinger breakout, RSI, multi-factor, turtle trading). Calculates "
            "comprehensive performance metrics including Sharpe, Sortino, Calmar "
            "ratios, max drawdown, and win rate. Use this skill for backtesting "
            "and quantitative strategy evaluation."
        ),
        "markdown": """\
---
name: quant-skill
description: "Quantitative strategy backtesting engine. Runs Python strategies against K-line history, provides preset templates, and calculates Sharpe/Sortino/Calmar ratios, max drawdown, win rate."
compatibility: "Requires AWS Bedrock AgentCore Runtime, Python 3.12, numpy, pandas"
metadata:
  version: "5.0.0"
  author: "Securities Trading Agent Platform"
  category: "finance"
---

# Quant Skill

## Overview
Full-featured quantitative strategy backtesting engine. Accepts user-defined Python strategy code with initialize() and handle_data() functions. Simulates order execution against historical K-line data with configurable initial capital. Tracks equity curve, trade log, and computes comprehensive performance metrics. Includes 6 preset strategy templates covering trend-following, momentum, mean-reversion, and multi-factor approaches.

## Tools
- run_backtest: Execute a quantitative strategy backtest. Takes strategy Python code, parameters, K-line data, and initial capital. Returns total/annual return, max drawdown, Sharpe ratio, win rate, trade log, and equity curve.
- list_quant_templates: List all preset strategy templates with name, description, category, and difficulty level. Templates include dual MA cross, MACD momentum, Bollinger breakout, RSI overbought/oversold, multi-factor, and turtle trading.
- calculate_performance_metrics: Compute detailed performance metrics from an equity curve. Returns total return, annual return, max drawdown, Sharpe ratio, Sortino ratio, Calmar ratio, and annualized volatility.

## Usage
Use list_quant_templates to show available strategies. Use run_backtest with strategy code and historical K-line data (minimum 30 bars required). Use calculate_performance_metrics to analyze any equity curve independently.

## Examples
- "Show me available quant strategies" -> list_quant_templates()
- "Backtest dual MA cross on 600519 daily data" -> run_backtest(strategy_code, params, kline_data, 1000000)
- "Calculate performance metrics for this equity curve" -> calculate_performance_metrics(equity_curve)
""",
    },
    # ── 6. notification-skill ─────────────────────────────────────
    {
        "name": "notification-skill",
        "description": (
            "Multi-channel trading signal notification skill. Sends formatted "
            "trading signal alerts via SES email with detailed signal information "
            "including stock, price, target, stop-loss, confidence, and risk/reward. "
            "Supports push notifications via WebSocket queue and SMS (reserved). "
            "Formats daily investment reports with portfolio summary, signals, and "
            "market overview. Use this skill to notify users of trading signals "
            "or deliver daily reports."
        ),
        "markdown": """\
---
name: notification-skill
description: "Multi-channel trading signal notification skill. Sends alerts via SES email with signal details. Supports push notifications and formats daily investment reports."
compatibility: "Requires AWS Bedrock AgentCore Runtime, Python 3.12, SMTP/SES configuration"
metadata:
  version: "5.0.0"
  author: "Securities Trading Agent Platform"
  category: "finance"
---

# Notification Skill

## Overview
Delivers trading signal notifications and daily investment reports through multiple channels. Email notifications use SMTP/SES with rich formatted content including stock details, signal type, prices, confidence, and risk warnings. Push notifications are queued to Redis for WebSocket delivery to the frontend. Daily reports combine portfolio summary, trading signals, and market overview into a formatted text report.

## Tools
- send_trading_signal_notification: Send a trading signal alert through specified channels (email, push, sms). Formats signal data into a detailed notification with stock info, prices, confidence, and risk disclaimer. Requires signal_data dict and channel list.
- format_daily_report: Generate a formatted daily investment report. Combines portfolio summary (total value, cash, profit), today's trading signals, and market overview into a structured text report with emoji formatting.

## Usage
Use send_trading_signal_notification after generating a trading signal to alert the user. Use format_daily_report at end of trading day to summarize portfolio performance and signals. Email channel requires SMTP configuration in environment.

## Examples
- "Notify me about this buy signal" -> send_trading_signal_notification(signal_data, ["email", "push"], "user@example.com")
- "Generate today's daily report" -> format_daily_report(portfolio_summary, signals, market_summary)
""",
    },
    # ── 7. crawler-skill ──────────────────────────────────────────
    {
        "name": "crawler-skill",
        "description": (
            "Professional financial web crawler skill for Chinese market data. "
            "Crawls Eastmoney, Sina Finance, and Cailian Press for news and telegrams. "
            "Retrieves stock research reports with analyst ratings from Eastmoney. "
            "Supports deep web page scraping with article, link, and table extraction "
            "modes. Collects industry sector data and capital flow information. "
            "Use this skill for structured financial data collection from Chinese "
            "financial websites."
        ),
        "markdown": """\
---
name: crawler-skill
description: "Professional financial web crawler. Crawls Eastmoney, Sina Finance, and Cailian Press for news, research reports, deep web scraping, and industry sector data with capital flow."
compatibility: "Requires AWS Bedrock AgentCore Runtime, Python 3.12, httpx"
metadata:
  version: "5.0.0"
  author: "Securities Trading Agent Platform"
  category: "finance"
---

# Crawler Skill

## Overview
Specialized financial data crawlers for major Chinese financial websites. Includes dedicated parsers for Eastmoney (news search, research reports, sector capital flow), Sina Finance (news search), and Cailian Press (real-time telegraph/flash news). Supports deep web page scraping with multiple extraction modes (article text, hyperlinks, HTML tables). Provides industry-level data aggregation combining news and sector fund flow analysis.

## Tools
- crawl_financial_news: Crawl financial news from multiple sources (Eastmoney, Sina, Cailian Press). Supports source selection (all/eastmoney/sina/cls) and configurable result count per source.
- crawl_stock_reports: Retrieve research reports for a specific stock from Eastmoney. Returns report titles, issuing institutions, authors, dates, and ratings.
- crawl_web_page_deep: Deep scrape any web page with extraction modes: article (main content text), full (all text), links (hyperlink list), tables (HTML table data).
- crawl_industry_data: Collect industry-level data including sector news and capital flow direction for a given industry keyword.
- list_available_crawlers: List all preset crawler adapters with descriptions and types (news, realtime, research, general, industry, custom).

## Usage
Use crawl_financial_news for broad market news gathering. Use crawl_stock_reports for individual stock research. Use crawl_web_page_deep when you need structured data from a specific URL. Use crawl_industry_data for sector-level analysis.

## Examples
- "Get latest news about Moutai" -> crawl_financial_news("Moutai", "all", 10)
- "Find research reports for 002167" -> crawl_stock_reports("002167")
- "Extract tables from this page" -> crawl_web_page_deep("https://example.com", "tables")
- "Get semiconductor industry data" -> crawl_industry_data("semiconductor")
""",
    },
    # ── 8. browser-crawler-skill ──────────────────────────────────
    {
        "name": "browser-crawler-skill",
        "description": (
            "AgentCore Browser-based web browsing and data collection skill. "
            "Uses headless browser with JavaScript rendering for dynamic pages. "
            "Supports Web Bot Auth for authenticated access to financial portals. "
            "Handles SPAs, lazy-loaded content, and interactive page elements. "
            "Ideal for scraping modern financial websites that require JS execution. "
            "Use this skill when static HTTP crawlers cannot access the needed content."
        ),
        "markdown": """\
---
name: browser-crawler-skill
description: "AgentCore Browser-based web browsing and data collection. Uses headless browser with JS rendering, Web Bot Auth for authenticated access, and dynamic page interaction for modern financial websites."
compatibility: "Requires AWS Bedrock AgentCore Runtime, Python 3.12, AgentCore Browser resource"
metadata:
  version: "5.0.0"
  author: "Securities Trading Agent Platform"
  category: "finance"
---

# Browser Crawler Skill

## Overview
Leverages AgentCore Browser (headless Chromium) for web browsing and data collection on dynamic, JavaScript-rendered pages. Unlike static HTTP crawlers, this skill can interact with SPAs, handle lazy-loaded content, execute JavaScript, and navigate multi-step workflows. Supports Web Bot Auth (browser signing) for authenticated access to financial data portals that verify bot identity. Configured in PUBLIC network mode for unrestricted internet access.

## Tools
- browse_and_extract: Navigate to a URL using AgentCore Browser, wait for JavaScript rendering, and extract page content. Supports CSS selectors for targeted extraction and configurable wait times for dynamic content.
- interact_with_page: Perform browser interactions (click, type, scroll, wait) on a loaded page. Useful for navigating paginated data, filling search forms, or expanding collapsed sections.
- capture_page_snapshot: Take a full-page screenshot or capture specific element screenshots for visual analysis and debugging.
- collect_dynamic_data: Automated data collection workflow that navigates, interacts, and extracts structured data from dynamic financial pages (e.g., real-time trading dashboards, interactive charts).

## Usage
Use this skill when the target website requires JavaScript execution, user interaction, or authenticated access. Prefer the static crawler-skill for simple HTML pages. Use browse_and_extract for single-page data retrieval. Use interact_with_page for multi-step navigation. Use collect_dynamic_data for automated scraping workflows.

## Examples
- "Browse the Eastmoney stock page for 600519" -> browse_and_extract("https://quote.eastmoney.com/sh600519.html", selector=".stock-info")
- "Click the next page button" -> interact_with_page(action="click", selector=".next-page")
- "Collect real-time data from trading dashboard" -> collect_dynamic_data(url, extraction_config)
""",
    },
    # ── 9. code-interpreter-skill ─────────────────────────────────
    {
        "name": "code-interpreter-skill",
        "description": (
            "AgentCore Code Interpreter for sandboxed Python code execution. "
            "Runs data analysis, visualization, and quantitative computing in an "
            "isolated environment with numpy, pandas, matplotlib, scipy pre-installed. "
            "Generates charts, processes CSV/Excel data, performs statistical analysis, "
            "and executes custom quantitative models. Use this skill when the agent "
            "needs to run arbitrary Python code for analysis or visualization."
        ),
        "markdown": """\
---
name: code-interpreter-skill
description: "AgentCore Code Interpreter for sandboxed Python execution. Runs data analysis, visualization, and quantitative computing with numpy/pandas/matplotlib/scipy in an isolated environment."
compatibility: "Requires AWS Bedrock AgentCore Runtime, Python 3.12, AgentCore Code Interpreter resource"
metadata:
  version: "5.0.0"
  author: "Securities Trading Agent Platform"
  category: "finance"
---

# Code Interpreter Skill

## Overview
Provides sandboxed Python code execution through AgentCore Code Interpreter. Runs in an isolated environment with PUBLIC network access and pre-installed scientific computing libraries (numpy, pandas, matplotlib, scipy, scikit-learn). Ideal for data analysis, chart generation, statistical modeling, and custom quantitative computations that go beyond the preset tools. Configured in PUBLIC network mode for package installation and data fetching.

## Tools
- execute_code: Run arbitrary Python code in the sandboxed interpreter. Returns stdout, stderr, and any generated files (charts, CSVs). Supports multi-cell execution for iterative analysis.
- upload_data: Upload data files (CSV, Excel, JSON) to the interpreter environment for processing. Returns the file path in the sandbox for use in subsequent code execution.
- download_result: Download generated files (charts, processed data, reports) from the interpreter environment. Returns file content or download URL.
- install_package: Install additional Python packages in the interpreter environment using pip. Useful for specialized libraries not pre-installed.

## Usage
Use execute_code for custom analysis that existing skills cannot handle (e.g., complex statistical models, custom visualizations, data transformations). Use upload_data to provide datasets, then execute_code to process them. Use download_result to retrieve generated charts or processed files.

## Examples
- "Plot a candlestick chart for this K-line data" -> execute_code("import matplotlib.pyplot as plt\\n...")
- "Calculate correlation matrix for these stocks" -> execute_code("import pandas as pd\\ndf = pd.DataFrame(data)\\ndf.corr()")
- "Run a Monte Carlo simulation for portfolio risk" -> execute_code(monte_carlo_code)
""",
    },
]