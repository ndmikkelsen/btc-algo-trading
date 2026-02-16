---
id: to-do-list
aliases:
  - to-do
tags:
  - to-do
  - kanban
kanban-plugin: board
---

## Low Priority - #p2

- [ ] Tune quote update threshold for low-volatility markets #p2
  > Branch: fix/position-reduce
  >
  > During live trading, the bot only updated quotes once in 5+ minutes because the should_update threshold (0.1% change) is too tight for the 5-second polling interval.
  >
  > In _update_quotes() (live_trader.py:740-743):
  >   elif abs(bid - self.state.bid_price) / self.state.bid_price > 0.001:
  >
  > In a calm market, BTC needs to move ~$70 between polls to trigger a requote. Orders sit at stale prices for extended periods.
  >
  > Options:
  > 1. Lower threshold (e.g., 0.0005 = 5bps)
  > 2. Add a time-based requote (e.g., always update every 60s)
  > 3. Hybrid: time OR price threshold
  >
  > Impact: Bot misses fills when market moves gradually.
- [ ] Complete stat_arb model implementation #p2
  > Branch: algo-imp
  >
  > Multiple TODO stubs found in strategies/stat_arb/model.py:
  > - Rolling correlation calculation
  > - OLS regression for hedge ratio
  > - Augmented Dickey-Fuller test for cointegration
  > - Spread calculation and z-score computation
  > - Half-life estimation
  >
  > This is a skeleton implementation that needs to be completed before the stat arb strategy can be used.
- [ ] Tune A-S parameters from paper trading results #p2
  > Adjust Avellaneda-Stoikov parameters based on paper trading observations.
  >
  > ## Parameters to Evaluate
  > - Risk aversion (γ) - currently 0.1
  > - Volatility window - currently 20 candles
  > - MIN_SPREAD - currently 0.4% (optimized config)
  > - ADX threshold - currently 25 for regime filter
  >
  > ## Goals
  > - Improve fill rate while maintaining profitability
  > - Reduce inventory risk exposure
  > - Optimize for Sharpe ratio in live conditions

## Medium Priority - #p1

- [ ] Prepare for live trading deployment #p1
  > Set up infrastructure for real money trading on Bybit mainnet.
  >
  > ## Checklist
  > - [ ] Create Bybit mainnet API keys (read + trade permissions)
  > - [ ] Configure mainnet credentials securely (env vars, not in code)
  > - [ ] Set initial capital allocation (start small: $500-1000)
  > - [ ] Implement kill switch / emergency stop
  > - [ ] Set up monitoring and alerting
  > - [ ] Document risk limits and stop-loss rules
  >
  > ## Risk Management
  > - Max position size limits
  > - Daily loss limits
  > - Automatic shutdown on anomalies
- [ ] Run A-S paper trading on Bybit testnet #p1
  > Validate Avellaneda-Stoikov strategy in live market conditions using Bybit testnet paper trading.
  >
  > ## Acceptance Criteria
  > - Run paper trader for minimum 1 week
  > - Monitor fill rates, spread capture, and inventory management
  > - Track P&L vs backtest expectations
  > - Identify any issues with live execution (latency, WebSocket stability)
  >
  > ## Resources
  > - scripts/run_paper_trader.py
  > - strategies/avellaneda_stoikov/live_trader.py
  > - config_hft.py settings

## High Priority - #p0

## In Progress

## Done

- [x] 🚨 CRITICAL: Manual close of pre-existing Bybit position required #p0
  > CRITICAL: Manual close of pre-existing Bybit position required BEFORE live trading.
  >
  > Status: BLOCKING — prevents live trading deployment
  >
  > Position details:
  > - Size: 0.029 BTC SHORT
  > - Exchange: Bybit mainnet BTCUSDT Futures
  > - Must be manually closed via:
  >   - Bybit web UI, OR
  >   - CCXT API call (place 0.029 BTC BUY market order)
  >
  > Why this is critical:
  > - Pre-existing position from previous trading session
  > - If left open + market moves against it, triggers liquidation
  > - Emergency reduce system is now fixed, but this position must still be manually closed
  >
  > After closing:
  > 1. Verify position shows 0.000 BTC on Bybit
  > 2. Run btc-algo-trading-iib (resume live trading)
  > 3. Monitor for systemic fix validation
- [x] Investigate 90-min dry spell between fills #p1
- [x] Fix PnL tracking desync after inventory reductions #p1
- [x] Add colored trade reporting and per-trade PnL display #p1
- [x] Resume live trading with fixed emergency position reduction #p1
  > Resume live trading with fixed emergency position reduction system.
  >
  > FIXES COMPLETED:
  > ✅ commit b3b08c2 — Emergency reduce robustness (config constants, lot-size rounding, client validation)
  > ✅ commit f7af538 — Systemic fix (order_size correction, inventory limits, startup warning)
  >
  > BEFORE GOING LIVE:
  > 1. ⚠️ Manually close pre-existing 0.029 BTC SHORT position on Bybit (btc-algo-trading-q6s)
  > 2. Run /run-live --order-pct 4.0 --capital 500
  > 3. Monitor for 1+ hour to validate:
  >    - No 'Error reducing position' spam
  >    - Inventory limits trigger at correct points (3 and 5 fills)
  >    - Bot maintains balanced position (not one-sided)
  >    - Profitability checks work correctly
  >
  > Both systemic issues fixed:
  > - Liquidation protection now works (closes position instead of error loop)
  > - Bot won't go one-sided after 1 fill (inventory limits corrected)
  > - Order sizing transparent ( notional, not misleading )
  > - Client-side validation prevents future violations
- [x] Backtest BTCMomentumScalper strategy #p1
- [x] Download Binance BTC/USDT data (2017-present) #p1
- [x] Verify backtesting works with sample data #p1
- [x] Configure exchange API for paper trading #p1
- [x] Install Freqtrade #p1
- [x] Backtesting Pipeline Setup #p1
- [x] Configure Cognee knowledge base for btc-algo-trading #p1
  > Set up isolated Cognee stack with unique ports, update all scripts and documentation to use btc-specific datasets and configuration.
- [x] Suppress asymmetric spread log noise #p2
- [x] Document backtesting findings #p2
- [x] Analyze performance by market regime #p2
- [x] Merge datasets into unified format #p2
- [x] Validate data quality #p2
- [x] Download Bitstamp data (2012-2017) #p2
- [x] Optimize BTCMomentumScalper strategy parameters #p2
- [x] Update PLAN.md with completed A-S milestones #p2
  > PLAN.md still shows M1-M4 milestones as unchecked, but all are implemented.
  >
  > ## Updates Needed
  > - Mark M1 (Core Model) as complete
  > - Mark M2 (Order Management) as complete
  > - Mark M3 (Backtesting Framework) as complete
  > - Mark M4 (Parameter Optimization) as complete
  > - Add M5: Paper Trading Validation
  > - Add M6: Live Trading Deployment
  > - Update Open Questions section

%% kanban:settings

```json
{
  "kanban-plugin": "board",
  "list-collapse": [false, false, false, false, true],
  "show-checkboxes": true,
  "show-card-footer": true,
  "tag-sort-order": ["p0", "p1", "p2"],
  "date-format": "YYYY-MM-DD"
}
```

%%
