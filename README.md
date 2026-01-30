# BTC Algo Trading

Algorithmic trading system for Bitcoin using backtested strategies.

## Overview

This project implements and backtests algorithmic trading strategies against historical BTC data, with the goal of automating trading via proven, data-driven approaches.

## Strategies

- **Momentum/Trend-Following** - 25-day lookback, Golden/Death Cross
- **Mean Reversion** - Bollinger Bands, RSI
- **Grid Trading** - Range-bound market automation
- **Hybrid** - 50/50 momentum + mean reversion portfolio

## Tech Stack

- **Freqtrade** - Bot framework with ML optimization
- **CCXT** - Exchange connectivity (108+ exchanges)
- **Python** - Core language
- **PostgreSQL** - Data storage

## Project Structure

```
btc-algo-trading/
├── strategies/          # Trading strategy implementations
├── data/               # Historical data (gitignored)
├── backtests/          # Backtest results and analysis
├── notebooks/          # Jupyter notebooks for research
├── config/             # Freqtrade configuration
└── docs/               # Documentation
```

## Getting Started

```bash
# Install Freqtrade
pip install freqtrade

# Download historical data
freqtrade download-data \
  --exchange binance \
  --pairs BTC/USDT \
  --timeframes 1m 1h 1d \
  --timerange 20170101-

# Run backtest
freqtrade backtesting \
  --strategy MomentumStrategy \
  --timerange 20200101-20231231
```

## Documentation

- [PLAN.md](PLAN.md) - Current project roadmap
- [AGENTS.md](AGENTS.md) - AI development guide
- [CONSTITUTION.md](CONSTITUTION.md) - Core principles

## Status

**Phase**: Planning & Data Acquisition
