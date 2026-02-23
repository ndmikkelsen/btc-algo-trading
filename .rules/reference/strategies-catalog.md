---
title: Strategy Catalog
category: reference
last_updated: 2026-02-22
description: Comprehensive catalog of algorithmic trading strategies with BTC applicability ratings
---

# Strategy Catalog

> Comprehensive reference of algorithmic trading strategies organized by category.
> Each entry includes theory, applicability to BTC, and implementation status.

## How to Use This Catalog

- **Researching**: Find strategies by category, then check BTC applicability rating
- **Prioritizing**: High-applicability strategies with "Not Started" status are candidates
- **Implementing**: Follow the [WORKFLOW.md](../../WORKFLOW.md) pipeline for any new strategy

### Status Legend

| Status | Meaning |
|--------|---------|
| **Production** | Live trading or validated for live |
| **Validated** | Backtested with go/no-go decision |
| **Scaffolded** | Code structure exists, not yet implemented |
| **Not Started** | Research only |

### BTC Applicability

| Rating | Meaning |
|--------|---------|
| **High** | Well-suited to BTC market structure and liquidity |
| **Medium** | Viable with adaptations or in specific regimes |
| **Low** | Poor fit due to BTC market characteristics |

---

## 1. Market Making

Profit from the bid-ask spread by providing liquidity on both sides of the book.

### 1.1 Avellaneda-Stoikov (A-S)

