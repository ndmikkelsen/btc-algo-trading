# Backtest Results: default_params

Generated: 2026-02-02 19:47:33

## Summary Table

| Timerange | Trades | Total Profit | Win/Draw/Loss | Drawdown | Market |
|-----------|--------|--------------|---------------|----------|--------|
| 20250202-20260203 | 44 | -1.46 | 14    26     4  31.8 | 223.995 USDT  2.23% | -22.14% |
| 20251106-20260203 | 9 | -0.36 | 3     5     1  33.3 | 72.564 USDT  0.73% | -24.21% |
| 20251205-20260203 | 7 | -0.37 | 2     4     1  28.6 | 72.557 USDT  0.73% | -14.84% |
| 20260104-20260203 | 6 | -0.4 | 1     4     1  16.7 | 72.533 USDT  0.73% | -13.64% |

## Analysis

### Key Observations
- Compare total profit % to market change % to assess strategy performance
- Win rate alone is misleading - check if "draws" (0% profit) dominate
- Drawdown indicates risk - higher drawdown = more risk

### Recommendations
- If strategy underperforms market on longer timeframes, consider re-optimization
- Walk-forward validation: train on older data, test on recent data
- Avoid overfitting by using larger training datasets
