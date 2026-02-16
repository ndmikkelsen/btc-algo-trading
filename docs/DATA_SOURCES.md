# Data Sources

BTC OHLCV data for backtesting and cross-validation.

## Exchange Sources

### USDT-paired exchanges (primary)

| Exchange | Pair | API | 1h History | Grade | Notes |
|----------|------|-----|------------|-------|-------|
| **OKX** | BTC/USDT | ccxt (public) | 365 days (8,761 candles) | A | Best accessible source. Full history, zero gaps, 100% completeness. Also has 5m (90 days) and 1m (30 days) data. |
| **KuCoin** | BTC/USDT | ccxt (public) | 365 days (8,760 candles) | A | Full history, zero gaps. Volume slightly lower than OKX. |
| **Bitfinex** | BTC/USDT | ccxt (public) | 365 days (8,760 candles) | A | Full history, zero gaps. Lowest volume of USDT exchanges. |

### USD-paired exchanges (cross-validation)

| Exchange | Pair | API | 1h History | Grade | Notes |
|----------|------|-----|------------|-------|-------|
| **Bitstamp** | BTC/USD | ccxt (public) | 365 days (8,760 candles) | A | Oldest active exchange. Full history. Consistent ~0.1% offset from USDT exchanges (USD/USDT basis). |
| **Kraken** | BTC/USD | ccxt (public) | 30 days (721 candles) | A | Excellent data quality but API only returns ~30 days of 1h candles. Useful for recent validation only. |

### Geo-restricted (not accessible from AU)

| Exchange | Status | Notes |
|----------|--------|-------|
| **Bybit** | 403 Blocked | CloudFront geo-restriction. Primary trading target but data unavailable for download. |
| **Binance** | 451 Blocked | Geo-restricted per terms of service. |

## Data Files

Located in `data/` (gitignored).

### 1-hour candles (365 days)
- `okx_btcusdt_1h.csv` — 8,761 candles, 2025-02-09 to 2026-02-09
- `kucoin_btcusdt_1h.csv` — 8,760 candles, 2025-02-09 to 2026-02-09
- `bitfinex_btcusdt_1h.csv` — 8,760 candles, 2025-02-09 to 2026-02-09
- `bitstamp_btcusd_1h.csv` — 8,760 candles, 2025-02-09 to 2026-02-09
- `kraken_btcusd_1h.csv` — 721 candles, 2026-01-10 to 2026-02-09

### Higher resolution (OKX only)
- `okx_btcusdt_5m.csv` — 25,920 candles, 90 days (2025-11-11 to 2026-02-09)
- `okx_btcusdt_1m.csv` — 43,200 candles, 30 days (2026-01-10 to 2026-02-09)

### Derived
- `aligned_multi_exchange_1h.csv` — All 5 exchanges aligned on common timestamps (721 rows)
- `data_quality_report_1h.txt` — Full quality report

## Cross-Exchange Analysis

### Key Findings

**USDT exchanges cluster tightly.** OKX, KuCoin, and Bitfinex show <0.01% mean deviation from each other. Any of these three produce essentially identical backtest results.

**USD/USDT basis is ~0.1%.** Bitstamp and Kraken (USD pairs) consistently sit ~0.1% below USDT exchanges. This is the stablecoin premium, not a data quality issue.

**Maximum cross-exchange spread: 0.33%.** Occurred during the Feb 4-5 2026 volatility event. Even at peak, all exchanges agree within 0.35%.

**Zero suspect data points.** No exchange deviated >1% from the median at any timestamp. Data integrity is excellent across all sources.

### Backtest Impact

The mean cross-exchange spread of 0.12% is significant if a strategy targets 0.1% per trade. **Recommendation: use exchange-specific data matching the deployment target.** Since Bybit is geo-blocked for downloads, OKX is the best proxy — both are major USDT exchanges with tight spreads between them historically.

For strategies with >0.5% per-trade target, any USDT source gives reliable results.

## How to Refresh Data

```bash
# Full refresh (all exchanges, 1h, 365 days)
python3 scripts/download_multi_source.py

# Specific exchange and timeframe
python3 scripts/download_multi_source.py --exchanges okx kucoin --timeframe 5m --days 90

# Validate after download
python3 scripts/validate_data.py --timeframe 1h

# Cross-exchange comparison
python3 scripts/compare_exchanges.py --timeframe 1h --save-aligned
```

## CSV Format

All files use consistent format:
```
timestamp,open,high,low,close,volume
2025-02-09 22:00:00+00:00,97502.1,97600.0,97350.0,97411.2,142.35
```

- `timestamp`: UTC datetime with timezone
- `open/high/low/close`: Price in quote currency (USDT or USD)
- `volume`: Base currency volume (BTC)