- **Theory**: Optimal quote placement minimizing inventory risk via reservation price adjustment. Spreads widen with inventory and volatility.
- **Who Uses It**: HFT firms, Hummingbot users, crypto market makers
- **BTC Applicability**: **High** — BTC/USDT has deep liquidity, tight spreads, 24/7 markets
- **Our Status**: **Production** — Full implementation with GLFT extension
- **Location**: `strategies/avellaneda_stoikov/`
- **References**: [Avellaneda & Stoikov 2008](https://www.math.nyu.edu/~avellane/HighFrequencyTrading.pdf)

### 1.2 Gueant-Lehalle-Fernandez-Tapia (GLFT)

- **Theory**: Extends A-S with order arrival intensity modeling (kappa parameter). Accounts for fill probability as a function of distance from mid.
- **Who Uses It**: Institutional market makers, quant funds
- **BTC Applicability**: **High** — Order book data readily available for kappa calibration
- **Our Status**: **Production** — Integrated into A-S implementation (`glft_model.py`)
- **Location**: `strategies/avellaneda_stoikov/glft_model.py`
- **References**: [Gueant, Lehalle & Fernandez-Tapia 2012](https://arxiv.org/abs/1105.3115)

### 1.3 Adaptive Spread Market Making

- **Theory**: Dynamically adjust spreads based on regime detection (trending vs ranging), volatility clustering, and order flow imbalance.
- **Who Uses It**: Sophisticated retail and institutional market makers
- **BTC Applicability**: **High** — BTC regime shifts are frequent and detectable
- **Our Status**: **Scaffolded** — Regime detection exists (`regime.py`), spread adaptation partial
- **Priority**: P2
- **References**: [Cartea, Jaimungal & Penalva 2015](https://www.springer.com/gp/book/9781107091146)

### 1.4 Multi-Level Market Making

- **Theory**: Place orders at multiple price levels with varying sizes. Deeper levels capture larger moves, inner levels capture frequent small moves.
- **Who Uses It**: Professional market makers, exchange-designated market makers
- **BTC Applicability**: **Medium** — Requires careful sizing to avoid adverse selection
- **Our Status**: Not Started
- **Priority**: P3

---

## 2. Statistical Arbitrage

Exploit statistical mispricings between related instruments.

### 2.1 Cross-Exchange Arbitrage

- **Theory**: Same asset priced differently across exchanges. Profit from price convergence after accounting for transfer costs and latency.
- **Who Uses It**: Crypto-native arb firms, retail arbitrageurs
- **BTC Applicability**: **High** — BTC trades on 100+ exchanges with frequent dislocations
- **Our Status**: **Scaffolded** — `strategies/stat_arb/`
- **Priority**: P2
- **References**: [Makarov & Schoar 2020](https://doi.org/10.1016/j.jfineco.2019.07.001)

### 2.2 Pairs Trading (Cointegration)

- **Theory**: Trade mean-reverting spreads between cointegrated pairs. Enter when spread deviates from equilibrium, exit on convergence.
- **Who Uses It**: Equity stat arb desks, crypto quant funds
- **BTC Applicability**: **Medium** — BTC/ETH and BTC/SOL show periodic cointegration
- **Our Status**: Not Started
- **Priority**: P3
- **References**: [Vidyamurthy 2004](https://www.wiley.com/Pairs+Trading-p-9780471460671)

### 2.3 Triangular Arbitrage

- **Theory**: Exploit pricing inconsistencies across three currency pairs (e.g., BTC/USDT, ETH/USDT, BTC/ETH).
- **Who Uses It**: HFT firms, exchange market makers
- **BTC Applicability**: **Medium** — Opportunities exist but are latency-sensitive
- **Our Status**: Not Started
- **Priority**: P4

### 2.4 Funding Rate Arbitrage

- **Theory**: Collect funding payments by holding opposite positions in spot and perpetual futures. When funding is positive, short perp + long spot.
- **Who Uses It**: Crypto-native funds, DeFi yield farmers
- **BTC Applicability**: **High** — BTC perp funding rates are volatile and frequently mispriced
- **Our Status**: Not Started
- **Priority**: P2
- **References**: [Bybit Funding Rate Docs](https://www.bybit.com/en/help-center/article/Funding-Rate)

---

## 3. Momentum & Trend Following

Capture directional moves by following established trends.

### 3.1 Time-Series Momentum

- **Theory**: Assets that have gone up recently tend to continue going up (and vice versa). Uses lookback returns to generate signals.
- **Who Uses It**: CTAs, trend-following funds (AQR, Man AHL, Winton)
- **BTC Applicability**: **High** — BTC exhibits strong momentum especially in bull markets
- **Our Status**: **Scaffolded** — `strategies/momentum_adaptive/`
- **Priority**: P3
- **References**: [Moskowitz, Ooi & Pedersen 2012](https://doi.org/10.1016/j.jfineco.2011.11.003)

### 3.2 Adaptive Momentum

- **Theory**: Dynamically adjust momentum lookback and position sizing based on volatility regime. Faster in low-vol, slower in high-vol.
- **Who Uses It**: Quant funds with regime-aware models
- **BTC Applicability**: **High** — BTC volatility regimes are distinct and measurable
- **Our Status**: **Scaffolded** — `strategies/momentum_adaptive/model.py`
- **Priority**: P3

### 3.3 Breakout / Channel

- **Theory**: Enter positions when price breaks above/below a defined range (Donchian channels, Bollinger Band breakouts). Classic turtle trading approach.
- **Who Uses It**: Trend followers, CTA funds
- **BTC Applicability**: **Medium** — Works in trending regimes, false breakouts common in ranging
- **Our Status**: Not Started
- **Priority**: P4

---

## 4. Mean Reversion

Profit from prices returning to a statistical mean or equilibrium.

### 4.1 Bollinger Band Mean Reversion (MRBB)

- **Theory**: Enter when price touches outer Bollinger Bands, exit at mean. Uses z-score of price relative to rolling mean.
- **Who Uses It**: Retail swing traders, systematic funds
- **BTC Applicability**: **Low** — Validated and shelved (NO-GO). Fee drag destroys edge.
- **Our Status**: **Validated — NO-GO** (Feb 2026). See `.rules/patterns/mrbb-validation-results.md`
- **Location**: `strategies/mean_reversion_bb/`
- **Key Finding**: +3.97% gross → -15.12% net after 0.06% taker fees

### 4.2 Ornstein-Uhlenbeck (OU) Process

- **Theory**: Model price as mean-reverting stochastic process. Estimate speed of reversion, long-term mean, and volatility to generate signals.
- **Who Uses It**: Quant desks, fixed income relative value
- **BTC Applicability**: **Low** — BTC is not well-modeled by OU in most regimes
- **Our Status**: Not Started
- **Priority**: P4

### 4.3 RSI Mean Reversion

- **Theory**: Enter on extreme RSI readings (oversold <30, overbought >70), exit on RSI normalization.
- **Who Uses It**: Retail traders, systematic funds as a filter
- **BTC Applicability**: **Medium** — Works as a filter/confirmation, poor standalone
- **Our Status**: Not Started
- **Priority**: P4

---

## 5. Volatility Strategies

Trade the volatility of an asset rather than its direction.

### 5.1 Variance Risk Premium

- **Theory**: Implied volatility consistently exceeds realized volatility. Harvest this premium by selling options/variance swaps.
- **Who Uses It**: Options market makers, vol arb desks
- **BTC Applicability**: **Medium** — Deribit BTC options market is liquid enough
- **Our Status**: Not Started
- **Priority**: P4
- **References**: [Carr & Wu 2009](https://doi.org/10.1093/rfs/hhn038)

### 5.2 Gamma Scalping

- **Theory**: Delta-hedge an options position and profit from realized volatility exceeding implied. Requires options access.
- **Who Uses It**: Options traders, vol desks
- **BTC Applicability**: **Medium** — Requires Deribit integration
- **Our Status**: Not Started
- **Priority**: P4

### 5.3 Volatility Regime Trading

- **Theory**: Classify market into vol regimes (low/medium/high) and adjust strategy parameters accordingly. Not a standalone strategy but a meta-layer.
- **Who Uses It**: Multi-strategy funds, adaptive systems
- **BTC Applicability**: **High** — BTC vol regimes are persistent and impact all strategies
- **Our Status**: Partial — Regime detection in `strategies/avellaneda_stoikov/regime.py`
- **Priority**: P2

---

## 6. Factor-Based Strategies

Combine multiple signals/factors for alpha generation.

### 6.1 Multi-Factor Models

- **Theory**: Combine momentum, value, carry, and quality factors. Portfolio weighting based on factor exposure.
- **Who Uses It**: Large quant funds (AQR, Two Sigma, Renaissance)
- **BTC Applicability**: **Medium** — Limited factor universe for single-asset trading
- **Our Status**: Not Started
- **Priority**: P4

### 6.2 On-Chain Factor Models

- **Theory**: Use blockchain-native data (MVRV, NVT, SOPR, exchange flows) as factors for timing BTC exposure.
- **Who Uses It**: Crypto-native funds, on-chain analysts
- **BTC Applicability**: **High** — Rich on-chain data unique to crypto
- **Our Status**: Not Started
- **Priority**: P3
- **References**: [Glassnode Academy](https://academy.glassnode.com/)

### 6.3 Sentiment-Based

- **Theory**: Use social media, news sentiment, and fear/greed indices as trading signals. NLP on crypto Twitter, Reddit, news.
- **Who Uses It**: Crypto funds, retail quant traders
- **BTC Applicability**: **High** — BTC is heavily sentiment-driven
- **Our Status**: Not Started
- **Priority**: P4

---

## 7. Machine Learning

Data-driven strategy generation and optimization.

### 7.1 Reinforcement Learning (Execution)

- **Theory**: Train RL agents to optimize order execution (timing, sizing, placement). Environment = order book, actions = order types.
- **Who Uses It**: HFT firms, execution desks
- **BTC Applicability**: **Medium** — Requires extensive training data and careful sim-to-real transfer
- **Our Status**: Not Started
- **Priority**: P4
- **References**: [Ning et al. 2021](https://arxiv.org/abs/2003.06468)

### 7.2 LSTM / Transformer Price Prediction

- **Theory**: Sequence models for short-term price direction prediction. Input features: OHLCV, order book, on-chain.
- **Who Uses It**: ML-focused quant funds
- **BTC Applicability**: **Medium** — Noisy signal, overfitting risk high
- **Our Status**: Not Started
- **Priority**: P4

### 7.3 Regime Classification (HMM / GMM)

- **Theory**: Use Hidden Markov Models or Gaussian Mixture Models to classify market regime (trending, ranging, volatile). Feed regime to other strategies.
- **Who Uses It**: Multi-strategy funds, adaptive systems
- **BTC Applicability**: **High** — BTC has distinct regimes; classification improves all strategies
- **Our Status**: Not Started (current regime detection is ADX-based, not ML)
- **Priority**: P3

---

## 8. Event-Driven

Trade around predictable or detectable market events.

### 8.1 Funding Rate Arbitrage

- **Theory**: Collect funding payments by holding opposite spot/perp positions. See also Section 2.4.
- **Who Uses It**: Crypto-native yield strategies
- **BTC Applicability**: **High** — Funding rates are volatile and frequently exploitable
- **Our Status**: Not Started
- **Priority**: P2

### 8.2 Liquidation Cascade Detection

- **Theory**: Detect large liquidation clusters (from leveraged positions) and trade the resulting price dislocations.
- **Who Uses It**: Crypto prop traders, on-chain analysts
- **BTC Applicability**: **High** — BTC leverage is extreme; cascades are frequent and tradeable
- **Our Status**: Not Started
- **Priority**: P3
- **References**: [Coinglass Liquidation Data](https://www.coinglass.com/LiquidationData)

### 8.3 Halving Cycle / Macro Event

- **Theory**: Trade the ~4-year BTC halving cycle and macro events (FOMC, CPI) that drive regime shifts.
- **Who Uses It**: Macro crypto funds, long-term allocators
- **BTC Applicability**: **High** — Halving cycle is the dominant BTC price driver
- **Our Status**: Not Started
- **Priority**: P4

---

## 9. High-Frequency / Microstructure

Exploit order book dynamics and information asymmetry at sub-second timescales.

### 9.1 Order Flow Imbalance

- **Theory**: Measure buy vs sell pressure in the order book. Persistent imbalance predicts short-term price direction.
- **Who Uses It**: HFT firms, proprietary trading desks
- **BTC Applicability**: **High** — BTC order books are transparent and imbalance is informative
- **Our Status**: **Scaffolded** — `strategies/scalper_microstructure/`
- **Priority**: P3

### 9.2 VPIN (Volume-Synchronized Probability of Informed Trading)

- **Theory**: Detect informed trading by measuring volume imbalance in time bars. High VPIN = toxic flow, widen spreads.
- **Who Uses It**: Market makers for adverse selection defense
- **BTC Applicability**: **High** — Useful as a filter for our market making strategies
- **Our Status**: Not Started
- **Priority**: P3
- **References**: [Easley, Lopez de Prado & O'Hara 2012](https://doi.org/10.1093/rfs/hhs053)

### 9.3 Lead-Lag (Cross-Exchange)

- **Theory**: One exchange's price movements lead another's by milliseconds. Trade the lagging exchange.
- **Who Uses It**: Crypto HFT firms
- **BTC Applicability**: **Medium** — Requires co-location or very low latency
- **Our Status**: Not Started
- **Priority**: P4

---

## 10. Execution Algorithms

Optimize large order execution to minimize market impact.

### 10.1 VWAP (Volume-Weighted Average Price)

- **Theory**: Execute orders proportionally to historical volume profile. Minimizes deviation from VWAP benchmark.
- **Who Uses It**: Institutional execution desks, brokers
- **BTC Applicability**: **High** — BTC has predictable intraday volume patterns
- **Our Status**: **Scaffolded** — `strategies/vwap_twap/`
- **Priority**: P3

### 10.2 TWAP (Time-Weighted Average Price)

- **Theory**: Execute equal-sized orders at equal time intervals. Simpler than VWAP, suitable when volume profile is flat.
- **Who Uses It**: Retail execution, simple rebalancing
- **BTC Applicability**: **High** — Simple, effective for position entry/exit
- **Our Status**: **Scaffolded** — `strategies/vwap_twap/`
- **Priority**: P3

### 10.3 Almgren-Chriss Optimal Execution

- **Theory**: Minimize execution cost = market impact + timing risk. Balances urgency against price impact using a risk-aversion parameter.
- **Who Uses It**: Institutional traders, large block execution
- **BTC Applicability**: **Medium** — Relevant for larger position sizes ($100K+)
- **Our Status**: Not Started
- **Priority**: P4
- **References**: [Almgren & Chriss 2000](https://doi.org/10.1016/S1386-4181(99)00011-0)

---

## Implementation Priority Summary

| Priority | Strategies | Rationale |
|----------|-----------|-----------|
| **P1 (Active)** | A-S/GLFT Market Making | In production, validating on Bybit |
| **P2 (Next)** | Funding Rate Arb, Cross-Exchange Arb, Adaptive Spreads, Vol Regime | High crypto-relevance, builds on existing infra |
| **P3 (Backlog)** | Momentum, On-Chain Factors, VPIN, VWAP/TWAP, Liquidation Detection | Valuable but requires new infrastructure |
| **P4 (Future)** | ML strategies, Options/Vol, OU Process, Almgren-Chriss | Complex, requires significant new capabilities |

---

**Last Updated**: 2026-02-22
