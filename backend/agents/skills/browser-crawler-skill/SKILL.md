---
name: browser-crawler-skill
description: >
  AgentCore Browser for web browsing, dynamic page interaction, and data collection
  with Web Bot Auth. Use when web_search/crawler tools cannot get sufficient data,
  when pages require JavaScript rendering, or when user explicitly requests browser use.
license: Apache-2.0
compatibility: Requires AWS AgentCore Browser service (SecuritiesTradingBrowser with Web Bot Auth).
metadata:
  version: "4.0.0"
  author: securities-trading-platform
  category: web
  browser-id: SecuritiesTradingBrowser-F6aHtUeGkj
allowed-tools: browser
---

# Browser Crawler Skill

AgentCore managed Chrome browser for web automation and data collection.

## Usage Conditions (use sparingly - slower than web_search/crawler)
- User explicitly requests "use browser"
- web_search/crawler data is insufficient
- Target page requires JavaScript rendering
- Page requires login or authentication

## Tools

### browser(browser_input)
AgentCore Browser automation tool. Supports:
- init_session: Start a new browser session
- navigate: Go to a URL
- get_text: Extract text from page elements
- click: Click on elements
- type: Enter text into fields
- screenshot: Capture page screenshot
- close: End browser session
