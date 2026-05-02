---
name: market-data-skill
description: >
  Real-time stock market data from multiple sources (Tencent, Sina, Yahoo Finance).
  Provides real-time quotes, batch quotes, K-line history, stock search with pinyin support,
  and market indices. Use when user asks about stock prices, market data, or needs historical K-line data.
license: Apache-2.0
compatibility: Requires internet access for market data APIs.
metadata:
  version: "2.0.0"
  author: securities-trading-platform
  category: market
allowed-tools: get_stock_realtime_quote get_stock_batch_quotes get_stock_kline search_stocks list_market_data_sources
---

# Market Data Skill

Provides comprehensive A-share market data from multiple sources.

## Tools

### get_stock_realtime_quote(stock_code, source)
Get real-time quote for a single stock. Returns price, change, volume, PE ratio, etc.
- stock_code: e.g. "600519", "sh600519"
- source: "tencent" (default), "sina", "yahoo"

### get_stock_batch_quotes(stock_codes, source)
Get quotes for multiple stocks at once.
- stock_codes: comma-separated, e.g. "600519,000858,300750"

### get_stock_kline(stock_code, period, count)
Get K-line (candlestick) history data.
- period: "day", "week", "month"
- count: number of bars (default 60)

### search_stocks(keyword)
Search stocks by code, name, or pinyin. Returns matching stocks with code, name, market.

### list_market_data_sources()
List available data sources and their capabilities.

## Examples
- "查询贵州茅台实时行情" -> get_stock_realtime_quote("600519")
- "批量查询宁德时代、比亚迪" -> get_stock_batch_quotes("300750,002594")
- "获取600519日K线数据" -> get_stock_kline("600519", "day", 120)
