---
title: Python Libraries Reference
category: reference
last_updated: 2026-02-22
description: Python libraries for algorithmic trading organized by function
---

# Python Libraries Reference

> Python libraries for algorithmic trading, organized by function.
> Each entry notes whether the library is already in our `requirements.txt`.

### Status Legend

| Status | Meaning |
|--------|---------|
| **Installed** | In `requirements.txt`, ready to use |
| **Not Installed** | Available via pip, not yet in project |

---

## 1. Backtesting Frameworks

### Freqtrade

- **Description**: Full-featured crypto trading bot framework with backtesting, optimization, and live trading. Strategy development in Python with built-in data handling.
- **Install**: `pip install freqtrade`
- **Use Case**: Our primary framework for directional strategies. Built-in Hyperopt for parameter optimization.
- **Status**: **Installed** (`freqtrade==2026.1`)
- **URL**: https://www.freqtrade.io/

### vectorbt

- **Description**: Vectorized backtesting library built on NumPy/Pandas. Extremely fast for parameter sweeps and portfolio simulation.
- **Install**: `pip install vectorbt`
- **Use Case**: Rapid strategy prototyping and parameter sweeps. 100x faster than event-driven backtesting for simple strategies.
- **Status**: Not Installed
- **URL**: https://vectorbt.dev/

### backtrader

- **Description**: Event-driven backtesting framework. Flexible architecture with broker simulation, commission modeling, and multi-data support.
- **Install**: `pip install backtrader`
- **Use Case**: Complex strategy backtesting when Freqtrade's framework is too restrictive. Good for multi-asset strategies.
- **Status**: Not Installed
- **URL**: https://www.backtrader.com/

### backtesting.py

- **Description**: Lightweight backtesting library. Simple API, good for quick prototyping. Less feature-rich than backtrader but easier to use.
- **Install**: `pip install backtesting`
- **Use Case**: Quick single-strategy prototyping and educational use.
- **Status**: Not Installed
- **URL**: https://kernc.github.io/backtesting.py/

---

## 2. Data Acquisition

### ccxt

- **Description**: Unified API for 100+ cryptocurrency exchanges. Handles REST and WebSocket connections, order management, and market data.
- **Install**: `pip install ccxt`
- **Use Case**: Our primary exchange connectivity layer. Used for market data, order placement, and account management on Bybit and MEXC.
- **Status**: **Installed** (`ccxt==4.5.35`)
- **URL**: https://docs.ccxt.com/

### yfinance

- **Description**: Yahoo Finance data downloader. Free historical OHLCV data for stocks, ETFs, crypto, and indices.
- **Install**: `pip install yfinance`
- **Use Case**: Quick data pulls for correlation analysis (BTC vs SPX, BTC vs Gold). Not for primary trading data.
- **Status**: Not Installed
- **URL**: https://github.com/ranaroussi/yfinance

### cryptofeed

- **Description**: Cryptocurrency exchange feed handler. Normalized WebSocket feeds from multiple exchanges with callback architecture.
- **Install**: `pip install cryptofeed`
- **Use Case**: Multi-exchange real-time data aggregation for cross-exchange arbitrage and lead-lag analysis.
- **Status**: Not Installed
- **URL**: https://github.com/bmoscon/cryptofeed

### python-binance / pybit

- **Description**: Exchange-specific Python clients with full API coverage and WebSocket support.
- **Install**: `pip install pybit` (Bybit)
- **Use Case**: Exchange-specific features not available through ccxt (e.g., advanced order types, account features).
- **Status**: Not Installed (we use ccxt for Bybit currently)

---

## 3. Technical Analysis

### TA-Lib

- **Description**: Technical analysis library with 150+ indicators. C-based core with Python wrapper. Industry standard.
- **Install**: `pip install ta-lib` (requires C library: `brew install ta-lib`)
- **Use Case**: All technical indicators (RSI, MACD, Bollinger Bands, ADX). Used in our regime detection module.
- **Status**: **Installed** (`ta-lib==0.6.8`)
- **URL**: https://ta-lib.github.io/ta-lib-python/

### pandas-ta (ft-pandas-ta)

- **Description**: Pure Python technical analysis library built on Pandas. No C dependencies. 130+ indicators.
- **Install**: `pip install pandas-ta`
- **Use Case**: Freqtrade's default TA library. Drop-in alternative when TA-Lib C dependency is problematic.
- **Status**: **Installed** (`ft-pandas-ta==0.3.16`)
- **URL**: https://github.com/twopirllc/pandas-ta

