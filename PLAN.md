# PLAN.md - Avellaneda-Stoikov Market Making

> Working memory for implementing the Avellaneda-Stoikov market making model.

## Current Focus

**Implementing Avellaneda-Stoikov Market Making Strategy**

## Overview

The Avellaneda-Stoikov (2008) model is a mathematical framework for optimal market making that:
- Places both bid and ask orders simultaneously
- Dynamically adjusts spreads based on inventory risk
- Uses a reservation price that accounts for position exposure
- Optimizes for profit while managing inventory risk

## Key Formulas

### Reservation Price
```
r = S - q × γ × σ² × (T - t)
```
Where:
- S = Mid price
- q = Current inventory (positive = long, negative = short)
- γ = Risk aversion parameter
- σ² = Price volatility
- (T - t) = Time remaining in trading session

### Optimal Spread
```
δ = γ × σ² × (T - t) + (2/γ) × ln(1 + γ/κ)
```
Where:
- κ = Order book liquidity parameter

### Optimal Quotes
```
bid = r - δ/2
ask = r + δ/2
```

## Milestones

### M1: Core Model Implementation
- [ ] Implement volatility estimation (rolling window)
- [ ] Implement reservation price calculation
- [ ] Implement optimal spread calculation
- [ ] Unit tests for all calculations

### M2: Order Management
- [ ] Implement quote generation (bid/ask prices)
- [ ] Implement inventory tracking
- [ ] Implement position limits
- [ ] Implement order placement logic

### M3: Backtesting Framework
- [ ] Build market making backtester (different from directional)
- [ ] Simulate order fills based on price movement
- [ ] Track P&L including spread capture
- [ ] Generate performance metrics

### M4: Parameter Optimization
- [ ] Tune risk aversion (γ)
- [ ] Tune volatility window
- [ ] Tune order book liquidity (κ)
- [ ] Optimize for Sharpe ratio

## Parameters

| Parameter | Symbol | Description | Typical Range |
|-----------|--------|-------------|---------------|
| Risk Aversion | γ | How much to penalize inventory | 0.01 - 1.0 |
| Volatility Window | w | Candles for σ calculation | 20 - 100 |
| Time Horizon | T | Trading session length | 1 day |
| Liquidity | κ | Order book density | 1.0 - 10.0 |

## Notes

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-30 | Start with Freqtrade | Best Python framework, ML support, active community |
| 2026-01-30 | Target 2012+ data | Covers all major market regimes |
| 2026-01-30 | Test momentum + mean reversion + hybrid | Research shows hybrid outperforms single strategies |
| 2026-02-01 | Implement Cognee knowledge base | AI memory layer for semantic search over strategies, backtests, and session history |

## Recent Milestones

### Cognee Integration (2026-02-01) ✅

Implemented isolated Cognee stack for btc-algo-trading knowledge base:
- Unique ports (8001, 5434, 6381, 7475, 7688) - runs alongside second-brain
- Datasets: btc-knowledge-garden, btc-patterns, btc-constitution, btc-strategies, btc-backtests
- Semantic search over trading strategies and documentation
- Session capture for queryable history

## Open Questions

- Which exchange for live trading? (Binance, Kraken, Coinbase)
- Position sizing strategy?
- Risk management rules (max drawdown, stop-loss)?

## Resources

- [Original Paper](https://www.math.nyu.edu/~avellane/HighFrequencyTrading.pdf)
- [Hummingbot A-S Guide](https://hummingbot.org/blog/guide-to-the-avellaneda--stoikov-strategy/)
- [GitHub Implementation](https://github.com/fedecaccia/avellaneda-stoikov)
