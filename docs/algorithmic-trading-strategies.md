# Bitcoin Algorithmic Trading Strategies

> Proven, backtested strategies for automated Bitcoin trading with implementation guidance.

## Overview

This document covers algorithmic trading strategies with documented performance results from academic
research and real-world backtesting. Each strategy includes expected performance metrics, optimal
market conditions, and implementation approaches.

---

## Strategy Categories

| Category | Best Market Condition | Typical Win Rate | Complexity |
|----------|----------------------|------------------|------------|
| Momentum/Trend-Following | Trending markets | 30-45% | Low-Medium |
| Mean Reversion | Sideways/Ranging | 60-70% | Medium |
| Grid Trading | Sideways/Ranging | N/A (frequency) | Low |
| On-Chain Analysis | All (long-term) | N/A (positioning) | Medium |
| Execution Algorithms | All | N/A (cost reduction) | High |
| DCA Variants | All (accumulation) | N/A | Low |

---

## 1. Momentum / Trend-Following Strategies

### Simple Momentum (25-Day Lookback)

**Rules:**

- Go long at close if price > price 25 days ago
- Exit if price < price 25 days ago

**Performance:**

- Outperforms buy-and-hold despite simplicity
- Low win rate (~42%) but high reward/risk ratio
- Average winner: 21% vs average loser: 4%
- Annual return: ~87% vs HODL ~66% (one backtest period)
- Only invested ~56% of the time

**Implementation:**

```python
# Pseudocode
def momentum_signal(prices, lookback=25):
    if prices[-1] > prices[-lookback]:
        return "LONG"
    else:
        return "EXIT"
```

### Golden/Death Cross (50/200 MA)

**Rules:**

- Buy when 50-day MA crosses above 200-day MA (Golden Cross)
- Sell when 50-day MA crosses below 200-day MA (Death Cross)

**Performance:**

- ~8 trades over 5-year period (2018-2023)
- Catches major bull trends
- Generates false signals in choppy/sideways markets
- Best as a filter, not standalone strategy

**Best Used For:** Position sizing overlay, trend confirmation

### Momentum with Volatility Filter

**Enhancement:** Only take momentum signals when volatility is within acceptable range.

**Performance:**

- Sharpe Ratio: ~1.2 (vs ~1.0 for unfiltered momentum)
- Improved stability in returns
- Strong performance pre-2021

---

## 2. Mean Reversion Strategies

### Bollinger Band Mean Reversion

**Rules:**

- Buy when price touches/crosses lower Bollinger Band
- Sell when price returns to middle band or touches upper band
- Use limit orders (avoids spread costs)

**Performance:**

- Daily returns up to 61% (before transaction costs) in backtests
- Win rate: 60-70%
- Works because Bitcoin price series shows mean-reverting properties (ARIMA)

**Critical Notes:**

- Stop-losses typically HURT mean reversion strategies
- Only use very wide stops if any
- High frequency, lower profit per trade

### BTC-Neutral Residual Mean Reversion

**Concept:** Trade the residual (deviation from expected value) rather than raw price.

**Performance:**

- Sharpe Ratio: ~2.3
- Particularly strong post-2021 as market matured
- Excels in range-bound conditions

### RSI Mean Reversion

**Rules:**

- Buy when RSI < 30 (oversold)
- Sell when RSI > 70 (overbought)
- Combine with Bollinger Bands to reduce false signals

---

## 3. Grid Trading

### How It Works

Places buy and sell orders at fixed price intervals within a defined range. Profits from price oscillations without predicting direction.

**Parameters:**

- Upper bound (resistance level)
- Lower bound (support level)
- Number of grids (affects order size and frequency)
- Grid spacing (uniform or geometric)

**Performance:**

- Target APR: >40% in proper conditions
- Minimum expectation: 3% monthly in sideways markets
- Academic research (Stevens Institute) found it competitive with ML-based strategies

**Best Conditions:**

- Range-bound/sideways markets
- Clear support and resistance levels
- Avoid trending markets (bull runs = just hold; bear markets = accumulate falling assets)

**Risk Management:**

- Set stop-loss below grid's lower bound
- Requires ~15-30 min weekly parameter review
- Not "set and forget"

**Implementation Options:**

