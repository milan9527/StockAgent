---
name: trading-skill
description: >
  Simulated stock trading with order execution, signal generation, position sizing,
  and strategy evaluation. Use when user wants to buy/sell stocks in simulation,
  check trading signals, or evaluate trading strategies.
license: Apache-2.0
compatibility: Requires PostgreSQL database for portfolio storage.
metadata:
  version: "1.0.0"
  author: securities-trading-platform
  category: trading
allowed-tools: execute_simulated_order generate_trading_signal calculate_position_size evaluate_strategy_conditions
---

# Trading Skill

Simulated trading execution and strategy management.

## Tools

### execute_simulated_order(stock_code, side, price, quantity)
Execute a simulated buy/sell order. Updates portfolio positions and cash balance.

### generate_trading_signal(stock_code, strategy_params)
Generate buy/sell/hold signals based on technical indicators and strategy rules.

### calculate_position_size(stock_code, risk_pct, stop_loss_pct)
Calculate optimal position size based on risk management rules.

### evaluate_strategy_conditions(stock_code, conditions)
Evaluate if current market conditions match strategy buy/sell rules.
