# Roadmap: Time-Decay Stop Loss

## Phase 1: Config + Model Core (btc-algo-trading-97n)
- Add 4 new config constants (STOP_DECAY_PHASE_1/2, STOP_DECAY_MULT_1/2)
- Change STOP_ATR_MULTIPLIER default: 2.5 -> 3.0
- Add 4 new model constructor params + entry_band_level state
- Add compute_time_decay_stop() method
- Remove stop_atr_multiplier==0 bypass in generate_orders()
- Update manage_risk() with time-decay tighten_stop logic
- Update get_strategy_info()

## Phase 2: Simulator + Live Trader (btc-algo-trading-lob, btc-algo-trading-g0l)
**Parallelizable** - both depend on Phase 1, independent of each other.

### 2a: Simulator (lob)
- Step path: track band_ref, remove stop==0 guards, add time-decay per bar
- Fast path: add band_ref, remove stop==0 guards, inline time-decay, set band_ref at entry

### 2b: Live Trader (g0l)
- Fix _check_stop_target() missing stop_price>0 guard
- Add band_ref to Position dataclass
- Store band_ref at entry
- Pass atr/band_ref/stop_price to manage_risk()

## Phase 3: Presets + Registry (btc-algo-trading-q9d)
- Update 5 optimized presets with stop_atr_multiplier=3.0 + decay params
- Add 4 new ParamSpecs to registry
- Update stop_atr_multiplier range (min 0.0->1.0, default 2.5->3.0)

## Phase 4: Tests (btc-algo-trading-7j1)
- Remove TestNoStopMode (4 tests)
- New test_time_decay_stops.py (~9 tests)
- Update param counts in test_param_registry.py

## Phase 5: Backtest Validation (btc-algo-trading-1qh)
- Sweep script comparing 5 stop configurations
- Measure Sharpe, max DD, worst trade, return, win rate
- Save results to backtests/mrbb/stop_decay_sweep/
