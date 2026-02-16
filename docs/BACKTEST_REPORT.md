# Rigorous Backtest Report

**Date**: 2026-02-09 19:15
**Strategy**: Avellaneda-Stoikov Market Making (post-audit fixes)
**Fixes Applied**: C1 (double-fill), C2 (fill model), C3 (reservation price), C4 (spread scaling), C5 (stop-loss)

---

## Executive Summary

- **Monte Carlo Mean Return**: -1.02% (90% CI: [-1.29%, -0.57%])
- **Profitable in**: 0% of simulations
- **Mean Sharpe**: -3.80
- **Out-of-Sample Return**: -0.15%
- **Out-of-Sample Sharpe**: -2.24

**Verdict**: **NO RELIABLE EDGE DETECTED**

---

## 1. Walk-Forward Analysis

| Fold | Train Period | Test Period | Train Return | Test Return | Train Sharpe | Test Sharpe |
|------|-------------|------------|-------------|------------|-------------|------------|
| 1 | 2025-02-09→2025-08-08 | 2025-08-08→2025-10-07 | -0.48% | -0.18% | -5.03 | -9.00 |
| 2 | 2025-04-10→2025-10-07 | 2025-10-07→2025-12-06 | -0.55% | -0.20% | -7.41 | -4.12 |
| 3 | 2025-06-09→2025-12-06 | 2025-12-06→2026-02-04 | -0.17% | -0.11% | -1.42 | -2.98 |

**Average Train Return**: -0.40%
**Average Test Return**: -0.16%
**Performance Degradation**: -59%

## 2. Out-of-Sample Test

| Metric | In-Sample | Out-of-Sample |
|--------|-----------|--------------|
| Return | -0.65% | -0.15% |
| Sharpe | -4.12 | -2.24 |
| Trades | 206 | 57 |
| Max DD | -0.75% | -0.24% |
| Stop-losses | 128 | 34 |

## 3. Parameter Sensitivity

### risk_aversion (base=0.1)

| Multiplier | Value | Return | Sharpe | Trades |
|-----------|-------|--------|--------|--------|
| 50% | 0.0500 | -0.88% | -4.48 | 274 |
| 80% | 0.0800 | -0.88% | -4.48 | 274 |
| 100% | 0.1000 | -0.88% | -4.48 | 274 |
| 120% | 0.1200 | -0.88% | -4.48 | 274 |
| 150% | 0.1500 | -0.88% | -4.48 | 274 |

### order_book_liquidity (base=1.5)

| Multiplier | Value | Return | Sharpe | Trades |
|-----------|-------|--------|--------|--------|
| 50% | 0.7500 | -0.88% | -4.48 | 274 |
| 80% | 1.2000 | -0.88% | -4.48 | 274 |
| 100% | 1.5000 | -0.88% | -4.48 | 274 |
| 120% | 1.8000 | -0.88% | -4.48 | 274 |
| 150% | 2.2500 | -0.88% | -4.48 | 274 |

### min_spread (base=0.0005)

| Multiplier | Value | Return | Sharpe | Trades |
|-----------|-------|--------|--------|--------|
| 50% | 0.0003 | -1.24% | -3.51 | 268 |
| 80% | 0.0004 | -0.54% | -1.77 | 286 |
| 100% | 0.0005 | -0.88% | -4.48 | 274 |
| 120% | 0.0006 | -1.24% | -6.14 | 260 |
| 150% | 0.0008 | -1.12% | -4.66 | 272 |

### volatility_window (base=50)

| Multiplier | Value | Return | Sharpe | Trades |
|-----------|-------|--------|--------|--------|
| 50% | 25.0000 | -0.88% | -4.48 | 274 |
| 80% | 40.0000 | -0.88% | -4.48 | 274 |
| 100% | 50.0000 | -0.88% | -4.48 | 274 |
| 120% | 60.0000 | -0.88% | -4.48 | 274 |
| 150% | 75.0000 | -0.88% | -4.48 | 274 |


## 4. Fee Sensitivity

| Fee Level | Return | Sharpe | Trades |
|----------|--------|--------|--------|
| 0.050% | -0.73% | -3.77 | 274 |
| 0.075% | -0.80% | -4.13 | 274 |
| 0.100% | -0.88% | -4.48 | 274 |
| 0.125% | -0.96% | -4.83 | 274 |
| 0.150% | -1.04% | -5.16 | 274 |
| 0.200% | -1.19% | -5.80 | 274 |

## 5. Slippage Sensitivity

| Max Slippage | Return | Sharpe | Trades |
|-------------|--------|--------|--------|
| 0.000% | -0.89% | -4.52 | 273 |
| 0.010% | -0.88% | -4.48 | 274 |
| 0.020% | -0.55% | -1.47 | 269 |
| 0.050% | -0.55% | -1.46 | 268 |
| 0.100% | -0.57% | -1.51 | 268 |

## 6. Fill Rate Sensitivity

| Fill Level | Return | Sharpe | Trades |
|-----------|--------|--------|--------|
| High (20) | -1.95% | -7.79 | 535 |
| Default (10) | -0.88% | -4.48 | 274 |
| Conservative (5) | -0.55% | -1.68 | 129 |
| Very Conservative (2) | -0.16% | -1.02 | 43 |

## 7. Multi-Source Data Comparison

| Exchange | Candles | Return | Sharpe | Trades | Max DD | Stop-Losses |
|---------|---------|--------|--------|--------|--------|-------------|
| OKX | 8761 | -0.88% | -4.48 | 274 | -0.99% | 173 |
| KuCoin | 8760 | -1.27% | -6.34 | 252 | -1.30% | 187 |
| Bitfinex | 8760 | -1.00% | -6.42 | 237 | -1.03% | 166 |
| Kraken | 721 | -0.08% | -7.97 | 26 | -0.09% | 22 |
| Bitstamp | 8760 | -1.02% | -5.33 | 258 | -1.08% | 187 |

**Return Spread**: 1.19% (max -0.08%, min -1.27%)

## 8. Monte Carlo Simulation

**Iterations**: 50

| Metric | Value |
|--------|-------|
| Mean Return | -1.02% |
| Median Return | -1.08% |
| 5th Percentile | -1.29% |
| 95th Percentile | -0.57% |
| Std Dev | 0.23% |
| Mean Sharpe | -3.80 |
| Median Sharpe | -3.93 |
| % Profitable | 0% |
| Avg Trades | 285 ± 18 |

---

## Conclusion

### Key Findings After Fixes

1. **Strategy is NOT profitable** after applying realistic fill model, slippage, and stop-losses
2. Out-of-sample performance is NEGATIVE (-0.15%)
3. Parameters show reasonable stability (no overfitting flags)
4. Results are consistent across data sources (spread: 1.2%)

### Impact of Audit Fixes

- **C1 (Double-fill fix)**: Only one side fills per candle — eliminates free spread capture
- **C2 (Realistic fills)**: Fill probability based on penetration depth, slippage added
- **C3 (Reservation price)**: Using paper's exact formula (absolute adjustment, not percentage)
- **C4 (Spread normalization)**: Spread properly scaled relative to price
- **C5 (Stop-loss)**: Positions force-closed at 0.5% loss
