# Roadmap: MRBB Profitability — Validate Edge, Optimize Stops, Deploy

## Phase 1: Discovery (parallel — no dependencies)

### 1a: Wide Stop Sweep (btc-algo-trading-2v5)
- Extend sweep_stop_decay.py to test 3.5x, 4.0x, 4.5x, 5.0x, 5.5x, 6.0x initial ATR multipliers
- For each: no decay, gentle decay (80% of initial), moderate decay (60%)
- Record Sharpe, return, MaxDD, worst trade, win rate, avg bars held, stop exit %
- Analyze the Sharpe/MaxDD efficient frontier
- Identify optimal initial ATR multiplier

### 1b: Fee Impact Analysis (btc-algo-trading-8sc)
- Audit simulator fee model (is slippage_pct the only fee proxy?)
- Calculate explicit fee drag per configuration
- Produce gross vs net comparison table
- If fees aren't properly modeled, add explicit maker/taker fees

### 1c: Regime Analysis (btc-algo-trading-k71)
- Segment 3-year backtest into quarterly windows
- Per-window: Sharpe, return, # trades, win rate
- Overlay with BTC realized vol and trend regime
- Identify which conditions the strategy profits in
- Check for "lucky period" clustering

## Phase 2: Validation (depends on Phase 1a sweep results)

### 2a: Statistical Significance (btc-algo-trading-sed)
- Bootstrap test on trade log: H0 Sharpe = 0
- Monte Carlo permutation test on PnL series
- Test both current 3.0x config AND best config from wide stop sweep
- Calculate p-values and confidence intervals

### 2b: Walk-Forward / CPCV (btc-algo-trading-7iy)
- CPCV on best config from sweep
- Walk-forward: train 6-month rolling, test next 3 months
- Compare IS vs OOS Sharpe degradation
- Overfitting check: OOS Sharpe must be > 50% of IS

## Phase 3: Integration (depends on Phases 1 + 2)

### Update Preset (btc-algo-trading-h9x)
- Update optimized.yaml with evidence-backed parameters
- Update 1m and 3m presets with calibrated phases
- Run full test suite (370+ tests)
- Document parameter selection rationale

## Phase 4: Paper Trading (depends on Phase 3)

### 30-Day Paper Trade (btc-algo-trading-l7z)
- Deploy DirectionalTrader with validated preset on Bybit dry-run
- Monitor: signal generation, stop management, time-decay behavior
- Compare paper results with backtest expectations
- Log execution issues

## Phase 5: Deployment Decision (depends on Phase 4)

### Go/No-Go (btc-algo-trading-cf3)
- Compile all evidence: backtest, significance, WFO, paper trade
- Calculate net-of-fees expected annual return and max drawdown
- If GO: deploy $500-1000 on Bybit futures
- If NO-GO: document findings and archive
