#!/usr/bin/env python3
"""Download BTC/USDT historical data from Bybit.

Usage:
    python scripts/download_data.py [--timeframe 1h] [--days 365]
"""

import argparse
import pandas as pd
import ccxt
from pathlib import Path
from datetime import datetime, timedelta
import time


def download_ohlcv(
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    days: int = 365,
    exchange_id: str = "bybit",
    output_dir: str = "data",
) -> pd.DataFrame:
    """
    Download OHLCV data from exchange.

    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
        days: Number of days of history to download
        exchange_id: Exchange to use (bybit, binance, etc.)
        output_dir: Directory to save data

    Returns:
        DataFrame with OHLCV data
    """
    print(f"Downloading {symbol} {timeframe} data from {exchange_id}")
    print(f"Fetching {days} days of history...")

    # Initialize exchange
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        'enableRateLimit': True,
    })

    # Calculate start time
    since = exchange.parse8601(
        (datetime.utcnow() - timedelta(days=days)).isoformat()
    )

    # Timeframe to milliseconds
    timeframe_ms = {
        '1m': 60 * 1000,
        '5m': 5 * 60 * 1000,
        '15m': 15 * 60 * 1000,
        '1h': 60 * 60 * 1000,
        '4h': 4 * 60 * 60 * 1000,
        '1d': 24 * 60 * 60 * 1000,
    }

    ms_per_candle = timeframe_ms.get(timeframe, 60 * 60 * 1000)
    expected_candles = int((days * 24 * 60 * 60 * 1000) / ms_per_candle)

    print(f"Expected ~{expected_candles} candles")

    # Fetch data in batches
    all_ohlcv = []
    current_since = since
    batch_size = 1000  # Most exchanges limit to 1000 per request

    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(
                symbol,
                timeframe,
                since=current_since,
                limit=batch_size,
            )

            if not ohlcv:
                break

            all_ohlcv.extend(ohlcv)

            # Progress update
            if len(all_ohlcv) % 5000 == 0:
                print(f"  Downloaded {len(all_ohlcv)} candles...")

            # Move to next batch
            current_since = ohlcv[-1][0] + ms_per_candle

            # Stop if we've reached current time
            if current_since > exchange.milliseconds():
                break

            # Rate limiting
            time.sleep(exchange.rateLimit / 1000)

        except Exception as e:
            print(f"Error fetching data: {e}")
            break

    if not all_ohlcv:
        raise ValueError("No data downloaded")

    # Convert to DataFrame
    df = pd.DataFrame(
        all_ohlcv,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')

    # Remove duplicates
    df = df[~df.index.duplicated(keep='first')]

    # Sort by time
    df = df.sort_index()

    print(f"Downloaded {len(df)} candles")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")

    # Save to file
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    filename = f"btcusdt_{timeframe}.csv"
    filepath = output_path / filename

    df.to_csv(filepath)
    print(f"Saved to {filepath}")

    return df


def main():
    parser = argparse.ArgumentParser(description="Download BTC/USDT OHLCV data")
    parser.add_argument('--timeframe', '-t', default='1h',
                        help='Timeframe (1m, 5m, 15m, 1h, 4h, 1d)')
    parser.add_argument('--days', '-d', type=int, default=365,
                        help='Days of history to download')
    parser.add_argument('--exchange', '-e', default='bybit',
                        help='Exchange (bybit, binance)')
    parser.add_argument('--output', '-o', default='data',
                        help='Output directory')

    args = parser.parse_args()

    download_ohlcv(
        symbol="BTC/USDT",
        timeframe=args.timeframe,
        days=args.days,
        exchange_id=args.exchange,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
