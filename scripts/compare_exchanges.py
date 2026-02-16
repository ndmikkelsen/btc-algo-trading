#!/usr/bin/env python3
"""Compare BTC price data across exchanges.

Aligns timestamps, calculates deviation statistics, and identifies
periods of high cross-exchange spread. Helps understand how much
backtest results depend on which exchange's data is used.

Usage:
    python scripts/compare_exchanges.py [--data-dir data] [--timeframe 1h]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def load_and_align(data_dir: str, timeframe: str) -> pd.DataFrame | None:
    """Load all exchange CSVs and align on timestamp."""
    data_path = Path(data_dir)
    files = sorted(data_path.glob(f"*_{timeframe}.csv"))

    if not files:
        print(f"No {timeframe} data files found in {data_dir}/")
        return None

    merged = None
    exchanges = []

    for filepath in files:
        exchange = filepath.stem.split("_")[0]
        try:
            df = pd.read_csv(filepath, parse_dates=["timestamp"])
            # Floor timestamps for alignment
            df["timestamp"] = df["timestamp"].dt.floor("min")
            df = df.drop_duplicates(subset=["timestamp"], keep="first")

            # Rename columns with exchange prefix
            rename = {
                col: f"{exchange}_{col}"
                for col in ["open", "high", "low", "close", "volume"]
            }
            df = df.rename(columns=rename)

            if merged is None:
                merged = df
            else:
                merged = merged.merge(df, on="timestamp", how="inner")

            exchanges.append(exchange)
            print(f"  Loaded {exchange}: {len(df):,} candles")

        except Exception as e:
            print(f"  Failed {filepath.name}: {e}")

    if merged is None or len(exchanges) < 2:
        print("Need at least 2 exchanges for comparison")
        return None

    merged = merged.sort_values("timestamp").reset_index(drop=True)
    print(f"\n  Aligned dataset: {len(merged):,} common candles across {len(exchanges)} exchanges")
    return merged


def compute_spread_stats(merged: pd.DataFrame) -> None:
    """Calculate and display cross-exchange spread statistics."""
    close_cols = [c for c in merged.columns if c.endswith("_close")]
    exchanges = [c.replace("_close", "") for c in close_cols]

    if len(exchanges) < 2:
        return

    print(f"\n{'='*70}")
    print(f"  CROSS-EXCHANGE PRICE COMPARISON")
    print(f"{'='*70}")

    # Reference: median price across all exchanges
    close_matrix = merged[close_cols]
    median_price = close_matrix.median(axis=1)
    merged["median_close"] = median_price

    # Per-exchange deviation from median
    print(f"\n1. DEVIATION FROM MEDIAN PRICE")
    print("-" * 50)
    for exchange in exchanges:
        col = f"{exchange}_close"
        deviation_pct = (merged[col] - median_price) / median_price * 100
        print(f"\n  {exchange.upper()}")
        print(f"    Mean deviation:    {deviation_pct.mean():+.4f}%")
        print(f"    Std deviation:     {deviation_pct.std():.4f}%")
        print(f"    Max above median:  {deviation_pct.max():+.4f}%")
        print(f"    Max below median:  {deviation_pct.min():+.4f}%")

    # Pairwise spread
    print(f"\n\n2. PAIRWISE SPREAD STATISTICS")
    print("-" * 50)
    for i, ex1 in enumerate(exchanges):
        for ex2 in exchanges[i + 1:]:
            spread_pct = (
                (merged[f"{ex1}_close"] - merged[f"{ex2}_close"])
                / merged[f"{ex1}_close"]
                * 100
            )
            print(f"\n  {ex1.upper()} vs {ex2.upper()}")
            print(f"    Mean spread:   {spread_pct.mean():+.4f}%")
            print(f"    Abs mean:      {spread_pct.abs().mean():.4f}%")
            print(f"    Max spread:    {spread_pct.abs().max():.4f}%")
            print(f"    Std:           {spread_pct.std():.4f}%")
            print(f"    P95 abs:       {spread_pct.abs().quantile(0.95):.4f}%")
            print(f"    P99 abs:       {spread_pct.abs().quantile(0.99):.4f}%")

    # Time-windowed analysis: find periods of high deviation
    print(f"\n\n3. HIGH-DEVIATION PERIODS")
    print("-" * 50)

    # Calculate max spread at each timestamp (range across all exchanges)
    max_spread_pct = (close_matrix.max(axis=1) - close_matrix.min(axis=1)) / median_price * 100
    merged["max_spread_pct"] = max_spread_pct

    print(f"  Overall max cross-exchange spread: {max_spread_pct.max():.4f}%")
    print(f"  Mean cross-exchange spread:        {max_spread_pct.mean():.4f}%")
    print(f"  Median:                            {max_spread_pct.median():.4f}%")

    # Find top 10 highest-spread timestamps
    top_spread = merged.nlargest(10, "max_spread_pct")
    print(f"\n  Top 10 highest-spread moments:")
    for _, row in top_spread.iterrows():
        ts = row["timestamp"]
        spread = row["max_spread_pct"]
        prices = {ex: f"${row[f'{ex}_close']:,.0f}" for ex in exchanges}
        prices_str = ", ".join(f"{k}={v}" for k, v in prices.items())
        print(f"    {ts}  spread={spread:.3f}%  ({prices_str})")

    # Rolling 24h average spread
    if len(merged) > 24:
        rolling_spread = max_spread_pct.rolling(24, min_periods=12).mean()
        high_spread_periods = merged[rolling_spread > rolling_spread.quantile(0.95)]
        if len(high_spread_periods) > 0:
            print(f"\n  Periods with elevated spread (top 5% of 24h rolling avg):")
            print(f"    {len(high_spread_periods)} candles affected")
            # Group into contiguous periods
            if len(high_spread_periods) > 0:
                first = high_spread_periods["timestamp"].iloc[0]
                last = high_spread_periods["timestamp"].iloc[-1]
                print(f"    Earliest: {first}")
                print(f"    Latest:   {last}")

    # Volume comparison
    print(f"\n\n4. VOLUME COMPARISON")
    print("-" * 50)
    vol_cols = [c for c in merged.columns if c.endswith("_volume")]
    for col in vol_cols:
        exchange = col.replace("_volume", "")
        vol = merged[col]
        print(f"  {exchange.upper():>10}: mean={vol.mean():>14,.0f}  median={vol.median():>14,.0f}  total={vol.sum():>18,.0f}")

    # Backtest impact estimate
    print(f"\n\n5. BACKTEST IMPACT ESTIMATE")
    print("-" * 50)
    print(f"  If a strategy captures 0.1% per trade, cross-exchange spread of")
    print(f"  {max_spread_pct.mean():.4f}% means {max_spread_pct.mean()/0.1*100:.1f}% of per-trade profit is within")
    print(f"  data-source uncertainty. This {'IS' if max_spread_pct.mean() > 0.05 else 'is NOT'} significant.")
    print(f"\n  Recommendation: {'Use exchange-specific data matching your deployment target' if max_spread_pct.mean() > 0.05 else 'Cross-exchange differences are minimal; any source should give reliable results'}.")

    print(f"\n{'='*70}")


def save_aligned_data(merged: pd.DataFrame, data_dir: str, timeframe: str) -> None:
    """Save the aligned, multi-exchange dataset."""
    output_path = Path(data_dir) / f"aligned_multi_exchange_{timeframe}.csv"
    merged.to_csv(output_path, index=False)
    print(f"\nAligned dataset saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Compare BTC price data across exchanges"
    )
    parser.add_argument("--data-dir", default="data", help="Data directory")
    parser.add_argument("--timeframe", "-t", default="1h", help="Timeframe to compare")
    parser.add_argument(
        "--save-aligned",
        action="store_true",
        help="Save aligned multi-exchange dataset",
    )
    args = parser.parse_args()

    print(f"Cross-exchange comparison for {args.timeframe} data\n")

    merged = load_and_align(args.data_dir, args.timeframe)
    if merged is None:
        sys.exit(1)

    compute_spread_stats(merged)

    if args.save_aligned:
        save_aligned_data(merged, args.data_dir, args.timeframe)


if __name__ == "__main__":
    main()
