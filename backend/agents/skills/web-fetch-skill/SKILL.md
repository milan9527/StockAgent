---
name: web-fetch-skill
description: >
  Web search and content extraction for financial information. Searches the internet,
  fetches web pages, and finds financial news. Use when user needs latest news,
  research reports, policy updates, or any web-based information.
license: Apache-2.0
compatibility: Requires internet access.
metadata:
  version: "1.0.0"
  author: securities-trading-platform
  category: web
allowed-tools: web_search fetch_web_page search_financial_news
---

# Web Fetch Skill

Internet search and content extraction for financial research.

## Tools

### web_search(query, max_results)
Search the internet using search engines. Returns titles, URLs, and snippets.

### fetch_web_page(url)
Fetch and extract text content from a specific URL. Strips HTML, returns clean text.

### search_financial_news(query)
Search specifically for financial news from major sources.

## Examples
- "搜索新能源行业最新政策" -> web_search("新能源行业最新政策 2025")
- "获取这个网页内容" -> fetch_web_page("https://finance.sina.com.cn/...")
