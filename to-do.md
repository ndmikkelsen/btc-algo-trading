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



## Medium Priority - #p1



## High Priority - #p0



## In Progress



## Done

- [x] Fix simulator short position cash accounting #p0
  > CRITICAL: simulator.py has inverted cash flow for shorts.
  > 
  > Line 210 (_enter_position): deducts cash for shorts (should credit — selling borrowed asset)
  > Line 270 (_exit_position): adds cash for shorts (should debit — buying back asset)
  > Line 291 (_mark_to_market): uses same formula for long/short (should invert for shorts)
  > 
  > Effect: Short P&L is inverted. Profitable shorts reduce equity, losing shorts increase it.
  > Proof: Recorded short PnL = -$186.18, but cash flow shows +$186.18.
  > Corrected total return: ~-25.5% (not +12.7%).
  > 
  > Fix: Branch on position side for cash operations. For shorts:
  > - Entry: cash += size * price (credit from short sale)
  > - Exit: cash -= size * exit_price (debit to buy back)
  > - MTM: cash + size * (2*entry_price - current_price)
  > 
  > Must fix before any further backtesting or parameter optimization.
  > 
  > Branch: feat/mean-reversion-bb
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
- [x] Update optimized preset with validated parameters #p1
  > After the sweep, significance test, and WFO validation, update the optimized preset YAML with the best validated configuration.
  > 
  > ## Work
  > - Take the best config from the wide stop sweep that passes statistical significance
  > - Verify it passes WFO/CPCV (not overfit)
  > - Update strategies/mean_reversion_bb/presets/optimized.yaml
  > - Update presets for 1m and 3m timeframes with calibrated phases
  > - Run full test suite to confirm no regressions
  > 
  > ## Depends On
  > - Wide stop sweep
  > - Statistical significance test
  > - WFO/CPCV validation
  > 
  > ## Success Criteria
  > - Preset updated with evidence-backed parameters
  > - All 370+ tests pass
  > - Clear documentation of why these params were chosen
- [x] Walk-forward / CPCV validation of optimized parameters #p1
  > Current backtest uses the full dataset for both fitting and evaluation (in-sample bias). Need proper out-of-sample validation.
  > 
  > ## Work
  > - Run combinatorial purged cross-validation (CPCV) on the best config from the wide stop sweep
  > - Run walk-forward optimization: train on rolling 6-month windows, test on next 3 months
  > - Compare in-sample vs out-of-sample Sharpe degradation
  > - Check for overfitting: if OOS Sharpe < 50% of IS Sharpe, the params are overfit
  > 
  > ## Depends On
  > - Wide stop sweep (need the best config first)
  > 
  > ## Success Criteria
  > - OOS Sharpe > 50% of IS Sharpe (not overfit)
  > - Walk-forward shows consistent performance across windows
  > - CPCV confirms parameter stability
- [x] Statistical significance: bootstrap/Monte Carlo test of strategy edge #p1
  > With 709 trades and 0.07 Sharpe, is the strategy edge distinguishable from random? We have monte_carlo.py and significance.py modules already.
  > 
  > ## Work
  > - Run bootstrap significance test on the trade log (H0: Sharpe = 0)
  > - Calculate p-value for observed Sharpe ratio
  > - Run Monte Carlo permutation test on trade PnL series
  > - Test with both the current 3.0x config AND the best config from the wide stop sweep
  > - If using the wide stop config (higher Sharpe), retest significance
  > 
  > ## Success Criteria
  > - p-value < 0.05 for Sharpe > 0 (statistically significant edge)
  > - OR clear evidence that there's no significant edge (honest no-go signal)
  > - Monte Carlo confidence intervals for expected Sharpe
- [x] Regime-dependent performance: break down returns by market condition #p1
  > The strategy uses ADX < 22 as a regime filter, but we don't know how returns distribute across time. BTC had distinct phases: 2023 consolidation, 2024 bull run, 2025 chop.
  > 
  > ## Work
  > - Segment the 3-year backtest into quarterly or monthly windows
  > - Calculate per-window: Sharpe, return, # trades, win rate
  > - Overlay with BTC regime (ranging vs trending, realized vol)
  > - Identify which market conditions the strategy profits in
  > - Check if the +3.32% (wide stop) clusters in specific periods or is distributed
  > 
  > ## Success Criteria
  > - Clear map of when the strategy works vs when it doesn't
  > - Identification of any "lucky periods" that inflate aggregate stats
  > - Confidence that the edge isn't regime-dependent on a single period
