---
name: analysis-skill
description: >
  Multi-timeframe technical analysis (daily/weekly/monthly) with MA, MACD, RSI, KDJ, BOLL indicators.
  Generates professional investment reports with scoring and recommendations.
  Use when user asks for technical analysis, investment reports, or stock evaluation.
license: Apache-2.0
compatibility: Requires market-data-skill for K-line data.
metadata:
  version: "2.0.0"
  author: securities-trading-platform
  category: analysis
allowed-tools: analyze_technical_indicators generate_investment_report
---

# Analysis Skill

Professional securities technical analysis across multiple timeframes.

## Tools

### analyze_technical_indicators(stock_code)
Multi-timeframe technical analysis. Returns indicators for daily, weekly, and monthly timeframes:
- MA5/MA10/MA20/MA60 with trend detection (bullish/bearish/neutral)
- MACD (DIF, DEA, signal: golden cross/death cross)
- RSI(14) with overbought/oversold status
- KDJ (K, D, J values with cross signals)
- Bollinger Bands (upper/mid/lower with position)

### generate_investment_report(stock_code, stock_name, quote_data, technical_data)
Generate a scored investment report with composite score (0-100) and recommendation (buy/hold/sell).

## Output Format
Reports should use Markdown tables for all data. No emoji. Professional tone.

## Examples
- "分析贵州茅台技术指标" -> analyze_technical_indicators("600519")
- Returns data for 日线/周线/月线 with all indicators in structured dict
