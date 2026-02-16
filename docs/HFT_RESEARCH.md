# HFT / Algorithmic Trading Strategy Research

> Research findings for BTC algorithmic trading strategies suitable for Bybit API execution.

## Executive Summary

Six algorithmic trading strategies were evaluated for implementation alongside the existing Avellaneda-Stoikov market making model. All strategies are designed to work within the latency constraints of Bybit's REST/WebSocket API (~50-200ms) on 1m-15m candle timeframes—not co-located microsecond-level HFT.

## Strategies Researched

### 1. Statistical Arbitrage / Pairs Trading

**Concept:** Exploits temporary mispricings between correlated crypto pairs (e.g., BTC/ETH, BTC/SOL). Uses cointegration theory to identify mean-reverting spreads and trades when the spread deviates significantly from its historical mean.

**Key Theory:**
- Engle-Granger cointegration test for pair selection
- Ornstein-Uhlenbeck process for spread dynamics
- Z-score entry/exit framework (entry at ±2σ, exit at mean)
- Half-life estimation for trade horizon calibration

**Feasibility for Bybit API:** HIGH
- Cross-pair arbitrage (not cross-exchange) eliminates latency concerns
- 5m candle timeframe provides sufficient signal
- Bybit supports all major pairs needed (BTC, ETH, SOL, etc.)
- Limitation: Bybit spot only, no native short selling → requires futures leg

**Complementarity with A-S:** HIGH
- Market-neutral (hedged), diversifies the directional risk of A-S
- Different signal source (spread dynamics vs market making)
- Both favor ranging markets but from different angles

**Risk-Reward:** Conservative
- Expected Sharpe: 1.0-2.0
- Win rate: 55-65%
- Max drawdown: 5-10%

---

### 2. Adaptive Momentum / Trend Following

**Concept:** Multi-timeframe momentum strategy combining MACD, RSI, and rate-of-change with volatility-scaled position sizing. Adapts parameters based on market regime (trending vs ranging).

**Key Theory:**
- Time-series momentum (Moskowitz et al., 2012)
- Volatility targeting (Barroso & Santa-Clara, 2015): size = σ_target / σ_realized
- Regime detection via ADX for parameter adaptation
- Multi-timeframe signal aggregation (5m, 15m, 1h)

**Feasibility for Bybit API:** HIGH
- Standard indicator-based signals work well on 5m-1h timeframes
- No latency sensitivity for trend following
- Bybit WebSocket provides real-time candle updates

**Complementarity with A-S:** VERY HIGH
- Directional strategy complements market-making
- A-S performs in ranging markets; momentum captures trends
- Together they cover most market regimes
- Can share regime detection code (ADX)

**Risk-Reward:** Moderate-Aggressive
- Expected Sharpe: 0.8-1.5
- Win rate: 40-50% (large winners compensate)
- Max drawdown: 10-20%

---

### 3. Mean Reversion with Bollinger Bands

**Concept:** Combines Bollinger Bands with VWAP confirmation and Keltner Channel squeeze detection. Enters counter-trend at band extremes, targets reversion to mean.

**Key Theory:**
- Bollinger Band touch as statistical extreme (2σ event)
- Keltner Channel squeeze: BB inside KC = volatility compression → breakout
- VWAP as institutional fair value anchor
- RSI for timing confirmation

**Feasibility for Bybit API:** HIGH
- All indicators are candle-based, no order book needed
- 5m timeframe provides clear signals
- Simple execution (single entry, defined target)

**Complementarity with A-S:** HIGH
- Both strategies profit from ranging markets
- Mean reversion BB provides directional trades; A-S provides market making
- Squeeze breakout signals can warn A-S to pause
- Shared volatility analysis

**Risk-Reward:** Conservative-Moderate
- Expected Sharpe: 1.0-1.8
- Win rate: 60-70%
- Max drawdown: 8-15%

---

### 4. Grid Trading

**Concept:** Places a grid of buy/sell limit orders at fixed intervals around the current price. Profits from natural price oscillation within the grid range.

**Key Theory:**
- Geometric grid: Level_i = Center × (1 + spacing)^i
- Profit per round trip = spacing - 2×fee
- ATR-based dynamic spacing adapts to volatility
- Regime detection gates grid activation (ranging only)

**Feasibility for Bybit API:** HIGH
- Limit order placement is natural for REST API
- Grid rebalancing on 1m intervals is sufficient
- Bybit supports sufficient open orders for grid operation

**Complementarity with A-S:** MODERATE
- Both are ranging-market strategies → some correlation
- Grid provides passive income; A-S provides active market making
- Grid is simpler, lower maintenance
- Risk: both lose in trends → diversification limited

**Risk-Reward:** Moderate
- Expected Sharpe: 0.5-1.2 (ranging), negative (trending)
- Win rate per grid trip: 90%+
- Max drawdown: 15-25% (grid break)

---

### 5. VWAP/TWAP Execution

