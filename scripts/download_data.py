#!/usr/bin/env python3
"""Download historical OHLCV data from Bybit for backtesting.

Usage:
    python scripts/download_data.py                          # Download 5m BTC/USDT
    python scripts/download_data.py --timeframe 1h           # Download 1h candles
    python scripts/download_data.py --start 2023-01-01       # Custom start date
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

import ccxt
import pandas as pd


# Bybit API returns max 200 candles per request
BYBIT_LIMIT = 200

# Milliseconds per timeframe
TIMEFRAME_MS = {
    "1m": 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}

SYMBOL = "BTC/USDT:USDT"
OUTPUT_DIR = "data"


def init_exchange() -> ccxt.bybit:
    """Initialize ccxt Bybit exchange (public, no auth needed).

    Reads SOCKS5_PROXY from environment for geo-restricted regions.
    """
    config: dict = {"enableRateLimit": True}

    proxy = os.getenv("SOCKS5_PROXY")
    if proxy:
        config["proxies"] = {"http": proxy, "https": proxy}
        print(f"Using proxy: {proxy}")

    return ccxt.bybit(config)


def load_existing_data(filepath: str) -> pd.DataFrame | None:
    """Load existing CSV and return DataFrame, or None if file doesn't exist."""
    if not os.path.exists(filepath):
        return None

    df = pd.read_csv(filepath)
    if df.empty:
        return None

    print(f"Found existing data: {len(df)} rows")
    print(f"  Last timestamp: {df['timestamp'].iloc[-1]} ms")
    return df


