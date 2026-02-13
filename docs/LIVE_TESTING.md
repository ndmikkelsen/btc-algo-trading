# Live Data Testing Infrastructure

Tools for validating the Avellaneda-Stoikov strategy against live/current market data.

## Overview

These scripts bridge the gap between backtesting and live trading by running the strategy observationally against real market data. No orders are placed — the tools measure what **would** have happened.

| Script | Purpose | Duration |
|--------|---------|----------|
| `run_shadow_trader.py` | Run A-S model against live prices | 48+ hours recommended |
| `analyze_shadow.py` | Analyze shadow trading results | Post-hoc |
| `monitor_data_quality.py` | Cross-exchange price consistency | Continuous |
| `estimate_fill_probability.py` | Empirical fill probability curve | One-time (uses 7d data) |

## Scripts

### 1. Shadow Trader (`scripts/run_shadow_trader.py`)

Connects to a live exchange via ccxt, runs the A-S model in real-time, and logs what it **would** have done.

```bash
# Default: OKX, 1m candles, optimized params, runs until Ctrl+C
python scripts/run_shadow_trader.py

# Custom configuration
python scripts/run_shadow_trader.py --exchange kucoin --timeframe 5m --config hft

# Run for 1 hour
python scripts/run_shadow_trader.py --duration 3600
```

**Options:**
- `--exchange`: okx (default), kucoin, bitfinex, kraken, bitstamp
- `--timeframe`: 1m (default), 5m, 15m, 1h
- `--duration`: seconds to run (0 = until Ctrl+C)
- `--config`: default, optimized (default), hft
- `--output`: output directory (default: `data/shadow_trading/`)

**What it monitors per tick:**
- Current mid price
- Model's bid/ask quotes
- Spread in basis points
- Regime detection (ADX, ranging/trending)
- Whether quotes would have been filled
- Theoretical inventory and P&L

**Output files:**
- `data/shadow_trading/shadow_{exchange}_{timestamp}.csv` — tick-by-tick data
- `data/shadow_trading/shadow_{exchange}_{timestamp}_summary.json` — session summary

### 2. Shadow Trade Analyzer (`scripts/analyze_shadow.py`)

Post-hoc analysis of shadow trading sessions.

```bash
# Analyze most recent shadow session
python scripts/analyze_shadow.py

# Analyze specific file
python scripts/analyze_shadow.py --file data/shadow_trading/shadow_okx_20260209_120000.csv

# Compare with backtester (requires matching OHLCV data)
python scripts/analyze_shadow.py --compare-backtest data/okx_btcusdt_1m.csv
```

**Analysis includes:**
- Fill rate breakdown (bid fills, ask fills, both, neither)
- Spread statistics (mean, median, percentiles)
- Effective spread captured on round-trips
- Regime detection distribution
- P&L progression
- Backtester comparison (when `--compare-backtest` provided)

### 3. Data Quality Monitor (`scripts/monitor_data_quality.py`)

Monitors price consistency across multiple exchanges in real-time.

```bash
# Default: OKX + KuCoin + Bitfinex, alert at 0.5% divergence
python scripts/monitor_data_quality.py

# Custom exchanges and threshold
python scripts/monitor_data_quality.py --exchanges okx kraken bitstamp --threshold 0.3

# Run for 1 hour, poll every 30 seconds
python scripts/monitor_data_quality.py --duration 3600 --interval 30
```

**Options:**
- `--exchanges`: 2+ exchanges to monitor (default: okx, kucoin, bitfinex)
- `--threshold`: alert threshold in % (default: 0.5)
- `--duration`: seconds to run (0 = until Ctrl+C)
- `--interval`: seconds between polls (default: 10)

**Output:** `data/data_quality/quality_{timestamp}.csv` and `_summary.json`

### 4. Fill Probability Estimator (`scripts/estimate_fill_probability.py`)

Builds an empirical fill probability curve from recent 1m data.

```bash
# Download 7 days of 1m data from OKX and estimate
python scripts/estimate_fill_probability.py

# Use already-downloaded data
python scripts/estimate_fill_probability.py --use-cached data/okx_btcusdt_1m.csv

# Include inventory risk analysis
python scripts/estimate_fill_probability.py --inventory-risk

# Different exchange
python scripts/estimate_fill_probability.py --exchange kucoin --days 14
```

**Output:**
- `data/fill_probability_curve.csv` — P(fill) vs distance from mid
- Console summary with calibration data
- Optional: `data/inventory_risk_after_fill.csv` — adverse moves after one-sided fills

## Interpreting Results

### Fill Probability Curve

The fill probability curve shows: *"if I place a limit order X basis points from the mid price, how often does it fill?"*

Key metrics:
- **Both-fill rate**: How often BOTH bid and ask fill (the market-making sweet spot)
- **Net spread**: Gross spread captured minus round-trip fees (20 bps at 0.1% per side)
- **Expected P&L per candle**: `both_fill_rate * net_spread` — the optimal distance maximizes this

**Calibration**: The `FILL_AGGRESSIVENESS` parameter in `config.py` should be tuned so the backtester's fill rate matches the empirical curve. If the backtester fills 60% of orders at 20bps but reality shows 40%, the backtester is optimistic.

### Shadow Trading

Look for:
- **Fill rate mismatch**: If the shadow trader's fill rate differs significantly from the backtester's predictions, the backtest assumptions are wrong
- **One-sided fills**: High bid-only or ask-only fill rates indicate the model is getting adversely selected
- **Regime accuracy**: Does ADX correctly identify ranging periods? Check if fills are more profitable during "ranging" vs "trending" labels
- **Spread captured**: Compare theoretical spread (what the model quotes) vs effective spread (what would actually be captured)

### Data Quality

Alerts indicate:
- **>0.5% cross-exchange spread**: Unusual, may indicate a flash crash, exchange issue, or stale data
- **Persistent divergence**: If one exchange consistently deviates, its data should not be used for backtesting
- **Correlation with fills**: Shadow fills during high-divergence periods may not be realistic

## Recommended Testing Protocol

### Phase 1: Fill Probability (1 hour)
```bash
python scripts/estimate_fill_probability.py --inventory-risk
```
Use results to calibrate backtester fill model.

### Phase 2: Data Quality Baseline (24 hours)
```bash
python scripts/monitor_data_quality.py --duration 86400
```
Establish baseline cross-exchange spread statistics.

### Phase 3: Shadow Trading (48+ hours)
```bash
python scripts/run_shadow_trader.py --duration 172800
```
At least 48 hours captures multiple market regimes (trending + ranging cycles).

### Phase 4: Analysis
```bash
python scripts/analyze_shadow.py --compare-backtest data/okx_btcusdt_1m.csv
```
Compare shadow results with backtester predictions for the same period.

### What to look for:
1. Does the backtester's fill rate match the shadow trader's?
2. Does the P&L trajectory look similar?
3. Are regime transitions detected at the same points?
4. How much latency exists between signal and fill opportunity?
5. Is the effective spread close to the theoretical spread?

If backtester and shadow trader diverge significantly, the backtest results are unreliable and the model/fill assumptions need adjustment before live trading.
