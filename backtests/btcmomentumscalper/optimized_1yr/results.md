# Backtest Results: optimized_1yr

Generated: 2026-02-02 19:47:07

## Summary Table

| Timerange | Trades | Total Profit | Win/Draw/Loss | Drawdown | Market |
|-----------|--------|--------------|---------------|----------|--------|
| 20250202-20260203 | 73 | 2.6 | 21    52     0   100 | 0 USDT  0.00% | -22.14% |
| 20251106-20260203 | 22 | 0.94 | 7    15     0   100 | 0 USDT  0.00% | -24.21% |
| 20251205-20260203 | 17 | 0.75 | 5    12     0   100 | 0 USDT  0.00% | -14.84% |
| 20260104-20260203 | 7 | 0.75 | 5     2     0   100 | 0 USDT  0.00% | -13.64% |

## Analysis

### Key Observations
- Compare total profit % to market change % to assess strategy performance
- Win rate alone is misleading - check if "draws" (0% profit) dominate
- Drawdown indicates risk - higher drawdown = more risk

### Recommendations
- If strategy underperforms market on longer timeframes, consider re-optimization
- Walk-forward validation: train on older data, test on recent data
- Avoid overfitting by using larger training datasets