def download_ohlcv(
    timeframe: str = "5m",
    start_date: str | None = None,
    output_dir: str = OUTPUT_DIR,
) -> pd.DataFrame:
    """Download OHLCV data from Bybit, appending to existing CSV if present.

    Args:
        timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d).
        start_date: Start date as YYYY-MM-DD string. Defaults to 2 years ago.
        output_dir: Directory to save output CSV.

    Returns:
        Complete DataFrame with all downloaded data.
    """
    ms_per_candle = TIMEFRAME_MS.get(timeframe)
    if ms_per_candle is None:
        print(f"Error: unsupported timeframe '{timeframe}'")
        print(f"Supported: {', '.join(TIMEFRAME_MS.keys())}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    filename = f"btcusdt_{timeframe}.csv"
    filepath = os.path.join(output_dir, filename)

    # Determine start time
    existing_df = load_existing_data(filepath)

    if existing_df is not None:
        # Resume from last timestamp + 1 candle
        since_ms = int(existing_df["timestamp"].iloc[-1]) + ms_per_candle
        print(f"Resuming download from {datetime.fromtimestamp(since_ms / 1000, tz=timezone.utc).isoformat()}")
    elif start_date:
        dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        since_ms = int(dt.timestamp() * 1000)
    else:
        # Default: 2 years ago
        now = datetime.now(timezone.utc)
        start = now.replace(year=now.year - 2)
        since_ms = int(start.timestamp() * 1000)

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    if since_ms >= now_ms:
        print("Data is already up to date.")
        return existing_df if existing_df is not None else pd.DataFrame()

    print(f"Downloading {SYMBOL} {timeframe} from Bybit")
    start_dt = datetime.fromtimestamp(since_ms / 1000, tz=timezone.utc)
    print(f"  From: {start_dt.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Symbol: {SYMBOL}")

    expected_candles = (now_ms - since_ms) // ms_per_candle
    print(f"  Expected: ~{expected_candles:,} candles")

    exchange = init_exchange()

    # Fetch in paginated batches
    all_rows: list[list] = []
    request_count = 0
    current_since = since_ms

    while current_since < now_ms:
        try:
            ohlcv = exchange.fetch_ohlcv(
                SYMBOL, timeframe, since=current_since, limit=BYBIT_LIMIT
            )
        except ccxt.RateLimitExceeded:
            print("  Rate limited, waiting 5s...")
            time.sleep(5)
            continue
        except ccxt.NetworkError as e:
            print(f"  Network error: {e}, retrying in 2s...")
            time.sleep(2)
            continue

        if not ohlcv:
            break

        all_rows.extend(ohlcv)
        request_count += 1

        # Advance past last candle
        current_since = ohlcv[-1][0] + ms_per_candle

        # Progress every 50 requests
        if request_count % 50 == 0:
            fetched_dt = datetime.fromtimestamp(ohlcv[-1][0] / 1000, tz=timezone.utc)
            print(f"  [{request_count} requests] {len(all_rows):,} candles, up to {fetched_dt.strftime('%Y-%m-%d %H:%M UTC')}")

        # Rate limiting: 100ms between requests
        time.sleep(0.1)

    if not all_rows:
        print("No new data to download.")
        return existing_df if existing_df is not None else pd.DataFrame()

    # Build DataFrame from new data
    new_df = pd.DataFrame(
        all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )

    # Deduplicate by timestamp
    new_df = new_df.drop_duplicates(subset=["timestamp"], keep="first")
    new_df = new_df.sort_values("timestamp").reset_index(drop=True)

    # Merge with existing data
    if existing_df is not None:
        df = pd.concat([existing_df, new_df], ignore_index=True)
        df = df.drop_duplicates(subset=["timestamp"], keep="first")
        df = df.sort_values("timestamp").reset_index(drop=True)
    else:
        df = new_df

    # Validate data
    issues = validate_data(df, ms_per_candle)

    # Save
    df.to_csv(filepath, index=False)
    print(f"\nSaved {len(df):,} candles to {filepath}")

    first_dt = datetime.fromtimestamp(df["timestamp"].iloc[0] / 1000, tz=timezone.utc)
    last_dt = datetime.fromtimestamp(df["timestamp"].iloc[-1] / 1000, tz=timezone.utc)
    print(f"  Range: {first_dt.strftime('%Y-%m-%d')} to {last_dt.strftime('%Y-%m-%d')}")

    if issues:
        print(f"\n  Validation warnings: {len(issues)}")
        for issue in issues[:10]:
            print(f"    - {issue}")
        if len(issues) > 10:
            print(f"    ... and {len(issues) - 10} more")

    return df


def validate_data(df: pd.DataFrame, ms_per_candle: int) -> list[str]:
    """Validate OHLCV data quality.

    Checks:
    - Gap detection: missing candles between consecutive timestamps.
    - OHLC relationships: high >= max(open, close), low <= min(open, close).

    Args:
        df: OHLCV DataFrame with 'timestamp' column in UTC milliseconds.
        ms_per_candle: Expected milliseconds between consecutive candles.

    Returns:
        List of validation warning strings.
    """
    issues: list[str] = []

    # 1. Gap detection
    timestamps = df["timestamp"].values
    diffs = timestamps[1:] - timestamps[:-1]
    gaps = diffs != ms_per_candle
    gap_count = int(gaps.sum())

    if gap_count > 0:
        # Report first few gaps
        gap_indices = gaps.nonzero()[0]
        for idx in gap_indices[:5]:
            expected = ms_per_candle
            actual = int(diffs[idx])
            missing = (actual // ms_per_candle) - 1
            gap_dt = datetime.fromtimestamp(timestamps[idx] / 1000, tz=timezone.utc)
            issues.append(
                f"Gap at {gap_dt.strftime('%Y-%m-%d %H:%M')}: "
                f"{missing} missing candle(s) ({actual}ms vs expected {expected}ms)"
            )
        if gap_count > 5:
            issues.append(f"... {gap_count - 5} more gaps")

    # 2. OHLC relationship checks
    bad_high = df["high"] < df[["open", "close"]].max(axis=1)
    bad_low = df["low"] > df[["open", "close"]].min(axis=1)

    if bad_high.any():
        count = int(bad_high.sum())
        issues.append(f"{count} candle(s) where high < max(open, close)")

    if bad_low.any():
        count = int(bad_low.sum())
        issues.append(f"{count} candle(s) where low > min(open, close)")

    if not issues:
        print("  Data validation: PASSED")
    else:
        print(f"  Data validation: {len(issues)} warning(s)")

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Download BTC/USDT OHLCV data from Bybit for backtesting."
    )
    parser.add_argument(
        "--timeframe", "-t", default="5m",
        help="Candle timeframe: 1m, 5m, 15m, 1h, 4h, 1d (default: 5m)",
    )
    parser.add_argument(
        "--start", "-s", default=None,
        help="Start date as YYYY-MM-DD (default: 2 years ago)",
    )
    parser.add_argument(
        "--output", "-o", default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )

    args = parser.parse_args()

    download_ohlcv(
        timeframe=args.timeframe,
        start_date=args.start,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
