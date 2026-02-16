#!/usr/bin/env python3
"""Download BTC OHLCV data from multiple exchanges for cross-validation.

Uses ccxt to fetch data from OKX, Kraken, Bitfinex, KuCoin, and Bitstamp.
(Bybit and Binance are geo-restricted from AU and excluded from defaults.)
Saves each exchange's data in a consistent CSV format for comparison.

Usage:
    python scripts/download_multi_source.py [--days 365] [--timeframe 1h]
    python scripts/download_multi_source.py --exchanges okx kraken --days 90 --timeframe 5m
"""

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import pandas as pd

# Exchange configurations: exchange_id -> (symbol, notes)
# Note: Bybit and Binance are geo-restricted from AU; excluded from defaults.
EXCHANGE_CONFIG = {
    "okx": {"symbol": "BTC/USDT", "notes": "Major exchange, good data quality"},
    "kraken": {"symbol": "BTC/USD", "notes": "Oldest exchange, USD pair (not USDT)"},
    "bitfinex": {"symbol": "BTC/USDT", "notes": "Long-running exchange, deep liquidity"},
    "kucoin": {"symbol": "BTC/USDT", "notes": "Large exchange, good API"},
    "bitstamp": {"symbol": "BTC/USD", "notes": "Oldest active exchange, USD pair"},
}

TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def create_exchange(exchange_id: str) -> ccxt.Exchange:
    """Create a ccxt exchange instance with rate limiting enabled."""
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


def download_ohlcv(
    exchange_id: str,
    timeframe: str = "1h",
    days: int = 365,
    output_dir: str = "data",
) -> pd.DataFrame | None:
    """Download OHLCV data from a single exchange.

    Returns DataFrame on success, None on failure.
    """
    config = EXCHANGE_CONFIG[exchange_id]
    symbol = config["symbol"]
    ms_per_candle = TIMEFRAME_MS.get(timeframe, 3_600_000)
    expected_candles = int((days * 86_400_000) / ms_per_candle)

    print(f"\n{'='*60}")
    print(f"  {exchange_id.upper()} — {symbol} {timeframe}")
    print(f"  {config['notes']}")
    print(f"  Expected ~{expected_candles:,} candles over {days} days")
    print(f"{'='*60}")

    try:
        exchange = create_exchange(exchange_id)

        since = int(
            (datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000
        )
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        all_ohlcv = []
        current_since = since
        batch_size = 1000
        retries = 0
        max_retries = 5

        while current_since < now_ms:
            try:
                ohlcv = exchange.fetch_ohlcv(
                    symbol, timeframe, since=current_since, limit=batch_size
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)
                retries = 0  # Reset on success

                # Progress
                pct = min(100, len(all_ohlcv) / expected_candles * 100)
                if len(all_ohlcv) % 3000 < batch_size:
                    print(f"  [{exchange_id}] {len(all_ohlcv):>7,} candles ({pct:.0f}%)")

                # Advance
                current_since = ohlcv[-1][0] + ms_per_candle

                # Rate limiting — respect exchange limits
                time.sleep(exchange.rateLimit / 1000)

            except ccxt.RateLimitExceeded:
                retries += 1
                if retries > max_retries:
                    print(f"  [{exchange_id}] Rate limit exceeded too many times, stopping")
                    break
                wait = 2**retries
                print(f"  [{exchange_id}] Rate limited, waiting {wait}s...")
                time.sleep(wait)

            except ccxt.NetworkError as e:
                retries += 1
                if retries > max_retries:
                    print(f"  [{exchange_id}] Network errors exceeded max retries: {e}")
                    break
                wait = 2**retries
                print(f"  [{exchange_id}] Network error, retrying in {wait}s: {e}")
                time.sleep(wait)

            except ccxt.ExchangeError as e:
                print(f"  [{exchange_id}] Exchange error: {e}")
                break

        if not all_ohlcv:
            print(f"  [{exchange_id}] No data downloaded!")
            return None

        # Build DataFrame
        df = pd.DataFrame(
            all_ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.drop_duplicates(subset=["timestamp"], keep="first")
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Save
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        pair_label = symbol.replace("/", "").lower()
        filename = f"{exchange_id}_{pair_label}_{timeframe}.csv"
        filepath = output_path / filename

        df.to_csv(filepath, index=False)

        # Report
        start = df["timestamp"].iloc[0]
        end = df["timestamp"].iloc[-1]
        actual_span = (end - start).days
        completeness = len(df) / expected_candles * 100

        print(f"\n  [{exchange_id}] DONE")
        print(f"  Candles: {len(df):,} ({completeness:.1f}% of expected)")
        print(f"  Range:   {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} ({actual_span} days)")
        print(f"  Saved:   {filepath}")

        return df

    except Exception as e:
        print(f"  [{exchange_id}] FAILED: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Download BTC OHLCV data from multiple exchanges"
    )
    parser.add_argument(
        "--exchanges",
        nargs="+",
        default=list(EXCHANGE_CONFIG.keys()),
        choices=list(EXCHANGE_CONFIG.keys()),
        help="Exchanges to download from (default: all)",
    )
    parser.add_argument(
        "--timeframe",
        "-t",
        default="1h",
        choices=list(TIMEFRAME_MS.keys()),
        help="Candle timeframe (default: 1h)",
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=365,
        help="Days of history to download (default: 365)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data",
        help="Output directory (default: data)",
    )
    args = parser.parse_args()

    print(f"Multi-source BTC data download")
    print(f"Timeframe: {args.timeframe}, Days: {args.days}")
    print(f"Exchanges: {', '.join(args.exchanges)}")
    print(f"Output: {args.output}/")

    results = {}
    for exchange_id in args.exchanges:
        df = download_ohlcv(
            exchange_id=exchange_id,
            timeframe=args.timeframe,
            days=args.days,
            output_dir=args.output,
        )
        results[exchange_id] = df

    # Summary
    print(f"\n{'='*60}")
    print(f"  DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    for exch, df in results.items():
        if df is not None:
            print(f"  {exch:>10}: {len(df):>8,} candles  ✓")
        else:
            print(f"  {exch:>10}: FAILED  ✗")

    successful = sum(1 for df in results.values() if df is not None)
    print(f"\n  {successful}/{len(results)} exchanges downloaded successfully")

    if successful == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
