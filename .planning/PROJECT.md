# MRBB Profitability — Validate Edge, Optimize Stops, Deploy

## Goal

Determine if the MRBB strategy has a statistically significant, fee-adjusted trading edge. Optimize stop distance based on backtest evidence, validate out-of-sample, and deploy if the edge is confirmed.

## Context

The strategy architecture is complete (model, simulator, 11 presets, time-decay stops, 370 tests). However, backtesting over 329k candles (Jan 2023 – Feb 2026, 5m BTC/USDT) reveals:

- Current optimized preset: +0.34% return, 0.07 Sharpe — barely above breakeven
- Wide 5x ATR stop: +3.32% return, 0.46 Sharpe — 10x better
- 56% of trades exit via stop loss, not target
- 709 trades total, avg duration ~11 bars (~55 min), avg PnL -$1.77
- Fee impact unquantified (0.01% maker / 0.06% taker could erase gross returns)

**Key insight**: wider stops dramatically improve performance. The current 3.0x ATR initial stop appears too tight for BTC's volatility in a mean reversion context.

## Success Criteria

- [ ] Optimal ATR multiplier identified (sweep 3.5x–6.0x)
- [ ] Fee model verified and net-of-fees returns calculated
- [ ] Regime analysis shows edge isn't dependent on single period
- [ ] Statistical significance: p < 0.05 for Sharpe > 0
- [ ] Walk-forward / CPCV confirms OOS Sharpe > 50% of IS Sharpe
- [ ] Preset updated with validated parameters
- [ ] 30-day paper trade with no execution bugs
- [ ] Clear go/no-go decision documented with evidence

## Beads Alignment

| Phase | Bead ID | Title |
|-------|---------|-------|
| Epic | btc-algo-trading-1em | Epic: MRBB Profitability — Validate Edge, Optimize Stops, Deploy |
| 1 | btc-algo-trading-2v5 | Wide stop sweep: test 3.5x–6.0x ATR with decay variants |
| 1 | btc-algo-trading-8sc | Fee impact analysis: verify simulator fees and net-of-fees returns |
| 1 | btc-algo-trading-k71 | Regime-dependent performance: break down returns by market condition |
| 2 | btc-algo-trading-sed | Statistical significance: bootstrap/Monte Carlo test of strategy edge |
| 2 | btc-algo-trading-7iy | Walk-forward / CPCV validation of optimized parameters |
| 3 | btc-algo-trading-h9x | Update optimized preset with validated parameters |
| 4 | btc-algo-trading-l7z | Paper trade validated MRBB config for 30 days |
| 5 | btc-algo-trading-cf3 | Go/no-go decision and small capital deployment |

## Dependency Graph

```
Phase 1 (parallel):
  2v5 (wide stop sweep)  ──┐
  8sc (fee analysis)      ──┼──> h9x (update preset) ──> l7z (paper trade) ──> cf3 (go/no-go)
  k71 (regime analysis)   ──┤
                            │
Phase 2 (after sweep):      │
  sed (significance)  ──────┤
  7iy (WFO/CPCV)     ──────┘
```

## Previous Milestone (Completed)

Time-Decay Stop Loss (5 phases, all closed):
- Config + model core, simulator, live trader, presets, tests, backtest sweep
- 370 tests passing, phase calibration fix applied
- Commits: 986f2c7, 27374a0, c2a7f3a
