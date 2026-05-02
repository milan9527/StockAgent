---
name: quant-skill
description: >
  Quantitative strategy backtesting engine with preset templates (dual MA, RSI+MACD, Bollinger).
  Calculates performance metrics including Sharpe ratio, max drawdown, win rate.
  Use when user wants to backtest strategies or analyze quantitative performance.
license: Apache-2.0
compatibility: Requires numpy and pandas for calculations.
metadata:
  version: "1.0.0"
  author: securities-trading-platform
  category: quant
allowed-tools: run_backtest list_quant_templates calculate_performance_metrics
---

# Quant Skill

Quantitative strategy backtesting and performance analysis.

## Tools

### run_backtest(stock_code, strategy_name, start_date, end_date, initial_capital, params)
Run a backtest with specified strategy. Returns equity curve, trade log, and metrics.

### list_quant_templates()
List available strategy templates with descriptions and default parameters.

### calculate_performance_metrics(equity_curve, trade_log)
Calculate Sharpe ratio, max drawdown, annual return, win rate from backtest results.
