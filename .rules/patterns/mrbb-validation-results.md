# MRBB Strategy Validation Results — NO-GO

> Complete evidence from the 5-phase validation pipeline (Feb 2026).
> This strategy was shelved after failing fee viability and statistical significance tests.

## Verdict: NO-GO for Deployment

The MRBB (Mean Reversion Bollinger Band) strategy on 5m BTC/USDT has no statistically
significant, fee-adjusted trading edge. Do not deploy capital.

## Dataset

- **Pair**: BTC/USDT perpetual (Bybit)
- **Timeframe**: 5-minute candles
- **Period**: Jan 2023 -- Feb 2026 (329,391 candles, ~3.13 years)
- **Trades**: ~676-709 depending on config

## Phase 1: Discovery

### 1a. Wide Stop Sweep

Tested 18 configurations: 6 ATR multipliers (3.5x--6.0x) x 3 decay schedules.

| Config | Sharpe | Return | MaxDD | Win Rate | Trades |
|--------|--------|--------|-------|----------|--------|
| 5.0x gentle decay (winner) | 0.57 | +3.97% | -2.99% | 55.3% | 676 |
| 5.5x gentle decay | 0.52 | +3.61% | -3.21% | 54.8% | 671 |
| 4.5x gentle decay | 0.48 | +3.28% | -2.87% | 53.9% | 681 |
| 3.0x current (baseline) | 0.07 | +0.34% | -4.55% | 44.4% | 709 |

**Finding**: Wider stops dramatically improve gross performance. 5.0x ATR with gentle
decay (5.0 -> 4.0 -> 3.25) is the Sharpe-optimal config. But even the best config
only returns +3.97% gross over 3 years.

### 1b. Fee Impact Analysis

**CRITICAL FINDING**: The simulator had no explicit exchange fees prior to this analysis.

| Config | Gross Return | Net Return | Sharpe (gross) | Sharpe (net) | Avg Fee/Trade |
|--------|-------------|------------|----------------|--------------|---------------|
| Optimized 3.0x | +0.34% | -18.89% | 0.07 | -3.59 | $2.71 |
| Best sweep 5.0x | +3.97% | ~-15.12% | 0.57 | ~-2.29 | $2.82 |

Fee structure: Bybit VIP0 taker = 0.06% per side (0.12% round-trip).
With ~676 trades, total fee drag = ~$1,909 vs ~$397 gross profit.

**The strategy trades too frequently with too small an edge per trade.**

### 1c. Regime Analysis

| Regime | Quarters | Avg Return | Avg Sharpe | Assessment |
|--------|----------|------------|------------|------------|
| Ranging | Q2'23, Q3'25 | +1.20% | +3.88 | Best regime |
| Volatile chop | Q3'24 | +0.80% | +1.67 | Decent |
| Trending down | Q3'23, Q2'24, Q1'25, Q4'25, Q1'26 | +0.21% | +0.81 | Mixed |
| Trending up | Q1'23, Q4'23, Q1'24, Q4'24, Q2'25 | -0.68% | -1.40 | Toxic |

- 8/13 quarters profitable gross (61.5%)
- Long-only mean reversion is structurally disadvantaged during bull runs
- Edge is heavily concentrated in ranging markets

## Phase 2: Validation

### 2a. Statistical Significance

Best config (5.0x gentle decay):

| Test | Result | Significant? |
|------|--------|-------------|
| t-test (Sharpe > 0) | p = 0.316 | No |
| Bootstrap (10k resamples) | p = 0.9998 | No |
| Monte Carlo permutation (10k) | p = 0.9996 | No |
| 95% CI for Sharpe | [-0.55, 1.68] | Spans zero |
| Deflated Sharpe (30 trials) | p = 0.916 | No |

**Neither config shows a statistically significant edge at any reasonable threshold.**

### 2b. Walk-Forward / CPCV

| Method | Avg IS Sharpe | Avg OOS Sharpe | OOS/IS Ratio | Verdict |
|--------|--------------|----------------|-------------|---------|
| Walk-forward (11 windows) | 0.40 | 0.77 | 1.89 | Not overfit |
| CPCV (15 splits, 50-bar purge) | 0.56 | 0.60 | 1.06 | Not overfit |

- PBO (Probability of Backtest Overfitting) = 20%
- 12/15 CPCV splits profitable OOS
- 6/11 WFO windows profitable OOS

**The signal is real (not overfit), but too small to be profitable after fees.**

## Why It Fails

1. **Edge per trade is microscopic**: avg gross PnL = -$1.77 (3.0x) to ~+$0.59 (5.0x)
2. **Fee drag dominates**: $2.71-$2.82 per trade in taker fees vs negligible edge
3. **Trade frequency is too high**: 676-709 trades over 3 years on 5m candles
4. **Regime dependence**: only 2/13 quarters (ranging) show strong positive edge

## What Would Need to Change

For a BB mean reversion concept to become viable on BTC:

| Change | Impact | Feasibility |
|--------|--------|-------------|
| Maker-only orders (0.01% vs 0.06%) | Reduces fee drag ~83% | Requires limit order management, non-fill risk |
| Longer timeframe (1h/4h) | Fewer trades, larger edge per trade | Literature supports this |
| Stricter entry filters | Reduce trades to <200, higher conviction | Needs research |
| Regime-gated trading | Skip trending-up periods | Requires reliable real-time detection |
| Bidirectional | Capture short-side edge in bear regimes | Added complexity, higher risk |

## Evidence Files

All raw results are in `backtests/mrbb/`:

- `wide_stop_sweep/` -- 18-config sweep results
- `fee_analysis/fee_impact.json` -- gross vs net comparison
- `regime_analysis/quarterly_results.json` -- per-quarter breakdown
- `significance/significance_results.json` -- bootstrap/MC/t-test/deflated Sharpe
- `walk_forward/wfo_results.json` -- WFO + CPCV results

## Scripts

Analysis scripts in `scripts/`:

- `sweep_wide_stops.py` -- ATR multiplier sweep
- `fee_analysis.py` -- fee impact calculator
- `regime_analysis.py` -- quarterly regime breakdown
- `significance_test.py` -- statistical significance battery
- `walk_forward_validation.py` -- WFO + CPCV validation

## Lessons Learned

1. **Always model fees from day one.** The simulator had no explicit fees, which masked the fundamental non-viability of the strategy for months of development.
2. **5m timeframe is hostile to mean reversion.** Too many trades with too small an edge. Literature consistently recommends 1h+ for crypto MR.
3. **Statistical significance testing is essential before deployment.** A 0.57 Sharpe looks decent until you realize p=0.32 and the CI spans zero.
4. **Walk-forward validation confirms signal reality.** The WFO/CPCV showed the signal isn't overfit -- it's just too weak. This is a useful distinction: the concept has merit, the execution parameters don't.
5. **Long-only mean reversion suffers in bull markets.** Counter-intuitive but consistent: during trending-up periods, buying dips to the lower band means buying into a trend that may not revert quickly enough.
