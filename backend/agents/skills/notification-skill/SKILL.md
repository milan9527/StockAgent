---
name: notification-skill
description: >
  Multi-channel notification for trading signals and investment reports via AWS SES email.
  Use when user wants to send trading alerts, daily reports, or notifications.
license: Apache-2.0
compatibility: Requires AWS SES configured for email sending.
metadata:
  version: "4.0.0"
  author: securities-trading-platform
  category: notification
allowed-tools: send_trading_signal_notification format_daily_report
---

# Notification Skill

Trading signal notifications and report delivery via email.

## Tools

### send_trading_signal_notification(signal_data, recipient_email)
Send a trading signal notification via AWS SES email.

### format_daily_report(portfolio_data, market_data)
Format a daily investment summary report for email delivery.
