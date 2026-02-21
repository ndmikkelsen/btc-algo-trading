# Time-Decay Stop Loss for MRBB Strategy

## Goal
Implement always-on ATR-based stop losses with time-decay tightening for the Mean Reversion Bollinger Band strategy. Currently the optimized preset runs with no stop loss (stop_atr_multiplier=0), exposing the strategy to unlimited downside risk from flash crashes.

## Success Criteria
- Every trade has a stop loss at entry (3.0x ATR beyond band)
- Stops tighten over time: 3.0x -> 2.0x -> 1.0x ATR at 33%/66% of max holding bars
- Worst-case single trade loss reduced vs current baseline
- Sharpe ratio maintained or improved vs no-stop baseline
- All existing tests pass, new tests cover time-decay logic
- Live trader bugs fixed (_check_stop_target guard, tighten_stop dead code)

## Beads Alignment

| Phase | Bead ID | Title |
|-------|---------|-------|
| 1 | btc-algo-trading-97n | Implement time-decay stop loss config and model |
| 2 | btc-algo-trading-lob | Update simulator for always-on time-decay stops |
| 2 | btc-algo-trading-g0l | Fix live trader stop/target bugs and add time-decay support |
| 3 | btc-algo-trading-q9d | Update presets and param registry for time-decay stops |
| 4 | btc-algo-trading-7j1 | Write time-decay stop loss tests |
| 5 | btc-algo-trading-1qh | Backtest sweep: validate time-decay stop configurations |

## Dependency Graph

```
97n (config + model)
 ├─> lob (simulator)  ──┐
 ├─> g0l (live trader) ──┼─> 7j1 (tests) ─> 1qh (backtest sweep)
 └─> q9d (presets)     ──┘
```
