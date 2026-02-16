# PLAN.md - Avellaneda-Stoikov Market Making

> Working memory for implementing the Avellaneda-Stoikov market making model.

## Recent Work

**Session**: 2026-02-12
**Branch**: algo-imp
**Last Commit**: 792e58a - chore: sync and format to-do.md from Beads

### Major Milestone: Bybit Futures HFT System
- **Pivoted from MEXC to Bybit** - Discovered MEXC Futures is institutional-only
- **Complete Bybit Futures integration** with 50x leverage support
- **Liquidation protection system** - Emergency position reduction at 20% threshold
- **Isolated margin mode** with configurable leverage (1-100x)
- **Comprehensive testing framework** - Automated validation suite
- **Full documentation suite** - DEPLOYMENT.md, README_FUTURES.md, PRE_DEPLOYMENT_CHECKLIST.md

### Architecture Changes
- Added bybit_futures_client.py (600+ lines) - Production Bybit API client with liquidation monitoring
- Updated live_trader.py - Futures mode support, position tracking (vs inventory)
- Updated config.py - Futures configuration (leverage, liquidation thresholds)
- Updated fee_model.py - Bybit VIP0/VIP1 fee tiers
- Enhanced run_paper_trader.py - --futures and --leverage CLI flags
- Dual exchange support - MEXC spot (0% maker fees) + Bybit futures (50x leverage)

### Next Major Steps
- Week 1: Run automated test suite on server (Task #6)
- Week 1: Complete pre-deployment checklist (Task #7)
- Week 2: Conservative live test with 10x leverage (Task #8)
- Week 3: Scale to 25x leverage if profitable (Task #9)
- Week 4+: Production deployment with 50x leverage (Task #10)

## Current Focus

**Validating A-S Strategy via Paper Trading on Bybit Futures**

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

### M1: Core Model Implementation ✅
- [x] Implement volatility estimation (rolling window)
- [x] Implement reservation price calculation
- [x] Implement optimal spread calculation
- [x] Unit tests for all calculations
- **Location**: `strategies/avellaneda_stoikov/model.py`

### M2: Order Management ✅
- [x] Implement quote generation (bid/ask prices)
- [x] Implement inventory tracking
- [x] Implement position limits
- [x] Implement order placement logic
- **Location**: `strategies/avellaneda_stoikov/order_manager.py`

### M3: Backtesting Framework ✅
- [x] Build market making backtester (different from directional)
- [x] Simulate order fills based on price movement
- [x] Track P&L including spread capture
- [x] Generate performance metrics
- **Location**: `strategies/avellaneda_stoikov/simulator.py`, `scripts/run_as_backtest.py`

### M4: Parameter Optimization ✅
- [x] Tune risk aversion (γ) → 0.1
- [x] Tune volatility window → 20 candles
- [x] Tune order book liquidity (κ) → 1.5
- [x] Optimize for Sharpe ratio
- **Result**: +43.52% annual return in ranging markets (ADX < 25)
- **Location**: `strategies/avellaneda_stoikov/config_optimized.py`

### M5: Paper Trading Validation 🔄
- [ ] Run paper trader on Bybit testnet for 1+ week
- [ ] Monitor fill rates and spread capture
- [ ] Validate inventory management in live conditions
- [ ] Compare live P&L vs backtest expectations
- [ ] Identify execution issues (latency, WebSocket stability)
- **Location**: `scripts/run_paper_trader.py`, `strategies/avellaneda_stoikov/live_trader.py`

### M6: Live Trading Deployment
- [ ] Create Bybit mainnet API keys
- [ ] Configure secure credential management
- [ ] Set initial capital allocation ($500-1000)
- [ ] Implement kill switch / emergency stop
- [ ] Set up monitoring and alerting
- [ ] Document risk limits and stop-loss rules

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
| 2026-02-01 | Abandon BTCMomentumScalper | Poor backtest results: -12% bull market, +0.36% bear market |
| 2026-02-01 | Focus on Avellaneda-Stoikov | Mathematical market making model with better risk-adjusted returns |
| 2026-02-03 | Use Bybit for trading | Testnet available, good API, WebSocket support |
| 2026-02-03 | Trade only ranging markets | ADX < 25 filter critical - strategy fails in trending markets |

## Recent Milestones

### Avellaneda-Stoikov Implementation (2026-02-01 - 2026-02-03) ✅

Complete market making infrastructure:
- **Core model** (246 lines): Reservation price, optimal spread, quote calculations
- **Order management** (408 lines): Order tracking, inventory, P&L management
- **Backtesting** (450 lines): Market simulator with regime detection
- **Live trading** (444 lines): Bybit WebSocket integration for real-time trading
- **Risk management** (256 lines): 4% risk/trade, 2:1 R:R, position limits
- **Regime detection** (233 lines): ADX-based filter for ranging markets
- **127 unit tests** covering all modules
- **3 config profiles**: base, HFT, optimized

### Cognee Integration (2026-02-01) ✅

Implemented isolated Cognee stack for btc-algo-trading knowledge base:
- Unique ports (8001, 5434, 6381, 7475, 7688) - runs alongside second-brain
- Datasets: btc-knowledge-garden, btc-patterns, btc-constitution, btc-strategies, btc-backtests
- Semantic search over trading strategies and documentation
- Session capture for queryable history

## Open Questions

- ~~Which exchange for live trading?~~ → **Bybit** (testnet available, good API)
- ~~Position sizing strategy?~~ → **4% risk per trade, 2:1 R:R**
- ~~Risk management rules?~~ → **Implemented in risk_manager.py**

### New Questions
- How long should paper trading validation run before going live?
- What's the minimum capital for meaningful live testing?
- Should we add more trading pairs beyond BTC/USDT?
- How to handle extended trending periods (strategy doesn't trade)?

## Resources

- [Original Paper](https://www.math.nyu.edu/~avellane/HighFrequencyTrading.pdf)
- [Hummingbot A-S Guide](https://hummingbot.org/blog/guide-to-the-avellaneda--stoikov-strategy/)
- [GitHub Implementation](https://github.com/fedecaccia/avellaneda-stoikov)
