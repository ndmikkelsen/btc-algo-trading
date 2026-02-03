# BTCMeanReversion Backtest Results

## Strategy Overview

Mean reversion strategy that buys oversold conditions and exits when price reverts to the mean. Uses Bollinger Bands and RSI to identify extremes.

**Entry Conditions (ALL must be true):**
1. Price at or below lower Bollinger Band (%B <= threshold)
2. RSI < oversold threshold
3. Volume spike (confirms selling exhaustion)

**Exit Conditions (ANY triggers exit):**
1. Price crosses above middle Bollinger Band (reverted to mean)
2. RSI > overbought threshold
3. ROI/Stoploss hit

## Backtest Period

- **Date Range**: 2021-07-05 to 2026-02-03 (4.5 years)
- **Data Points**: ~480,000 candles (5m timeframe)
- **Market Change**: +132.92% (strong bull market)

## Results Comparison

| Metric | Default Params | Optimized Params |
|--------|---------------|------------------|
| Total Profit | -75.54% | -9.97% |
| Trades | 2,105 | 115 |
| Win Rate | 50.3% | 56.5% |
| Max Drawdown | 75.78% | 12.85% |
| Sharpe Ratio | -3.26 | -0.23 |

## Optimized Parameters

```json
{
    "bb_period": 25,
    "bb_std": 3.0,
    "bb_oversold_threshold": -0.2,
    "rsi_period": 18,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "volume_factor": 1.1
}
```

## Exit Breakdown (Optimized)

| Exit Reason | Count | Avg Profit | Total |
|-------------|-------|------------|-------|
| ROI | 83 | +0.54% | +13.52% |
| Trailing Stop | 7 | +0.58% | +1.23% |
| Stop Loss | 25 | -3.19% | -24.72% |

## Analysis

### Why the Strategy Lost Money

1. **Strong Bull Market**: BTC gained +132.92% during the test period. Mean reversion strategies perform poorly in trending markets because:
   - They short momentum (buy when falling)
   - Trends continue longer than expected
   - Stop losses trigger during trend continuation

2. **Strategy Selectivity**: With only 115 trades over 4.5 years (1 trade every 2 weeks), the strategy missed most of the bullish moves.

3. **Risk/Reward Asymmetry**: Stop losses (-3.19%) are larger than average wins (+0.54%), requiring >85% win rate to profit.

### When Mean Reversion Works Best

- Ranging/sideways markets
- High volatility with no clear trend
- Markets with established support/resistance levels

### Recommendations

1. **Add Trend Filter**: Only trade mean reversion when ADX < 25 (no strong trend)
2. **Dynamic Position Sizing**: Reduce size in trending markets
3. **Consider Regime Detection**: Use separate strategies for trending vs ranging markets
4. **Hybrid Approach**: Combine with momentum strategy for trend-following

## Conclusion

The mean reversion strategy significantly outperformed its default configuration (-9.97% vs -75.54%) but still lost money in the strong bull market. This is expected behavior for mean reversion during trends. The optimized parameters show the strategy can be profitable in the right market conditions (demonstrated by +1.24% profit in the 2025 training period).

**Date Generated**: 2026-02-02