- [Open-source Grid Trading Bot](https://github.com/jordantete/grid_trading_bot) - Python, CCXT-based
- Exchange-native bots (Bybit, Binance) - lower latency

---

## 4. On-Chain Analysis Strategies

### MVRV Z-Score Strategy

**Metric:** Market Value to Realized Value, normalized as Z-Score

**Trading Rules:**

- **Accumulate** when Z-Score < 0 (below realized value = undervalued)
- **Hold** when Z-Score 0-3 (normal range)
- **Take Profit** when Z-Score > 3.7 (historically marks cycle tops)

**Performance:**

- Identified market tops within 2 weeks historically
- Works on longer timeframes (weeks to months)
- Not suitable for short-term trading

**Data Sources:**

- [CheckOnChain](https://charts.checkonchain.com/)
- [Bitcoin Magazine Pro](https://www.bitcoinmagazinepro.com/charts/mvrv-zscore/)
- [CryptoQuant](https://cryptoquant.com/asset/btc/chart/market-indicator/mvrv-ratio)
- [Glassnode](https://glassnode.com)

### SOPR (Spent Output Profit Ratio)

**Variants:**

- Market SOPR - all transactions
- STH-SOPR - Short-term holders (<155 days)
- LTH-SOPR - Long-term holders (>155 days)

**Trading Rules:**

- SOPR < 1: Sellers are at a loss (potential bottom)
- SOPR > 1: Sellers are in profit (watch for distribution)
- Reset to 1 after prolonged < 1: Capitulation complete

### Realized Price Bands

**Concept:** Use realized price (average acquisition cost of all BTC) as dynamic support/resistance.

**Application:**

- Price below realized price = accumulation zone
- Price far above = extended, watch for correction

---

## 5. Execution Algorithms

For larger position sizes, execution algorithms minimize market impact and improve average entry/exit prices.

### TWAP (Time-Weighted Average Price)

**How It Works:** Breaks large orders into equal-sized chunks executed at regular intervals.

**Real-World Example:**

- MicroStrategy's $250M BTC purchase (2020) used TWAP via Coinbase
- Spread over several days to minimize slippage
- A crypto VC achieved 7.5% improvement over VWAP using TWAP (July 2024)

**Best For:**

- Large orders
- Uncertain volume conditions
- Compliance-friendly (predictable execution)

### VWAP (Volume-Weighted Average Price)

**How It Works:** Executes more during high-volume periods to match market's natural rhythm.

**Best For:**

- When you want execution price close to market average
- Liquid markets with predictable volume patterns

### Implementation

- Build custom using CCXT + scheduling
- Use institutional platforms (Wyden, Talos)
- Exchange APIs often support TWAP/VWAP natively

---

## 6. DCA (Dollar Cost Averaging) Variants

### Standard DCA

**Performance:**

- $10/week from 2019-2024: +202% return
- $100/month since 2014: +1,648% return ($35,700 -> $589,000)
- Outperforms lump sum ~18-34% of the time (but with lower drawdowns)

### Value Averaging

**Concept:** Adjust contribution size based on portfolio performance vs target growth rate.

**Rules:**

- If portfolio below target: invest more
- If portfolio above target: invest less (or sell)

### Dynamic DCA

**Enhancement:** Increase DCA amount during favorable on-chain conditions (low MVRV, high fear).

---

## 7. Hybrid / Blended Strategies

### 50/50 Momentum + Mean Reversion Portfolio

**Performance:**

- Sharpe Ratio: 1.71
- Annualized Return: 56%
- T-stat: 4.07
- Smoother returns across market regimes

**Rationale:** Momentum works in trends, mean reversion works in ranges. Combining captures both.

### Supertrend + RSI + Bollinger Bands

**Concept:** Use Supertrend for trend direction, RSI for entry timing, Bollinger Bands for targets.

**Reduces false signals** compared to single-indicator strategies.

---

## Implementation Stack

### Python Libraries

| Library | Purpose | Notes |
|---------|---------|-------|
| [CCXT](https://github.com/ccxt/ccxt) | Exchange connectivity | 108+ exchanges supported |
| [Freqtrade](https://www.freqtrade.io/en/stable/) | Full trading bot framework | ML optimization, Telegram control |
| [Backtrader](https://www.backtrader.com/) | Backtesting framework | Flexible, well-documented |
| [Backtesting.py](https://kernc.github.io/backtesting.py/) | Lightweight backtesting | Fast, simple API |
| [NautilusTrader](https://nautilustrader.io/) | Production-grade platform | Event-driven, high performance |

### Data Sources

| Source | Data Type | Cost |
|--------|-----------|------|
| Binance API | OHLCV, trades | Free |
| CoinGecko | Historical prices | Free tier available |
| Glassnode | On-chain metrics | Paid (some free) |
| CryptoQuant | On-chain metrics | Paid (some free) |
| Kaiko | Institutional-grade | Paid |

### Recommended Stack for Starting

```text
Freqtrade (bot framework)
    └── CCXT (exchange connection)
    └── PostgreSQL (data storage)
    └── FreqAI (ML optimization)
```

---

## Backtesting Best Practices

### Data Quality

- Use bid-ask data for short timeframes (not just trade data)
- Verify data across multiple sources (exchanges have "rolled back" trades)
- Account for survivorship bias

### Realistic Assumptions

- Include transaction fees (0.1% typical)
- Include slippage (0.05-0.5% depending on size)
- Use out-of-sample testing periods

### Risk Management

- Max 1% risk per trade
- Halt at 15% equity drawdown
- Max 3-4 indicators per strategy (avoid overfitting)

### Metrics to Track

- Sharpe Ratio (>1.0 good, >2.0 excellent)
- Maximum Drawdown
- Win Rate (context-dependent)
- Profit Factor (>1.5 target)
- Time in Market

---

## Historical Data Acquisition

To backtest against all BTC data, you need to understand what's available and from where.

### BTC Data Timeline

| Period | Data Quality | Notes |
|--------|--------------|-------|
| 2009-2010 | Sparse | Mining only, no real trading |
| 2010-2011 | Limited | Mt. Gox era, unreliable |
| 2012-2014 | Moderate | Bitstamp, early Coinbase |
| 2015-2017 | Good | Multiple exchanges, consistent |
| 2017-Present | Excellent | Binance, high liquidity, 1-min data |

**Realistic "all data" = 2012-present** for meaningful backtesting.

### Free Data Sources

| Source | Coverage | Granularity | Format |
|--------|----------|-------------|--------|
| [Binance Data](https://data.binance.vision/) | 2017+ | 1m, tick | CSV/ZIP |
| [CryptoDataDownload](https://www.cryptodatadownload.com/data/) | 2017+ | 1m, 1h, 1d | CSV |
| [Kraken OHLCVT](https://support.kraken.com/articles/360047124832) | 2013+ | 1m-1d | CSV/ZIP |
| [Bitstamp via CDD](https://www.cryptodatadownload.com/data/bitstamp/) | 2011+ | 1h, 1d | CSV |
| [Kaggle - Binance Full History](https://www.kaggle.com/datasets/jorijnsmit/binance-full-history) | 2017+ | 1m | Parquet |

### Freqtrade Data Download

```bash
# Install Freqtrade first
pip install freqtrade

# Download BTC/USDT from Binance (all available history)
freqtrade download-data \
  --exchange binance \
  --pairs BTC/USDT \
  --timeframes 1m 5m 1h 1d \
  --timerange 20170101-

# Download multiple pairs
freqtrade download-data \
  --exchange binance \
  --pairs BTC/USDT ETH/USDT \
  --timeframes 1h 1d \
  --days 2000

# Download all USDT pairs
freqtrade download-data \
  --exchange binance \
  --pairs ".*/USDT" \
  --timeframes 1d
```

Data stored in: `user_data/data/<exchange>/`

### Combining Multiple Sources (Full History)

For comprehensive 2012+ coverage:

```text
2012-2017: Bitstamp daily/hourly (oldest reliable exchange data)
2017-2024: Binance 1-minute (highest liquidity, best data)
```

**Approach:**
1. Download Bitstamp CSV from CryptoDataDownload (2012-2017)
2. Download Binance data via Freqtrade (2017+)
3. Merge/concatenate with pandas, handle overlapping period
4. Validate: check for gaps, anomalies, timezone consistency

### Data Quality Checklist

- [ ] No gaps in timestamps (especially around exchange outages)
- [ ] Volume data present and non-zero
- [ ] OHLC relationships valid (High >= Open, Close, Low)
- [ ] Timezone normalized to UTC
- [ ] Duplicates removed
- [ ] Outliers flagged (flash crashes, fat-finger trades)

### Storage Estimates

| Timeframe | ~Size per Year | 10 Years |
|-----------|----------------|----------|
| 1-minute | 50-100 MB | 500 MB - 1 GB |
| 1-hour | 2-5 MB | 20-50 MB |
| 1-day | 50-100 KB | 500 KB - 1 MB |

1-minute data for comprehensive backtesting: **~1-2 GB total**

### Market Regimes to Test

Your backtest should cover these distinct periods:

| Period | Regime | Why It Matters |
|--------|--------|----------------|
| 2013-2014 | Early bull/bear | Low liquidity, high volatility |
| 2017 | Parabolic bull | Tests momentum strategies |
| 2018 | Extended bear (-84%) | Tests drawdown handling |
| 2019-2020 | Accumulation | Tests range strategies |
| 2020-2021 | Institutional bull | Tests trend-following |
| 2022 | Bear market (-77%) | Tests risk management |
| 2023-2024 | Recovery/ETF era | Current market structure |

A strategy that works across **all regimes** is more robust than one optimized for a single period.

---

## Risk Warnings

1. **Backtests are not guarantees** - Past performance doesn't predict future results
2. **Market regime changes** - Strategies that worked pre-2021 may not work post-2021
3. **Overfitting risk** - More parameters = more likely to fail live
4. **Liquidity risk** - Large orders move markets
5. **Exchange risk** - Counterparty risk, API failures, flash crashes

---

## Next Steps

### Phase 1: Environment & Data
1. [ ] Set up Freqtrade development environment
2. [ ] Download Binance BTC/USDT data (2017-present, 1m/1h/1d)
3. [ ] Download Bitstamp data (2012-2017) for extended history
4. [ ] Validate and merge datasets
5. [ ] Verify coverage across all market regimes

### Phase 2: Strategy Implementation
6. [ ] Implement simple momentum strategy (25-day lookback)
7. [ ] Implement mean reversion strategy (Bollinger Bands)
8. [ ] Implement hybrid 50/50 portfolio

### Phase 3: Backtesting & Analysis
9. [ ] Backtest each strategy against full history
10. [ ] Analyze performance by market regime
11. [ ] Compare Sharpe ratios, max drawdown, win rates
12. [ ] Select best performer(s)

### Phase 4: Validation
13. [ ] Paper trade for 1-3 months
14. [ ] Compare paper results to backtest expectations
15. [ ] Refine parameters if needed
16. [ ] Go live with small position sizing

---

## Sources

### Strategy Research

- [QuantifiedStrategies - Bitcoin Trading Strategies](https://www.quantifiedstrategies.com/bitcoin-trading-strategies/)
- [QuantifiedStrategies - Algo Trading Strategies](https://www.quantifiedstrategies.com/algo-trading-strategies/)
- [QuantPedia - Trend-following and Mean-reversion in Bitcoin](https://quantpedia.com/trend-following-and-mean-reversion-in-bitcoin/)
- [Medium - Systematic Crypto Trading Strategies](https://medium.com/@briplotnik/systematic-crypto-trading-strategies-momentum-mean-reversion-volatility-filtering-8d7da06d60ed)

### Grid Trading

- [Stevens Institute - Grid Trading Research](https://fsc.stevens.edu/cryptocurrency-market-making-improving-grid-trading-strategies-in-bitcoin/)
- [Coinrule - Grid Bot Guide 2025](https://coinrule.com/blog/trading-tips/grid-bot-guide-2025-to-master-automated-crypto-trading/)

### On-Chain Analysis

- [Bitcoin Magazine Pro - MVRV Z-Score](https://www.bitcoinmagazinepro.com/charts/mvrv-zscore/)
- [CheckOnChain](https://charts.checkonchain.com/)
- [CryptoQuant - MVRV Ratio](https://cryptoquant.com/asset/btc/chart/market-indicator/mvrv-ratio)

### Execution Algorithms

- [TradingView - TWAP vs VWAP](https://www.tradingview.com/news/cointelegraph:4e659b29e094b:0-twap-vs-vwap-in-crypto-trading-what-s-the-difference/)
- [Chainlink - TWAP vs VWAP](https://chain.link/education-hub/twap-vs-vwap)

### DCA Analysis

- [dcaBTC Calculator](https://dcabtc.com/)
- [Newhedge - DCA Calculator](https://newhedge.io/bitcoin/dollar-cost-averaging-calculator)
- [Bull Bitcoin - DCA vs Lump Sum Analysis](https://www.bullbitcoin.com/blog/smash-buy-versus-dca)

### Implementation Resources

- [CCXT Documentation](https://github.com/ccxt/ccxt)
- [Freqtrade Documentation](https://www.freqtrade.io/en/stable/)
- [Backtrader Documentation](https://www.backtrader.com/)
- [CoinGecko - Backtesting Guide](https://www.coingecko.com/learn/backtesting-crypto-trading-strategies-python)