**Concept:** Algorithmic execution strategies that minimize market impact for large orders. Dual purpose: (1) execution engine for other strategies' orders, (2) standalone alpha using VWAP deviation as signal.

**Key Theory:**
- VWAP schedule: q_t = Q × (v_t / V_total) — volume-weighted
- TWAP schedule: q_t = Q / N — time-weighted with randomization
- Market impact model (Almgren & Chriss, 2001): temp + permanent impact
- VWAP deviation as alpha signal (institutional accumulation/distribution)

**Feasibility for Bybit API:** HIGH
- Execution algorithms are designed for REST/limit order APIs
- Volume profile estimation works on 1m candles
- Most beneficial as infrastructure for other strategies

**Complementarity with A-S:** VERY HIGH
- Not competing — serves as execution layer for all strategies
- Reduces implementation shortfall when A-S or other strategies need large fills
- VWAP alpha signal adds diversified signal source

**Risk-Reward:** Very Conservative (execution), Conservative (alpha)
- Execution: saves 5-20 bps vs naive fills
- Alpha Sharpe: 0.5-1.0
- Max drawdown: 5-10%

---

### 6. Scalper / Microstructure

**Concept:** Analyzes order flow imbalance, cumulative volume delta, and VPIN (flow toxicity) to identify short-term directional moves. Captures 5-10 bps per trade with tight risk management.

**Key Theory:**
- Order Flow Imbalance: OFI = Σ(Buy - Sell) / Total
- VPIN (Easley et al., 2012): volume-bucketed toxicity indicator
- CVD divergence: price vs cumulative volume delta
- Circuit breakers for risk management (max losses, cooldown)

**Feasibility for Bybit API:** MODERATE
- Requires taker buy/sell volume split (available via Bybit API)
- 1m candles limit granularity vs tick-level HFT
- API latency (~50-200ms) prevents true microstructure alpha
- Still viable as "lower frequency microstructure" on 1m bars
- Full bid/ask spread analysis requires L2 order book data (WebSocket)

**Complementarity with A-S:** MODERATE
- Both analyze market microstructure but at different scales
- VPIN toxicity signal can benefit A-S (pause when toxic)
- OFI can provide directional bias for A-S quote skewing
- Shared infrastructure for volume analysis

**Risk-Reward:** Aggressive
- Expected Sharpe: 1.5-3.0 (when working)
- Win rate: 55-65%
- Max drawdown: 3-8%
- High trade frequency, tight stops

---

## Implementation Priority

| Priority | Strategy | Rationale |
|----------|----------|-----------|
| 1 | **Adaptive Momentum** | Highest complementarity with A-S (covers trends). Well-understood indicators. Straightforward implementation. |
| 2 | **Mean Reversion BB** | Natural extension of ranging-market focus. Simple signals, high win rate. Shares volatility analysis with A-S. |
| 3 | **VWAP/TWAP Execution** | Infrastructure value for all strategies. Reduces execution costs. VWAP alpha is a bonus. |
| 4 | **Statistical Arbitrage** | Market-neutral diversification. Requires more data infrastructure (multi-pair feeds). |
| 5 | **Grid Trading** | Simple passive income. Some overlap with A-S. Good for stable ranging periods. |
| 6 | **Scalper Microstructure** | Highest complexity, most constrained by API latency. Implement last when infrastructure is mature. |

## Feasibility Constraints (Bybit API)

| Constraint | Impact | Mitigation |
|-----------|--------|------------|
| API latency 50-200ms | Cannot do microsecond-level HFT | Focus on 1m-5m candle strategies |
| Rate limits | Max requests/second limits order frequency | Batch orders, use WebSocket for data |
| No co-location | Speed disadvantage vs prop firms | Avoid latency-sensitive strategies |
| Spot only (no native short) | Limits stat arb and momentum shorts | Use futures for short leg |
| Order book depth | L2 data available via WebSocket | Use for spread analysis in scalper |

## Portfolio Complementarity Matrix

```
                 A-S    StatArb  Momentum  MeanRev  Grid   VWAP   Scalper
A-S               -     Low      High      Med      Med    High   Med
StatArb          Low      -      Med       Med      Low    High   Low
Momentum         High   Med        -       High     High   Med    Med
MeanRev          Med    Med      High        -      Med    Med    Med
Grid             Med    Low      High      Med       -     Med    Low
VWAP             High   High     Med       Med      Med      -    Med
Scalper          Med    Low      Med       Med      Low    Med      -
```

(High = high complementarity/diversification, Low = high correlation/overlap)

## Recommended Next Steps

1. **Implement Adaptive Momentum** — highest priority, best diversification vs A-S
2. **Implement Mean Reversion BB** — second priority, overlapping market conditions with high win rate
3. **Build VWAP/TWAP as shared execution infrastructure** — benefits all strategies
4. **Backtest each strategy independently** on BTC/USDT 1m-5m data
5. **Portfolio optimization** — find optimal capital allocation across strategies using correlation analysis
6. **Paper trading** — run strategies in parallel on Bybit testnet before live capital