- [x] Fee impact analysis: verify simulator fees and net-of-fees returns #p1
  > The optimized preset shows +0.34% gross return over 3 years with 709 trades. At Bybit VIP0 rates (0.01% maker, 0.06% taker), total fee drag could erase all profit.
  > 
  > ## Work
  > - Verify the simulator fee model (is slippage_pct acting as fee proxy? or are fees separate?)
  > - Calculate explicit fee drag: 709 trades × 2 legs × avg trade size × fee rate
  > - Compare gross vs net returns for each sweep configuration
  > - If fees aren't modeled, add them to the simulator
  > 
  > ## Success Criteria
  > - Clear accounting of gross return vs fee drag vs net return
  > - Simulator correctly models Bybit VIP0 fees
  > - Decision: is the strategy profitable after fees?
- [x] Wide stop sweep: test 3.5x–6.0x ATR with decay variants #p1
  > The Phase 5 sweep showed 5.0x fixed stop returns +3.32% (0.46 Sharpe) vs 3.0x at +0.41% (0.08 Sharpe). This is the single biggest performance lever.
  > 
  > ## Work
  > - Extend sweep_stop_decay.py to test 3.5x, 4.0x, 4.5x, 5.0x, 5.5x, 6.0x initial multipliers
  > - For each, test: no decay, gentle decay (to 80% of initial), moderate decay (to 60%)
  > - Record: Sharpe, return, MaxDD, worst trade, win rate, avg bars held, stop exit %
  > - Analyze the Sharpe/MaxDD frontier — find the sweet spot
  > 
  > ## Success Criteria
  > - Clear identification of optimal initial ATR multiplier
  > - Sharpe improvement over current 3.0x baseline
  > - MaxDD acceptable (target < 8%)
- [x] Epic: MRBB Profitability — Validate Edge, Optimize Stops, Deploy #p1
  > ## Context
  > 
  > The MRBB strategy has solid architecture (model, simulator, presets, time-decay stops, 370 tests) but backtesting over 3+ years of 5m BTC data reveals concerning profitability:
  > 
  > - Optimized preset (gentle decay 3→2.5→2x): +0.34% return, 0.07 Sharpe, 44% win rate
  > - Wide 5x stop variant: +3.32% return, 0.46 Sharpe, 58% win rate — 10x better
  > - 56% of trades exit via stop loss (not target)
  > - 709 trades over 3 years — thin sample for statistical confidence
  > - Avg trade PnL is slightly negative (-$1.77)
  > - Fee impact unknown (0.06% taker may erase gross returns)
  > 
  > ## Key Insight
  > 
  > Wider stops dramatically improve performance. The strategy's real edge appears to be in **giving winners room to run**, not tight stop management. The current 3.0x ATR initial stop may be too tight for BTC's volatility.
  > 
  > ## Goals
  > 
  > 1. Determine if MRBB has a statistically significant edge
  > 2. Find the optimal stop distance and decay schedule
  > 3. Quantify fee drag and net-of-fees profitability
  > 4. Understand regime-dependent performance
  > 5. Paper trade validated configuration
  > 6. Deploy with small capital if edge is confirmed
  > 
  > ## Success Criteria
  > 
  > - Statistical significance test (p < 0.05 for Sharpe > 0)
  > - Net-of-fees Sharpe > 0.5 on out-of-sample data
  > - Regime analysis showing consistent edge in target market conditions
  > - 30-day paper trade with no code bugs or execution issues
  > - Clear go/no-go decision based on evidence
- [x] Backtest sweep: validate time-decay stop configurations #p1
  > Phase 8 of time-decay stop loss plan.
  > 
  > Run backtest sweep comparing 5 configurations:
  > 1. Baseline: no stops (stop_atr_multiplier=0)
  > 2. Wide constant: 3.0x ATR, no decay
  > 3. Time-decay default: 3.0x->2.0x->1.0x at 33%/66%
  > 4. Aggressive decay: 2.5x->1.5x->0.75x
  > 5. Conservative decay: 3.5x->2.5x->1.5x
  > 
  > Measure: Sharpe, max drawdown, worst single trade, total return, win rate.
  > 
  > Write sweep script and save results to backtests/mrbb/stop_decay_sweep/.
