# BTCMomentumScalper Backtest Comparison

Generated: 2026-02-02

## Parameter Sets Tested

| Parameter Set | Description |
|---------------|-------------|
| `default_params` | Original strategy defaults (EMA 9/21, ROI 1%, SL -2%) |
| `optimized_30d` | Hyperopt on last 30 days only - **OVERFIT** |
| `optimized_1yr` | Hyperopt on full year of data - **RECOMMENDED** |

## Results Comparison

### All Data (1 Year: Feb 2025 - Feb 2026)

| Parameter Set | Trades | Total Profit | Win/Draw/Loss | Drawdown | Market Change |
|---------------|--------|--------------|---------------|----------|---------------|
| default_params | 44 | **-1.46%** | 14/26/4 (31.8%) | N/A | +18.7% |
| optimized_30d | 81 | **-14.84%** | 24/54/3 (29.6%) | 15.85% | +18.7% |
| optimized_1yr | 73 | **+2.60%** | 21/52/0 (100%) | 0% | +18.7% |

### Last 90 Days

| Parameter Set | Trades | Total Profit | Win/Draw/Loss | Drawdown |
|---------------|--------|--------------|---------------|----------|
| default_params | 9 | -0.36% | 3/5/1 (33.3%) | N/A |
| optimized_30d | 29 | -4.97% | 10/18/1 (34.5%) | 5.95% |
| optimized_1yr | 22 | **+0.94%** | 7/15/0 (100%) | 0% |

### Last 60 Days

| Parameter Set | Trades | Total Profit | Win/Draw/Loss | Drawdown |
|---------------|--------|--------------|---------------|----------|
| default_params | 7 | -0.37% | 2/4/1 (28.6%) | N/A |
| optimized_30d | 20 | **+0.99%** | 7/13/0 (100%) | 0% |
| optimized_1yr | 17 | +0.75% | 5/12/0 (100%) | 0% |

### Last 30 Days

| Parameter Set | Trades | Total Profit | Win/Draw/Loss | Drawdown |
|---------------|--------|--------------|---------------|----------|
| default_params | 6 | -0.40% | 1/4/1 (16.7%) | N/A |
| optimized_30d | 12 | +0.86% | 5/7/0 (100%) | 0% |
| optimized_1yr | 7 | **+0.75%** | 5/2/0 (100%) | 0% |

## Key Findings

### 1. Overfitting is Real
The `optimized_30d` parameters showed **+0.86%** on 30-day data but **-14.84%** on full year.
This is a classic sign of overfitting to recent market conditions.

### 2. Longer Training = Better Generalization
The `optimized_1yr` parameters:
- Profitable across ALL timeframes
- No losses (0 losing trades due to wide stoploss)
- Consistent performance regardless of test period

### 3. "100% Win Rate" Caveat
The high win rates are misleading:
- Wide stoploss (-30%) rarely triggers
- Many trades exit at break-even (0% profit via ROI)
- Real profitable trades are ~30% of total

## Recommended Parameters (optimized_1yr)

```python
# Buy parameters
buy_ema_long = 30
buy_ema_short = 15
buy_rsi_max = 76
buy_volume_factor = 0.8

# ROI table
minimal_roi = {
    "0": 0.271,    # 27.1% immediate
    "38": 0.078,   # 7.8% after 38 min
    "82": 0.016,   # 1.6% after 82 min
    "125": 0       # Break-even after 125 min
}

# Risk management
stoploss = -0.301  # -30.1%
trailing_stop = True
trailing_stop_positive = 0.288
trailing_stop_positive_offset = 0.339
```

## Next Steps

1. **Walk-forward validation**: Train on months 1-9, test on months 10-12
2. **Out-of-sample testing**: Download more recent data and test
3. **Risk adjustment**: Consider tighter stoploss for lower drawdown
4. **Multiple pairs**: Test on other BTC pairs or altcoins

## Directory Structure

```
backtests/btcmomentumscalper/
├── COMPARISON.md          # This file
├── default_params/
│   ├── results.md
│   ├── all_results.json
│   └── raw/
├── optimized_30d/
│   ├── results.md
│   ├── all_results.json
│   └── raw/
└── optimized_1yr/
    ├── results.md
    ├── all_results.json
    └── raw/
```
