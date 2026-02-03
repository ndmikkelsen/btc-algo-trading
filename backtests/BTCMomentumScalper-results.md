# BTCMomentumScalper Backtest Results

**Date**: 2026-02-01
**Data Source**: BinanceUS BTC/USD 5m

## Summary

| Period | Days | Trades | Return | Sharpe | Win Rate | Max DD | Market |
|--------|------|--------|--------|--------|----------|--------|--------|
| 2019-10 to 2023-07 | 1382 | 204 | **-12.06%** | -0.64 | 33.8% | 12.07% | +213.97% |
| 2025-02 to 2026-02 | 346 | 28 | **+0.36%** | 0.13 | 50.0% | 0.73% | -18.57% |

## Key Observations

### Historical Period (Oct 2019 - Jul 2023)
- **Lost money while BTC gained 213%** - significant underperformance
- Stop losses (-2.2% x 28 trades = -19.23%) destroyed profits
- ROI exits generated +7.17% but couldn't offset stop losses
- Win rate only 33.8% (69 wins, 107 draws, 28 losses)

### Recent Period (Feb 2025 - Feb 2026)
- Slightly profitable in declining market (+0.36% vs -18.57% BTC)
- Much better win rate: 50% (14 wins, 13 draws, 1 loss)
- Only 1 stop loss triggered vs 27 ROI exits
- Max drawdown contained at 0.73%

## Analysis

The strategy performs **better in sideways/bearish markets** than bull markets:

1. **Bull Market Problem**: EMA crossover triggers entries too late in strong uptrends, then stop losses hit during normal pullbacks
2. **Bear/Sideways Advantage**: More range-bound price action suits the scalping approach
3. **Stop Loss Issue**: -2% stoploss is too tight for 5m timeframe volatility

## Recommendations

1. **Widen stoploss** to -3% or -4% to reduce false stops
2. **Add trend filter** - only trade when in bullish higher timeframe trend
3. **Adjust RSI parameters** - current settings may be too aggressive
4. **Consider market regime detection** - different parameters for different conditions

## Exit Reason Breakdown

### Historical (2019-2023)
- ROI: 176 trades, +7.17% total
- Stop Loss: 28 trades, -19.23% total

### Recent (2025-2026)
- ROI: 27 trades, +1.09% total
- Stop Loss: 1 trade, -0.73% total

## Files

Detailed results saved in:
- `user_data/backtest_results/backtest-result-2026-02-01_15-14-24.meta.json` (2019-2023)
- `user_data/backtest_results/backtest-result-2026-02-01_15-14-41.meta.json` (2025-2026)