---

## 4. Machine Learning

### scikit-learn

- **Description**: General-purpose ML library. Classification, regression, clustering, dimensionality reduction, model selection.
- **Install**: `pip install scikit-learn`
- **Use Case**: Regime classification (Random Forest, SVM), feature selection, model validation (cross-validation, grid search).
- **Status**: Not Installed (add when ML strategies begin)
- **URL**: https://scikit-learn.org/

### PyTorch

- **Description**: Deep learning framework. Flexible, Pythonic API for neural networks. GPU acceleration.
- **Install**: `pip install torch`
- **Use Case**: LSTM/Transformer price prediction models, reinforcement learning agents.
- **Status**: Not Installed (add when deep learning strategies begin)
- **URL**: https://pytorch.org/

### stable-baselines3

- **Description**: Reliable RL algorithm implementations (PPO, SAC, A2C, DQN). Built on PyTorch.
- **Install**: `pip install stable-baselines3`
- **Use Case**: Training RL agents for execution optimization and adaptive market making.
- **Status**: Not Installed
- **URL**: https://stable-baselines3.readthedocs.io/

### XGBoost / LightGBM

- **Description**: Gradient boosting libraries. Fast, accurate, good for tabular data. Feature importance built in.
- **Install**: `pip install xgboost lightgbm`
- **Use Case**: Feature-based signal generation, regime classification with interpretable models.
- **Status**: Not Installed
- **URL**: https://xgboost.readthedocs.io/

---

## 5. Statistics & Econometrics

### statsmodels

- **Description**: Statistical models, hypothesis tests, and data exploration. OLS, ARIMA, VAR, cointegration tests.
- **Install**: `pip install statsmodels`
- **Use Case**: Cointegration testing (pairs trading), ARIMA modeling, Granger causality, Augmented Dickey-Fuller tests.
- **Status**: Not Installed (add when stat arb strategies begin)
- **URL**: https://www.statsmodels.org/

### arch

- **Description**: ARCH/GARCH volatility modeling. Univariate and multivariate volatility models.
- **Install**: `pip install arch`
- **Use Case**: Volatility forecasting for spread adjustment, regime detection based on vol clustering.
- **Status**: Not Installed
- **URL**: https://arch.readthedocs.io/

### scipy

- **Description**: Scientific computing library. Optimization, interpolation, integration, statistics.
- **Install**: `pip install scipy`
- **Use Case**: Statistical tests (KS test, t-test), optimization (minimize), distribution fitting.
- **Status**: Not Installed (add as needed — NumPy covers most current needs)
- **URL**: https://scipy.org/

---

## 6. Execution & Connectivity

### ccxt (see Section 2)

Already listed above. Primary execution layer.

### websockets

- **Description**: WebSocket client and server library. Clean async API for persistent connections.
- **Install**: `pip install websockets`
- **Use Case**: Real-time market data feeds and order updates from exchanges. Used in our live trader.
- **Status**: **Installed** (`websockets==16.0`)

### websocket-client

- **Description**: Synchronous WebSocket client. Simpler API than `websockets` for non-async code.
- **Install**: `pip install websocket-client`
- **Use Case**: Simpler WebSocket connections where async isn't needed.
- **Status**: **Installed** (`websocket-client==1.8.0`)

### aiohttp

- **Description**: Async HTTP client/server. High-performance for concurrent API calls.
- **Install**: `pip install aiohttp`
- **Use Case**: Concurrent exchange API calls, async data fetching.
- **Status**: **Installed** (`aiohttp==3.13.3`)

---

## 7. Risk & Performance Analysis

### pyfolio

- **Description**: Portfolio and risk analytics library by Quantopian. Tear sheets, drawdown analysis, factor exposure.
- **Install**: `pip install pyfolio-reloaded`
- **Use Case**: Strategy performance tear sheets, drawdown analysis, benchmark comparison.
- **Status**: Not Installed
- **URL**: https://github.com/stefan-jansen/pyfolio-reloaded

### empyrical

- **Description**: Common financial risk metrics. Sharpe ratio, max drawdown, Sortino ratio, alpha/beta.
- **Install**: `pip install empyrical-reloaded`
- **Use Case**: Standard performance metric calculations. Used by pyfolio internally.
- **Status**: Not Installed
- **URL**: https://github.com/stefan-jansen/empyrical-reloaded

### riskfolio-lib

