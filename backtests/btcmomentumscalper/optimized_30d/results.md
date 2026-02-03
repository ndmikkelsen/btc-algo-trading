# Backtest Results: optimized_30d

Generated: 2026-02-02 19:42:23

## Summary Table

| Timerange | Trades | Total Profit | Win/Draw/Loss | Drawdown | Market |
|-----------|--------|--------------|---------------|----------|--------|
| 20250202-20260203 | 81 | -14.84 | 24    54     3  29.6 | 1587.24 USDT  15.85% | -22.14% |
| 20251106-20260203 | 29 | -4.97 | 10    18     1  34.5 | 595.431 USDT  5.95% | -24.21% |
| 20251205-20260203 | 20 | 0.99 | 7    13     0   100 | 0 USDT  0.00% | -14.84% |
| 20260104-20260203 | 12 | 0.86 | 5     7     0   100 | 0 USDT  0.00% | -13.64% |

## Analysis

### Key Observations
- Compare total profit % to market change % to assess strategy performance
- Win rate alone is misleading - check if "draws" (0% profit) dominate
- Drawdown indicates risk - higher drawdown = more risk

### Recommendations
- If strategy underperforms market on longer timeframes, consider re-optimization
- Walk-forward validation: train on older data, test on recent data
- Avoid overfitting by using larger training datasets
