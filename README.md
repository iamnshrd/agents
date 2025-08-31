<!-- PROJECT SHIELDS -->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]


<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/polymarket/agents">
    <img src="docs/images/cli.png" alt="Logo" width="466" height="262">
  </a>

<h3 align="center">Polymarket Agents</h3>

  <p align="center">
    Trade autonomously on Polymarket using AI Agents with MCP integration
    <br />
    <a href="https://github.com/polymarket/agents"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/polymarket/agents">View Demo</a>
    ·
    <a href="https://github.com/polymarket/agents/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/polymarket/agents/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
  
  <p align="center">
    <strong>🚀 New Features:</strong> MCP Integration • Telegram Alerts • Dry-Run Trading • Performance Analytics
  </p>
</div>


<!-- CONTENT -->
# Polymarket Agents

Polymarket Agents is a developer framework and set of utilities for building AI agents for Polymarket.

This code is free and publicly available under MIT License open source license ([terms of service](#terms-of-service))!

## Features

- **🤖 AI Agents**: Autonomous trading on prediction markets
- **📊 Polymarket Integration**: Full API integration for market data and trading
- **🔍 MCP Integration**: Modern Model Context Protocol for data sourcing
  - **Tavily MCP**: Web search, data extraction, sentiment analysis
  - **The Verge News MCP**: High-quality technology news via Smithery
- **📱 Telegram Alerts**: Real-time notifications for trades, positions, and market updates
- **💾 Dry-Run Mode**: Safe trading simulation with virtual balance
- **📈 Performance Analytics**: Comprehensive trading performance metrics
- **🔐 Environment Configuration**: Secure parameter management via .env files
- **🛠️ CLI Interface**: Rich command-line interface for all operations
- **📚 RAG Support**: Retrieval-Augmented Generation with ChromaDB
- **🎯 Superforecasting**: LLM-powered market prediction tools

# Getting started

This repo is inteded for use with Python 3.9

1. Clone the repository

   ```
   git clone https://github.com/{username}/polymarket-agents.git
   cd polymarket-agents
   ```

2. Create the virtual environment

   ```
   virtualenv --python=python3.9 .venv
   ```

3. Activate the virtual environment

   - On Windows:

   ```
   .venv\Scripts\activate
   ```

   - On macOS and Linux:

   ```
   source .venv/bin/activate
   ```

4. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

5. Set up your environment variables:

   - Create a `.env` file in the project root directory

   ```
   cp .env.example .env
   ```

   - Add the following environment variables:

   ```
   # Core Trading
   POLYGON_WALLET_PRIVATE_KEY=""
   OPENAI_API_KEY=""
   
   # Telegram Integration
   TELEGRAM_BOT_TOKEN=""
   TELEGRAM_CHAT_ID=""
   
   # MCP Integration
   TAVILY_API_KEY=""
   SMITHERY_API_KEY=""
   
   # Trading Configuration (dry-run)
   TRADING_MODE=dry_run
   DRY_RUN_BALANCE=100000   # cents → $1000.00
   MAX_POSITION_SIZE=0.10   # 10% от баланса на сделку (кламп)
   RISK_PER_TRADE=0.02      # базовый риск, влияет на размер позиции
   ```

6. Load your wallet with USDC.

7. Try the command line interface...

   ```
   python scripts/python/cli.py
   ```

   Or just go trade! 

   ```
   # Single dry-run trade
   python -m agents.application.dry_run_trader

   # Continuous dry-run session (edit __main__ or call from CLI soon)
   # Example (Python REPL):
   # from agents.application.dry_run_trader import DryRunTrader
   # t = DryRunTrader(); t.run_session(num_trades=10, pause_secs=2.0)

   # Telegram bot (simple long-polling): commands /positions and /portfolio
   # Requires TELEGRAM_BOT_TOKEN and (optionally) TELEGRAM_CHAT_ID
   python -c "import asyncio; from agents.connectors.telegram import telegram_bot_poll; asyncio.run(telegram_bot_poll())"

## docker-compose

To run both the session trader and Telegram bot as services:

1. Build image locally:

   ```
   docker build -f Dockerfile -t polymarket-agents:latest .
   ```

2. Ensure your `.env` is in the repo root and contains required keys.

3. Start services:

   ```
   docker compose up -d
   ```

4. Logs:

   ```
   docker compose logs -f session
   docker compose logs -f telegram
   tail -f logs/trading.log
   ```

   # Legacy single-step example
   python agents/application/trade.py
   ```

8. Note: If running the command outside of docker, please set the following env var:

   ```
   export PYTHONPATH="."
   ```

   If running with docker is preferred, we provide the following scripts:

   ```
   ./scripts/bash/build-docker.sh
   ./scripts/bash/run-docker-dev.sh
   ```

## Architecture

The Polymarket Agents architecture features modular components that can be maintained and extended by individual community members.

### APIs & Connectors

Polymarket Agents connectors standardize data sources and order types.

- **`Chroma.py`**: ChromaDB for vectorizing news sources and other API data. Developers can add their own vector database implementations.

- **`Gamma.py`**: Defines `GammaMarketClient` class, which interfaces with the Polymarket Gamma API to fetch and parse market and event metadata. Methods to retrieve current and tradable markets, as well as defined information on specific markets and events.

- **`Polymarket.py`**: Defines a Polymarket class that interacts with the Polymarket API to retrieve and manage market and event data, and to execute orders on the Polymarket DEX. Includes methods for API key initialization, market and event data retrieval, and trade execution.

- **`Objects.py`**: Data models using Pydantic; representations for trades, markets, events, and related entities.

### **New MCP Connectors**

- **`tavily_mcp.py`**: Tavily MCP client for web search, data extraction, sentiment analysis, and market research.

- **`verge_news_mcp.py`**: The Verge News MCP client via Smithery for high-quality technology news and market insights.

- **`telegram.py`**: Telegram integration for real-time trading alerts, position updates, and market notifications.

### **Enhanced Trading Modules**

- **`enhanced_dry_run_trader.py`**: Advanced dry-run trader with MCP integration for market analysis and news sentiment.

- **`trading_config.py`**: Centralized configuration management for all trading parameters and MCP settings.

- **`trading_logger.py`**: Comprehensive logging system for trades, performance, and system events.

- **`performance_analyzer.py`**: Advanced analytics for trading performance, including PnL, Sharpe ratio, and drawdown analysis.

### Scripts

Files for managing your local environment, server set-up to run the application remotely, and cli for end-user commands.

`cli.py` is the primary user interface for the repo. Users can run various commands to interact with the Polymarket API, retrieve relevant news articles, query local data, send data/prompts to LLMs, and execute trades in Polymarkets.

## 🚀 New CLI Commands

### **Trading Operations**
- `dry-run-trade` - Execute a single dry-run trade
- `enhanced-dry-run-trade` - Execute trade with MCP analysis
- `enhanced-session` - Run multiple enhanced trades
- `show-positions` - Display current trading positions
- `show-portfolio` - Show portfolio performance
- `show-trade-history` - Display trading history

### **Configuration & Status**
- `show-config` - Display current configuration
- `show-mcp-status` - Check MCP server status
- `show-verge-news-status` - Check The Verge News MCP status
- `show-mcp-config` - Show MCP configuration for clients

### **Performance & Analytics**
- `performance-report` - Generate detailed performance report
- `performance-summary` - Show performance summary
- `export-performance` - Export performance data to JSON

### **News & Data**
- `test-mcp-search` - Test Tavily MCP search
- `test-verge-news-search` - Test The Verge News search
- `get-verge-daily-news` - Get today's news from The Verge

### **Legacy Commands**
- `get-all-markets` - Retrieve markets from Polymarket
- `ask-llm` - Ask questions to LLM
- `ask-polymarket-llm` - Ask questions with market context

Commands should follow this format:

`python scripts/python/cli.py command_name [attribute value] [attribute value]`

Example:

`get-all-markets`
Retrieve and display a list of markets from Polymarket, sorted by volume.

   ```
   python scripts/python/cli.py get-all-markets --limit <LIMIT> --sort-by <SORT_BY>
   ```

- limit: The number of markets to retrieve (default: 5).
- sort_by: The sorting criterion, either volume (default) or another valid attribute.

# Contributing

If you would like to contribute to this project, please follow these steps:

1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Submit a pull request.

Please run pre-commit hooks before making contributions. To initialize them:

   ```
   pre-commit install
   ```

# Related Repos

- [py-clob-client](https://github.com/Polymarket/py-clob-client): Python client for the Polymarket CLOB
- [python-order-utils](https://github.com/Polymarket/python-order-utils): Python utilities to generate and sign orders from Polymarket's CLOB
- [Polymarket CLOB client](https://github.com/Polymarket/clob-client): Typescript client for Polymarket CLOB
- [Langchain](https://github.com/langchain-ai/langchain): Utility for building context-aware reasoning applications
- [Chroma](https://docs.trychroma.com/getting-started): Chroma is an AI-native open-source vector database

# Prediction markets reading

- Prediction Markets: Bottlenecks and the Next Major Unlocks, Mikey 0x: https://mirror.xyz/1kx.eth/jnQhA56Kx9p3RODKiGzqzHGGEODpbskivUUNdd7hwh0
- The promise and challenges of crypto + AI applications, Vitalik Buterin: https://vitalik.eth.limo/general/2024/01/30/cryptoai.html
- Superforecasting: How to Upgrade Your Company's Judgement, Schoemaker and Tetlock: https://hbr.org/2016/05/superforecasting-how-to-upgrade-your-companys-judgment

# License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/Polymarket/agents/blob/main/LICENSE.md) file for details.

# Contact

For any questions or inquiries, please contact liam@polymarket.com or reach out at www.greenestreet.xyz

Enjoy using the CLI application! If you encounter any issues, feel free to open an issue on the repository.

# Terms of Service

[Terms of Service](https://polymarket.com/tos) prohibit US persons and persons from certain other jurisdictions from trading on Polymarket (via UI & API and including agents developed by persons in restricted jurisdictions), although data and information is viewable globally.


<!-- LINKS -->
[contributors-shield]: https://img.shields.io/github/contributors/polymarket/agents?style=for-the-badge
[contributors-url]: https://github.com/polymarket/agents/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/polymarket/agents?style=for-the-badge
[forks-url]: https://github.com/polymarket/agents/network/members
[stars-shield]: https://img.shields.io/github/stars/polymarket/agents?style=for-the-badge
[stars-url]: https://github.com/polymarket/agents/stargazers
[issues-shield]: https://img.shields.io/github/issues/polymarket/agents?style=for-the-badge
[issues-url]: https://github.com/polymarket/agents/issues
[license-shield]: https://img.shields.io/github/license/polymarket/agents?style=for-the-badge
[license-url]: https://github.com/polymarket/agents/blob/master/LICENSE.md
