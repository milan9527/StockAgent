---
name: crawler-skill
description: >
  Professional financial web crawler for East Money, Sina Finance, Cailian Press.
  Crawls financial news, stock research reports, deep web pages, and industry data.
  Use when user needs comprehensive financial data from Chinese financial websites.
license: Apache-2.0
compatibility: Requires internet access to Chinese financial websites.
metadata:
  version: "4.0.0"
  author: securities-trading-platform
  category: web
allowed-tools: crawl_financial_news crawl_stock_reports crawl_web_page_deep crawl_industry_data list_available_crawlers
---

# Crawler Skill

Professional financial web crawling for A-share market research.

## Tools

### crawl_financial_news(source, keyword, limit)
Crawl financial news from East Money, Sina Finance, or Cailian Press.
- source: "eastmoney", "sina", "cailian"
- keyword: search keyword
- limit: max results

### crawl_stock_reports(stock_code, limit)
Crawl broker research reports and ratings for a specific stock.

### crawl_web_page_deep(url)
Deep crawl a web page extracting articles, links, tables, and structured data.

### crawl_industry_data(industry, data_type)
Crawl industry-level data including capital flow and sector performance.