- **Description**: Portfolio optimization and risk management. Mean-variance, CVaR, HRP, and Black-Litterman models.
- **Install**: `pip install riskfolio-lib`
- **Use Case**: Multi-strategy portfolio allocation and risk budgeting (when running multiple strategies).
- **Status**: Not Installed
- **URL**: https://riskfolio-lib.readthedocs.io/

---

## 8. Optimization

### Optuna

- **Description**: Hyperparameter optimization framework. Bayesian optimization with pruning. Database-backed for distributed runs.
- **Install**: `pip install optuna`
- **Use Case**: Strategy parameter optimization (gamma, kappa, lookback windows). Superior to grid search for high-dimensional spaces.
- **Status**: Not Installed
- **URL**: https://optuna.org/

### scipy.optimize (see Section 5)

Part of SciPy. Useful for single-objective optimization (minimize, curve_fit).

---

## 9. Visualization

### Plotly

- **Description**: Interactive plotting library. Candlestick charts, 3D plots, dashboards. Works in notebooks and standalone.
- **Install**: `pip install plotly`
- **Use Case**: Interactive backtest result visualization, parameter surface plots, P&L curves.
- **Status**: Not Installed
- **URL**: https://plotly.com/python/

### mplfinance

- **Description**: Matplotlib-based financial charting. Candlestick, OHLC, and Renko charts.
- **Install**: `pip install mplfinance`
- **Use Case**: Quick candlestick charts with indicator overlays for strategy development.
- **Status**: Not Installed
- **URL**: https://github.com/matplotlib/mplfinance

### Rich

- **Description**: Rich text and beautiful formatting in the terminal. Tables, progress bars, syntax highlighting.
- **Install**: `pip install rich`
- **Use Case**: Terminal-based TUI dashboards for live trading monitoring. Used in our TUI dashboard.
- **Status**: **Installed** (`rich==14.3.2`)

### Streamlit

- **Description**: Python web app framework for data science. Build interactive dashboards with minimal code.
- **Install**: `pip install streamlit`
- **Use Case**: Strategy analysis dashboards, backtest result viewers, live trading monitors.
- **Status**: Not Installed
- **URL**: https://streamlit.io/

---

## 10. Data Processing

### NumPy

- **Description**: Numerical computing library. N-dimensional arrays, linear algebra, random number generation.
- **Install**: `pip install numpy`
- **Use Case**: Core numerical operations throughout all strategies.
- **Status**: **Installed** (`numpy==2.4.2`)

### Pandas

- **Description**: Data manipulation library. DataFrames, time series, groupby, merge/join.
- **Install**: `pip install pandas`
- **Use Case**: All data handling — OHLCV data, trade logs, performance analysis.
- **Status**: **Installed** (`pandas==2.3.3`)

### PyArrow

- **Description**: Apache Arrow for Python. Columnar in-memory format. Fast Parquet/Feather I/O.
- **Install**: `pip install pyarrow`
- **Use Case**: Efficient storage and loading of large historical datasets. Parquet file I/O.
- **Status**: **Installed** (`pyarrow==23.0.0`)

---

## 11. Database & Storage

### SQLAlchemy

- **Description**: Python SQL toolkit and ORM. Database-agnostic interface for PostgreSQL, SQLite, MySQL.
- **Install**: `pip install sqlalchemy`
- **Use Case**: Trade logging, backtest results storage, strategy state persistence.
- **Status**: **Installed** (`sqlalchemy==2.0.46`)

### psycopg2

- **Description**: PostgreSQL adapter for Python. Required for SQLAlchemy PostgreSQL connections.
- **Install**: `pip install psycopg2-binary`
- **Use Case**: PostgreSQL connectivity for paper trading instance tracking.
- **Status**: **Installed** (`psycopg2-binary==2.9.10`)

---

## Installation Summary

### Currently Installed (13 packages)

```
ccxt, freqtrade, ta-lib, ft-pandas-ta, websockets, websocket-client,
aiohttp, rich, numpy, pandas, pyarrow, sqlalchemy, psycopg2-binary
```

### Recommended Next Installs (by priority)

| Priority | Packages | For |
|----------|----------|-----|
| P2 | `statsmodels`, `scipy` | Stat arb, cointegration testing |
| P2 | `optuna` | Parameter optimization |
| P3 | `scikit-learn` | Regime classification |
| P3 | `plotly`, `pyfolio-reloaded` | Visualization and analysis |
| P3 | `vectorbt` | Fast parameter sweeps |
| P4 | `torch`, `stable-baselines3` | ML/RL strategies |
| P4 | `cryptofeed` | Multi-exchange data |

---

**Last Updated**: 2026-02-22
