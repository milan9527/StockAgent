---
name: code-interpreter-skill
description: >
  AgentCore Code Interpreter for executing Python code, data analysis, visualization,
  and custom crawler generation. Use when user needs code execution, complex calculations,
  data processing, or when built-in crawlers need supplementing with custom programs.
license: Apache-2.0
compatibility: Requires AWS AgentCore Code Interpreter service.
metadata:
  version: "4.0.0"
  author: securities-trading-platform
  category: quant
  interpreter-id: SecuritiesTradingCodeInterpreter-wGp9YodWEL
allowed-tools: code_interpreter
---

# Code Interpreter Skill

AgentCore managed Python execution environment for data analysis and code execution.

## Tools

### code_interpreter(code)
Execute Python code in a sandboxed environment. Supports:
- Data analysis with pandas, numpy
- Web crawling with requests, BeautifulSoup
- Visualization with matplotlib
- Financial calculations
- Custom crawler program generation

## Use Cases
- Generate and run custom web crawlers when built-in crawlers are insufficient
- Complex financial calculations (Sharpe ratio, portfolio optimization)
- Data transformation and analysis
- Markdown to HTML conversion for reports
