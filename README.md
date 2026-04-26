# 证券交易助手 Agent 平台

AI-powered securities trading assistant platform built on **Strands Agent SDK** and **AWS Bedrock AgentCore**, featuring investment analysis, stock trading, and quantitative backtesting.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Frontend (React 18 + Vite)                          │
│  Dashboard │ 投资分析 │ 行情 │ 模拟盘 │ 交易策略 │ 量化 │ AI助手 │ Skills │ 扫描 │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ HTTPS (/api/*)
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                    Amazon CloudFront (OAC → S3 + ALB)                       │
│  /* → S3 (sec-trading-web-app-prod)                                         │
│  /api/* → ALB (securities-trading-alb) → ECS Fargate                        │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                    ECS Fargate Backend (FastAPI)                             │
│  Auth │ Market │ Portfolio │ Strategy │ Quant │ Chat │ Skills │ Scanning     │
│                                                                             │
│  Skills (直接执行):                                                          │
│  market_data │ analysis │ web_fetch │ crawler │ trading │ quant │ notify     │
│                                                                             │
│  AI Chat/Analysis → invoke_runtime_agent() ─────────────────────┐           │
└──────┬──────────────┬───────────────────────────────────────────┼───────────┘
       │              │                                           │
┌──────▼──────┐ ┌─────▼────────────┐                    ┌────────▼───────────┐
│ Aurora      │ │ ElastiCache      │                    │ AgentCore Runtime  │
│ PostgreSQL  │ │ Redis (TLS)      │                    │ SecuritiesTrading  │
│ Serverless  │ │ Serverless       │                    │ Agent              │
│ v2          │ │                  │                    │                    │
│ 12 tables   │ │ Quote cache 10s  │                    │ ┌────────────────┐ │
│ Users       │ │ K-line cache 60s │                    │ │ Orchestrator   │ │
│ Stocks      │ │                  │                    │ │ (Agent-as-Tool)│ │
│ Portfolios  │ │                  │                    │ │                │ │
│ Strategies  │ │                  │                    │ │ Sub-Agents:    │ │
│ Orders      │ │                  │                    │ │ • Analyst      │ │
│ Reports     │ │                  │                    │ │ • Trader       │ │
│ Skills      │ │                  │                    │ │ • Quant        │ │
└─────────────┘ └──────────────────┘                    │ │                │ │
                                                        │ │ Tools:         │ │
┌───────────────────────────────────────────┐           │ │ • Browser ✅   │ │
│ AgentCore Services                        │           │ │ • CodeInterp ✅│ │
│                                           │           │ └────────────────┘ │
│ Memory (STM + LTM)                        │◄──────────│                    │
│ ├─ SessionSummarizer                      │           │ OTEL Tracing       │
│ ├─ InvestmentPreferenceLearner            │           │ Persistent Storage │
│ └─ TradingKnowledgeEvolution (SCOPE)      │           │ /mnt/reports       │
│                                           │           └────────────────────┘
│ Registry (9 Skills + external)            │                    │
│ ├─ market-data-skill                      │                    │
│ ├─ analysis-skill                         │              ┌─────▼─────┐
│ ├─ web-fetch-skill                        │              │ Bedrock   │
│ ├─ crawler-skill                          │              │ Claude    │
│ ├─ trading-skill                          │              │ Sonnet    │
│ ├─ quant-skill                            │              │ 4.6       │
│ ├─ notification-skill                     │              └───────────┘
│ ├─ browser-crawler-skill                  │
│ └─ code-interpreter-skill                 │
│                                           │
│ Browser (Public + Web Bot Auth)           │
│ Code Interpreter (Public)                 │
│ Observability (OTEL → CloudWatch)         │
└───────────────────────────────────────────┘
```

## Key Features

### 1. Investment Analysis (投资分析)
- Quick technical analysis: MA, MACD, RSI, Bollinger Bands
- AI-powered deep research via AgentCore Runtime
- Professional financial crawlers (东方财富, 新浪, 财联社)
- Stock research reports from broker analysts
- Web search for latest news and announcements
- Analysis templates: stock, sector, market overview, comparison, risk

### 2. Market Data (行情)
- Multi-source realtime quotes: Tencent (default), Sina, Yahoo Finance
- Candlestick K-line charts with MA/Bollinger/Volume indicators
- Buy/Sell 5-level order book
- Market indices: 上证指数, 深圳成指, 创业板指
- Watchlist management with auto-refresh (10s interval)
- Stock search with pinyin autocomplete

### 3. Simulated Trading (模拟盘)
- Paper trading with realistic commission/tax calculation
- Stock search autocomplete with realtime price display
- 5-level order book for price selection
- Position tracking and P&L calculation
- Order history

### 4. Trading Strategy (交易策略)
- Create/edit strategies with technical indicators
- Buy/sell conditions and risk rules
- Strategy status management (draft/active/paused)

### 5. Quantitative Trading (量化交易)
- 6 preset templates (幻方量化 style): Dual MA, MACD, Bollinger, RSI, Multi-factor, Turtle
- Custom strategy code editor
- Historical backtesting engine
- Performance metrics: Sharpe, Sortino, Calmar, max drawdown, win rate
- Equity curve visualization

### 6. AI Assistant (AI助手) — Agent Playground
- Chat with AgentCore Runtime agent (Claude Sonnet 4.6)
- **Skill Control Panel**: toggle 9+ skills on/off
- **Smart Select**: AgentCore Registry semantic search auto-selects relevant skills
- **Agent presets**: Orchestrator, Analyst, Trader, Quant with skill presets
- Conversation stored in AgentCore Memory (STM + LTM)
- SCOPE self-evolution: agent learns from interactions
- Browser and Code Interpreter tools available

### 7. Skills Management
- 9 built-in skills + external imports
- Import from URL (GitHub) or MCP/pip
- Auto-publish to AgentCore Registry with approval workflow
- LLM-powered security scanning (4 dimensions: security, compliance, compatibility, license)

### 8. Settings
- LLM model switching (9 models: Claude 4.x, Nova, Haiku)
- Max tokens configuration (4K-64K slider)
- Data source management

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS, Recharts, Vite |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2 |
| Agent SDK | Strands Agents SDK, Agent-as-Tool pattern |
| Runtime | AWS Bedrock AgentCore Runtime (ARM64, VPC) |
| LLM | Bedrock Claude Sonnet 4.6 (default), 9 models available |
| Memory | AgentCore Memory (STM + LTM, SCOPE self-evolution) |
| Registry | AgentCore Registry (13 skill records, semantic search) |
| Browser | AgentCore Browser (Public, Web Bot Auth) |
| Code Exec | AgentCore Code Interpreter (Public) |
| Observability | AgentCore Observability (OTEL → CloudWatch) |
| Storage | AgentCore Runtime Persistent Filesystems (/mnt/reports) |
| Database | Amazon Aurora PostgreSQL Serverless v2 |
| Cache | Amazon ElastiCache Redis Serverless (TLS) |
| Hosting | CloudFront + S3 (frontend), ECS Fargate + ALB (backend) |
| Auth | JWT + Amazon Cognito (optional) |

## Workflow

### AI Assistant Flow
```
User message
  → Frontend (ChatPage with Skill Control)
  → POST /api/chat/ (ECS Fargate)
  → Smart Select: SearchRegistryRecords (semantic match)
  → invoke_runtime_agent() → AgentCore Runtime
    → Registry Smart Select (inject matched skills into prompt)
    → Orchestrator Agent (Claude 4.6)
      → Routes to sub-agent or direct tool
      → Browser / Code Interpreter / Skills
    → Memory: STM saves conversation, LTM extracts knowledge
  → Response (Markdown) → Frontend renders
```

### Investment Analysis Flow
```
Quick Analysis: Stock code → realtime quote + K-line → technical indicators → report
Deep Analysis:  Stock code → AgentCore Runtime
                  → crawl_financial_news (东方财富/新浪/财联社)
                  → crawl_stock_reports (broker research)
                  → web_search (latest news)
                  → analyze_technical_indicators
                  → Browser (dynamic pages) / Code Interpreter (data analysis)
                  → Generate professional report
```

## Local Development

### Prerequisites
- Python 3.12+, Node.js 18+, PostgreSQL 16+, Redis 6+
- AWS credentials configured (`aws configure`)
- Bedrock model access enabled (Claude Sonnet 4.6)

### Setup
```bash
# 1. Start databases
sudo systemctl start postgresql redis6

# 2. Create database
sudo -u postgres psql -c "CREATE DATABASE securities_trading OWNER postgres;"

# 3. Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .
cp env/local.env .env  # or env/aws.env for AWS services
python -m db.seed      # Initialize seed data
python main.py         # http://localhost:8000

# 4. Frontend
cd frontend
npm install
npm run dev -- --host 0.0.0.0  # http://localhost:3000

# 5. Access via SSH tunnel
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 ec2-user@<ip>
```

### Default accounts
- demo / demo123456
- admin / admin123456

## AWS Deployment

### Infrastructure (already deployed in us-east-1)

| Resource | Details |
|----------|---------|
| Aurora PostgreSQL | `securities-trading-aurora` (Serverless v2, VPC-only SG) |
| ElastiCache Redis | `securities-trading-redis` (Serverless, TLS, VPC-only SG) |
| ECS Fargate | `securities-trading` cluster, `backend` service (ARM64, 1vCPU/2GB) |
| ALB | `securities-trading-alb` → ECS target group (port 8000) |
| ECR | `securities-trading-backend` (Docker image) |
| CloudFront | `dt0u20qd1sod9.cloudfront.net` (OAC→S3 + /api/*→ALB) |
| S3 | `sec-trading-web-app-prod` (private, OAC only) |
| AgentCore Runtime | `SecuritiesTradingAgent-Ma2PoA8Zw8` (Public network) |
| AgentCore Memory | `SecuritiesTradingMemory-PhU3ojCYpp` (STM+LTM, 3 strategies) |
| AgentCore Registry | `Eea8hqxihmpeJlYv` (13 records, all APPROVED) |
| AgentCore Browser | `SecuritiesTradingBrowser` (Public + Web Bot Auth) |
| AgentCore Code Interpreter | `SecuritiesTradingCodeInterpreter-wGp9YodWEL` |
| Cognito | `us-east-1_DpOE0uo8p` (optional, self-signup disabled) |

### Deploy Commands
```bash
# Frontend → S3 + CloudFront
cd frontend && npm run build
aws s3 sync dist/ s3://sec-trading-web-app-prod/ --delete
aws cloudfront create-invalidation --distribution-id EFHJYSE515D2O --paths "/*"

# Backend → ECR + ECS Fargate
cd backend
docker build -t securities-trading-backend .
docker tag securities-trading-backend:latest 632930644527.dkr.ecr.us-east-1.amazonaws.com/securities-trading-backend:latest
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 632930644527.dkr.ecr.us-east-1.amazonaws.com
docker push 632930644527.dkr.ecr.us-east-1.amazonaws.com/securities-trading-backend:latest
aws ecs update-service --cluster securities-trading --service backend --force-new-deployment

# AgentCore Runtime
agentcore deploy --auto-update-on-conflict

# Full infrastructure setup
python infra/deploy_aws.py plan    # Preview
python infra/deploy_aws.py deploy  # Deploy all
python infra/deploy_aws.py status  # Check status
```

### Security Groups
```
ALB SG (sg-alb)         : TCP 80 ← 0.0.0.0/0
ECS SG (sg-ecs)         : TCP 8000 ← ALB SG
Aurora SG (sg-aurora)   : TCP 5432 ← VPC CIDR + ECS SG + Runtime SG
Redis SG (sg-redis)     : TCP 6379 ← VPC CIDR + ECS SG + Runtime SG
Runtime SG (sg-runtime) : outbound all
```

## Project Structure
```
├── backend/
│   ├── agents/
│   │   ├── orchestrator_agent.py    # Main agent (AgentCore Runtime entry)
│   │   ├── investment_analyst_agent.py
│   │   ├── stock_trading_agent.py
│   │   ├── quant_trading_agent.py
│   │   ├── model_loader.py          # 9 LLM models
│   │   ├── runtime_client.py        # AgentCore Runtime invoke client
│   │   └── skills/
│   │       ├── market_data_skill.py # Multi-source quotes, K-line, order book
│   │       ├── analysis_skill.py    # Technical indicators, reports
│   │       ├── web_fetch_skill.py   # Web search (DDG + Bing)
│   │       ├── crawler_skill.py     # Financial crawlers (东方财富/新浪/财联社)
│   │       ├── trading_skill.py     # Simulated trading, signals
│   │       ├── quant_skill.py       # Backtesting engine, 6 templates
│   │       └── notification_skill.py # SES email, push notifications
│   ├── api/routes/
│   │   ├── auth_routes.py           # JWT + Cognito auth
│   │   ├── chat_routes.py           # AI chat + Smart Select
│   │   ├── market_routes.py         # Quotes, K-line, indices, order book
│   │   ├── portfolio_routes.py      # Simulated trading
│   │   ├── strategy_routes.py       # Trading + quant strategies
│   │   ├── analysis_routes.py       # Investment analysis + templates
│   │   ├── watchlist_routes.py      # Watchlist CRUD + autocomplete
│   │   ├── skill_routes.py          # Skills CRUD + Registry sync
│   │   ├── scanning_routes.py       # LLM security scanning
│   │   └── settings_routes.py       # LLM switch, max tokens
│   ├── db/
│   │   ├── database.py, models.py, redis_client.py, seed.py
│   ├── config/settings.py
│   ├── infra/setup_agentcore.py
│   ├── main.py, Dockerfile, .bedrock_agentcore.yaml
│   └── env/ (local.env, aws.env)
├── frontend/
│   └── src/pages/
│       ├── DashboardPage.tsx         # Indices + watchlist + portfolio
│       ├── AnalysisPage.tsx          # Quick + AI deep analysis
│       ├── MarketPage.tsx            # Quotes + K-line + watchlist
│       ├── PortfolioPage.tsx         # Trading with order book
│       ├── StrategyPage.tsx          # Trading strategies
│       ├── QuantPage.tsx             # Quant backtesting
│       ├── ChatPage.tsx              # Agent Playground + Skill Control
│       ├── SkillsPage.tsx            # Skills management
│       ├── ScanningPage.tsx          # LLM security scanning
│       └── SettingsPage.tsx          # LLM + data source config
├── infra/deploy_aws.py
├── docker-compose.yml
└── README.md
```

## Live URL
- **Frontend**: https://dt0u20qd1sod9.cloudfront.net
- **API Docs**: https://dt0u20qd1sod9.cloudfront.net/api/docs
- **CloudWatch**: [GenAI Observability Dashboard](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core)
