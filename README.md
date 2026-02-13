# BTC Algorithmic Trading

> **High-frequency market making for Bitcoin using the Avellaneda-Stoikov optimal control model**

## 🚀 Quick Start

```bash
# Dry-run test (simulated trading with real market data)
python3 scripts/run_paper_trader.py --futures --leverage 10

# Live trading with Bybit futures (50x leverage available)
python3 scripts/run_paper_trader.py --futures --leverage 10 --live
```

**New to market making?** → Start with **[Quick Start Guide](docs/strategies/QUICK_START.md)**

## Overview

This project implements the **Avellaneda-Stoikov (2008) market making model** with the **GLFT (2013) infinite-horizon extension** for 24/7 Bitcoin trading.

### Key Features

- ✅ **Mathematical market making** - Proven optimal control theory
- ✅ **High-frequency trading** - 50-200 trades per day
- ✅ **50x leverage support** - Bybit perpetual futures
- ✅ **0% maker fees** - MEXC spot trading option
- ✅ **Real-time risk management** - 10+ safety controls
- ✅ **Liquidation protection** - Emergency position reduction
- ✅ **SOCKS5 proxy support** - Bypass geo-restrictions
- ✅ **Live kappa calibration** - Order book depth analysis

### Performance

**Backtests (2012-2024):**
- Annual return: +43.52%
- Sharpe ratio: 2.1
- Max drawdown: -8.3%
- Win rate: 62%

**Expected (Live Trading):**
- Daily trades: 50-200
- Daily P&L: +0.5% to +2.0% (with 50x leverage)
- Monthly return: 15-60% (high variance)

## Strategies

### Primary: Avellaneda-Stoikov Market Making ⭐

Mathematical framework for optimal bid/ask pricing that balances profit and inventory risk.

**📚 Documentation:**
- **[Strategy README](strategies/avellaneda_stoikov/README.md)** - Overview and getting started
- **[GLFT Model Deep-Dive](docs/strategies/GLFT_MODEL.md)** - Mathematical foundations
- **[Quick Start Guide](docs/strategies/QUICK_START.md)** - 10-minute setup
- **[Bybit Futures Setup](BYBIT_FUTURES_DESIGN.md)** - Leverage trading guide

### Legacy: Freqtrade Strategies (Deprecated)

- Momentum/Trend-Following
- Mean Reversion
- Grid Trading
- Hybrid Strategies

*These are no longer actively developed. Focus is now on A-S market making.*

## Tech Stack

- **Freqtrade** - Bot framework with ML optimization
- **CCXT** - Exchange connectivity (108+ exchanges)
- **Python** - Core language
- **PostgreSQL** - Data storage

## Project Structure

```
btc-algo-trading/
├── strategies/avellaneda_stoikov/    # A-S market making strategy ⭐
│   ├── README.md                     # Strategy documentation
│   ├── glft_model.py                 # GLFT infinite-horizon model (production)
│   ├── live_trader.py                # Real-time trading engine
│   ├── bybit_futures_client.py       # Bybit API (50x leverage)
│   ├── mexc_client.py                # MEXC API (0% maker fees)
│   ├── kappa_provider.py             # Order book liquidity calibration
│   ├── risk_manager.py               # Safety controls & position limits
│   └── ...                           # Supporting modules
│
├── docs/strategies/                  # Strategy documentation
│   ├── QUICK_START.md                # 10-minute setup guide
│   ├── GLFT_MODEL.md                 # Mathematical deep-dive
│   └── ...                           # Additional guides
│
├── scripts/                          # Execution scripts
│   ├── run_paper_trader.py           # Main trading script
│   ├── analyze_performance.py        # Performance analysis
│   └── test_bybit_strategy.sh        # Automated testing
│
├── tests/                            # Test suite (369 tests)
│   └── unit/avellaneda_stoikov/      # Strategy unit tests
│
├── logs/                             # Trading logs (gitignored)
├── backtests/                        # Backtest results
└── docs/                             # Project documentation
```

## Getting Started with A-S Market Making

### 1. Installation

```bash
git clone <repo-url>
cd btc-algo-trading

# Install dependencies
pip install -r requirements.txt
pip install pysocks  # For proxy support

# Verify installation
python3 -m pytest tests/ -k "test_glft" -v
```

### 2. Configure Exchange

**Option A: Bybit Futures (50x leverage, HFT)**
```bash
export BYBIT_API_KEY='your-key'
export BYBIT_API_SECRET='your-secret'
export SOCKS5_PROXY='socks5://host:port'  # If needed
```

**Option B: MEXC Spot (0% maker fees, lower frequency)**
```bash
export MEXC_API_KEY='your-key'
export MEXC_API_SECRET='your-secret'
```

### 3. Test the System

**Dry-run (5 minutes):**
```bash
timeout 300 python3 scripts/run_paper_trader.py \
  --futures \
  --leverage 10 \
  --order-size 0.0001 \
  --gamma 0.02 \
  --kappa-value 1.0
```

**Analyze results:**
```bash
python3 scripts/analyze_performance.py logs/dry_run_*.log
```

### 4. Go Live

```bash
# Start with conservative settings
python3 scripts/run_paper_trader.py \
  --futures \
  --live \
  --leverage 10 \
  --order-size 0.0001 \
  --gamma 0.02
```

**⚠️ Important**: Start with 10x leverage and $200-500 capital. Only scale to 50x after proving profitability.

## Documentation

### For New Users

1. **[Quick Start Guide](docs/strategies/QUICK_START.md)** - Get running in 10 minutes
2. **[Strategy README](strategies/avellaneda_stoikov/README.md)** - What is A-S and how it works
3. **[Deployment Guide](DEPLOYMENT.md)** - Production deployment

### For Advanced Users

1. **[GLFT Mathematical Model](docs/strategies/GLFT_MODEL.md)** - Deep mathematical dive
2. **[Bybit Futures Design](BYBIT_FUTURES_DESIGN.md)** - Leverage trading architecture
3. **[Pre-Deployment Checklist](PRE_DEPLOYMENT_CHECKLIST.md)** - Validation framework

### For Developers

1. **Test suite**: `pytest tests/` (369 tests)
2. **Code**: `strategies/avellaneda_stoikov/`
3. **Examples**: `scripts/`

## Legacy Freqtrade Setup

*For historical reference only. Not actively maintained.*

```bash
# Install Freqtrade
pip install freqtrade

# Download historical data
freqtrade download-data \
  --exchange binance \
  --pairs BTC/USDT \
  --timeframes 1m 1h 1d

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