- [x] Write time-decay stop loss tests #p1
  > Phase 7 of time-decay stop loss plan.
  > 
  > Remove TestNoStopMode class (4 tests) from test_optimized_params.py.
  > 
  > New test file test_time_decay_stops.py (~9 tests):
  > - test_initial_stop_at_entry
  > - test_stop_tightens_at_phase_1 (33%)
  > - test_stop_tightens_at_phase_2 (66%)
  > - test_stop_only_tightens_never_widens
  > - test_short_stop_decay_symmetry
  > - test_manage_risk_returns_tighten_stop
  > - test_simulator_fast_stop_triggers
  > - test_compute_time_decay_stop_method
  > - test_custom_decay_params
  > 
  > Update param counts in test_param_registry.py (28->32).
  > 
  > Files: test_time_decay_stops.py (new), test_optimized_params.py, test_param_registry.py
- [x] Update presets and param registry for time-decay stops #p1
  > Phases 5-6 of time-decay stop loss plan.
  > 
  > Presets: Update 5 optimized presets (optimized, optimized_1m, optimized_3m, optimized_5m_v2, optimized_bidirectional) with stop_atr_multiplier=3.0 and decay params (0.33/0.66/2.0/1.0).
  > 
  > Param registry: Add 4 new ParamSpecs (stop_decay_phase_1/2, stop_decay_mult_1/2). Update stop_atr_multiplier range min from 0.0 to 1.0, default from 2.5 to 3.0.
  > 
  > Files: presets/*.yaml, param_registry.py
- [x] Fix live trader stop/target bugs and add time-decay support #p1
  > Phase 4 of time-decay stop loss plan.
  > 
  > Bugs to fix:
  > - _check_stop_target() missing 'if pos.stop_price > 0' guard (compares price against 0.0)
  > - manage_risk() tighten_stop is dead code (never returns new_stop value) — now functional with model changes
  > 
  > New features:
  > - Add band_ref field to Position dataclass
  > - Store band_ref at entry in _enter_position()
  > - Pass atr, band_ref, stop_price context to manage_risk() in _trading_loop()
  > 
  > File: directional_trader.py
- [x] Update simulator for always-on time-decay stops #p1
  > Phase 3 of time-decay stop loss plan.
  > 
  > Step-based path: track band_ref state, remove 'if stop_loss != 0' guards, add time-decay stop tightening per bar.
  > 
  > Fast path: add band_ref local variable, remove stop_loss==0 guards (lines 483, 505), inline time-decay logic after bars_held++, remove stop_loss=0.0 assignments at entry (lines 600, 607), set band_ref at entry.
  > 
  > Key: stops only tighten, never widen (max for longs, min for shorts).
  > 
  > File: simulator.py
- [x] Implement time-decay stop loss config and model #p1
  > Phase 1-2 of time-decay stop loss plan.
  > 
  > Add 4 new config constants (STOP_DECAY_PHASE_1/2, STOP_DECAY_MULT_1/2), change STOP_ATR_MULTIPLIER default from 2.5 to 3.0.
  > 
  > Model changes: add 4 new constructor params, add entry_band_level state, add compute_time_decay_stop() method, remove stop_atr_multiplier==0 bypass in generate_orders(), update manage_risk() with atr/band_ref/stop_price params and time-decay tighten_stop logic, update get_strategy_info().
  > 
  > Files: config.py, model.py
- [x] Build parameter preset system with YAML configs #p1
  > Create a parameter preset system that allows saving, loading, and switching between named parameter sets.
  > 
  > ## Design
  > - Presets stored as YAML files in strategies/mean_reversion_bb/presets/
  > - Each preset file contains all 18 tunable params + metadata (name, description, market regime it targets)
  > - Default presets: 'conservative', 'aggressive', 'long-only', 'ranging-market', 'trending-market'
  > - ParamPreset dataclass with load/save/validate methods
  > - CLI integration: --preset <name> flag for both trader and backtest scripts
  > 
  > ## Files
  > - strategies/mean_reversion_bb/presets.py (PresetManager class)
  > - strategies/mean_reversion_bb/presets/*.yaml (preset files)
  > - Update run_mrbb_trader.py and run_mrbb_backtest.py for --preset flag
  > - Update mrbb.sh for --preset flag
  > 
  > ## Acceptance
  > - python3 scripts/run_mrbb_trader.py --preset conservative --dry-run
  > - python3 scripts/run_mrbb_backtest.py --data data/btcusdt_5m.csv --preset aggressive
  > - Presets validated on load (type checks, range checks from param_registry)
  > 
  > Branch: feat/mean-reversion-bb
  > Depends on: param_registry.py (already exists)
- [x] MRBB Parameter Presets & Backtesting Improvements #p1
  > Epic: Build parameter preset system, fix simulator bugs, and enable multi-bot concurrent testing.
  > 
  > ## Context
  > Backtest analysis revealed: (1) simulator short accounting bug inverting P&L, (2) strategy needs parameter tuning but no way to manage presets, (3) want to run multiple bots with different params simultaneously.
  > 
  > ## Goals
  > - Fix simulator short position cash accounting
  > - Build parameter preset system (YAML/JSON config files)
  > - Enable concurrent bot instances with different presets
  > - Run parameter comparison backtests
  > - Dynamic preset loading for quick testing cycles
  > 
  > ## Success Criteria
  > - Simulator produces correct P&L for both long and short trades
  > - Parameter presets loadable from config files
  > - Multiple bot instances can run simultaneously with different presets
  > - Backtest comparison script can test multiple presets in one run
- [x] Live trade MRBB with small capital on Bybit #p1
- [x] Paper trade MRBB on live Bybit data (dry-run) #p1
- [x] Re-validate optimized parameters with CPCV and WFO #p1
- [x] Analyze parameter sensitivity and select optimal set #p1
- [x] Parameter grid search optimization #p1
- [x] Run CPCV for overfitting detection #p1
- [x] Run Monte Carlo simulation for robustness #p1
- [x] Run walk-forward optimization on historical data #p1
- [x] Analyze backtest results by market regime #p1
- [x] Run initial backtest on full historical dataset #p1
- [x] Identify market regime periods in historical data #p1
- [x] Download 2+ years of 5m BTC/USDT data from Bybit #p1
- [x] Epic: MRBB Strategy — Research, Backtest, Tune, Deploy #p1
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
- [x] Prepare for live trading deployment #p1
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
- [x] Run A-S paper trading on Bybit testnet #p1
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
- [x] Backtest BTCMomentumScalper strategy #p1
- [x] Download Binance BTC/USDT data (2017-present) #p1
- [x] Verify backtesting works with sample data #p1
- [x] Configure exchange API for paper trading #p1
- [x] Install Freqtrade #p1
- [x] Backtesting Pipeline Setup #p1
- [x] Configure Cognee knowledge base for btc-algo-trading #p1
  > Set up isolated Cognee stack with unique ports, update all scripts and documentation to use btc-specific datasets and configuration.
- [x] Go/no-go decision and small capital deployment #p2
  > Final deployment gate. Review all evidence and make a data-driven decision.
  > 
  > ## Work
  > - Compile evidence: backtest stats, significance tests, WFO results, paper trade log
  > - Calculate expected annual return, max drawdown, and Sharpe net of fees
  > - Determine appropriate capital allocation (Kelly criterion or fixed fraction)
  > - If GO: deploy with small capital on Bybit futures (start at $500-1000)
  > - If NO-GO: document what would need to change and archive the strategy
  > 
  > ## Depends On
  > - Paper trade completed
  > - All validation tasks passed
  > 
  > ## Success Criteria
  > - Clear, documented go/no-go decision based on evidence
  > - If GO: live deployment with defined risk limits
  > - If NO-GO: clear thesis on what's missing
- [x] Paper trade validated MRBB config for 30 days #p2
  > Once parameters are validated, run a 30-day paper trading session on live Bybit data to verify execution.
  > 
  > ## Work
  > - Deploy DirectionalTrader with the validated optimized preset
  > - Run in dry-run mode (real market data, simulated fills)
  > - Monitor: signal generation, order placement, stop management, time-decay behavior
  > - Compare paper trade results with backtest expectations
  > - Log any execution issues (connectivity, data gaps, etc.)
  > 
  > ## Depends On
  > - Updated optimized preset with validated parameters
  > 
  > ## Success Criteria
  > - 30 days of continuous paper trading without crashes
  > - Trade frequency matches backtest expectations (~0.65/day)
  > - No code bugs in live execution path
  > - Results directionally consistent with backtest
- [x] Create tuned parameter presets from backtest analysis #p2
  > Based on trade log analysis findings, create initial parameter presets:
  > 
  > ## Presets to create
  > 
  > 1. **default** — Current settings (baseline)
  > 2. **conservative** — Wider BB (3.0 std), higher ADX threshold (28), reduced risk (1% per trade)
  > 3. **aggressive** — Tighter BB (2.0 std), lower ADX threshold (20), higher risk (3%)
  > 4. **long-only** — Disable shorts entirely, optimized for BTC uptrend bias
  > 5. **ranging** — Optimized for low-volatility sideways markets (tight BB, low ADX threshold)
  > 6. **high-rr** — Focus on reward:risk ratio 2:1+ (wide targets, tight stops)
  > 
  > ## Parameter changes from findings
  > - Fix band_walking exit: increase threshold from 3 to 5 consecutive touches
  > - Consider disabling band_walking exit in some presets
  > - ADX threshold range: 20-30 across presets
  > - BB std range: 2.0-3.0 across presets
  > - Add long-only mode via new use_shorts config param
  > 
  > Branch: feat/mean-reversion-bb
  > Depends on: simulator fix, preset system
- [x] Build backtest comparison runner for multiple presets #p2
  > Script to backtest multiple parameter presets and produce a comparison report.
  > 
  > ## Design
  > - New script: scripts/compare_mrbb_presets.py
  > - Takes: --data, --presets (list or 'all'), --equity, --days
  > - Runs each preset through the simulator
  > - Produces comparison table: preset name, return, sharpe, max DD, trades, win rate, PF
  > - Saves results to backtests/mrbb/comparisons/{timestamp}/
  > - Optional: parallel execution via multiprocessing
  > 
  > ## Output format
  > Preset          | Return | Sharpe | Max DD | Trades | WR   | PF
  > conservative    | +5.2%  | 1.40   | -3.1%  | 450    | 42%  | 1.15
  > aggressive      | +18.1% | 2.10   | -8.5%  | 1800   | 38%  | 0.95
  > long-only       | +12.3% | 1.85   | -4.2%  | 600    | 45%  | 1.30
  > 
  > ## Acceptance
  > - python3 scripts/compare_mrbb_presets.py --data data/btcusdt_5m.csv --presets all
  > - Comparison table printed to stdout and saved to JSON/CSV
  > 
  > Branch: feat/mean-reversion-bb
  > Depends on: simulator fix, preset system
- [x] Enable concurrent bot instances with different presets #p2
  > Allow running multiple MRBB bot instances simultaneously with different parameter presets.
  > 
  > ## Design
  > - Each instance gets a unique instance ID (preset name or custom)
  > - PID files namespaced: .mrbb-{instance_id}.pid
  > - Log files namespaced: /tmp/mrbb-{instance_id}-{timestamp}.log
  > - Wrapper script supports: ./scripts/mrbb.sh start --preset conservative --id conservative-1
  > - Status command shows all running instances
  > - Stop can target specific instance or all
  > 
  > ## Changes
  > - mrbb.sh: instance ID support, 'status --all', 'stop --all' 
  > - run_mrbb_trader.py: accept --instance-id, namespace log files
  > - directional_trader.py: include instance ID in output
  > 
  > ## Acceptance
  > - Can start 2+ bots with different presets simultaneously
  > - Each has separate PID file and log file
  > - 'mrbb.sh status' shows all running instances
  > - 'mrbb.sh stop conservative-1' stops only that instance
  > 
  > Branch: feat/mean-reversion-bb
  > Depends on: preset system
- [x] Run statistical significance tests #p2
- [x] Research optimal BB parameter ranges from literature #p2

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
