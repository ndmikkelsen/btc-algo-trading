#!/usr/bin/env python3
"""Estimate fill probability as a function of distance from mid price.

Downloads recent 1m candle data and simulates placing limit orders at
various distances from the mid price, checking whether subsequent candles
would have filled them.  Builds an empirical fill probability curve.

Usage:
    python scripts/estimate_fill_probability.py
    python scripts/estimate_fill_probability.py --exchange okx --days 7
    python scripts/estimate_fill_probability.py --use-cached data/okx_btcusdt_1m.csv
"""

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

EXCHANGE_SYMBOLS = {
    "okx": "BTC/USDT",
    "kraken": "BTC/USD",
    "bitfinex": "BTC/USDT",
    "kucoin": "BTC/USDT",
    "bitstamp": "BTC/USD",
}


def download_1m_data(exchange_id: str, days: int = 7) -> pd.DataFrame:
    """Download recent 1m candle data."""
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({"enableRateLimit": True})
    symbol = EXCHANGE_SYMBOLS[exchange_id]

    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    ms_per_candle = 60_000

    all_ohlcv = []
    current_since = since
    expected = days * 24 * 60

    print(f"Downloading {days} days of 1m data from {exchange_id}...")
    print(f"Expected ~{expected:,} candles")

    while current_since < now_ms:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, "1m", since=current_since, limit=1000)
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            current_since = ohlcv[-1][0] + ms_per_candle

            if len(all_ohlcv) % 5000 < 1000:
                pct = len(all_ohlcv) / expected * 100
                print(f"  {len(all_ohlcv):>7,} candles ({pct:.0f}%)")

            time.sleep(exchange.rateLimit / 1000)

        except ccxt.RateLimitExceeded:
            print("  Rate limited, waiting 5s...")
            time.sleep(5)
        except ccxt.NetworkError as e:
            print(f"  Network error, retrying: {e}")
            time.sleep(3)
        except ccxt.ExchangeError as e:
            print(f"  Exchange error: {e}")
            break

    if not all_ohlcv:
        print("No data downloaded!")
        sys.exit(1)

    df = pd.DataFrame(
        all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates(subset=["timestamp"], keep="first")
    df = df.sort_values("timestamp").reset_index(drop=True)

    print(f"Downloaded {len(df):,} candles")
    return df


def estimate_fill_probabilities(
    df: pd.DataFrame,
    distances_bps: list[float] | None = None,
    lookahead_candles: int = 1,
) -> pd.DataFrame:
    """Estimate P(fill) for limit orders at various distances from mid.

    For each candle, we simulate placing a bid/ask at `distance` below/above
    the mid price, then check if the subsequent candle(s) would have filled it.

    Args:
        df: OHLCV DataFrame with columns open, high, low, close.
        distances_bps: List of distances in basis points to test.
        lookahead_candles: How many future candles to check for fills.

    Returns:
        DataFrame with columns: distance_bps, distance_pct, bid_fill_rate,
        ask_fill_rate, both_fill_rate, expected_spread_capture_bps.
    """
    if distances_bps is None:
        distances_bps = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 500]

    results = []

    for dist_bps in distances_bps:
        dist_pct = dist_bps / 10000
        bid_fills = 0
        ask_fills = 0
        both_fills = 0
        total = 0

        for i in range(len(df) - lookahead_candles):
            mid = (df.iloc[i]["high"] + df.iloc[i]["low"]) / 2
            bid_price = mid * (1 - dist_pct)
            ask_price = mid * (1 + dist_pct)

            # Check if future candles would fill
            bid_hit = False
            ask_hit = False
            for j in range(1, lookahead_candles + 1):
                future = df.iloc[i + j]
                if future["low"] <= bid_price:
                    bid_hit = True
                if future["high"] >= ask_price:
                    ask_hit = True

            if bid_hit:
                bid_fills += 1
            if ask_hit:
                ask_fills += 1
            if bid_hit and ask_hit:
                both_fills += 1
            total += 1

        if total == 0:
            continue

        # Expected spread capture: if both fill, we capture 2*distance minus fees
        fee_bps = 20  # 0.1% maker each side
        gross_spread = 2 * dist_bps
        net_spread = gross_spread - fee_bps
        both_rate = both_fills / total

        results.append({
            "distance_bps": dist_bps,
            "distance_pct": dist_pct * 100,
            "bid_fill_rate": bid_fills / total * 100,
            "ask_fill_rate": ask_fills / total * 100,
            "both_fill_rate": both_rate * 100,
            "one_side_only_rate": (bid_fills + ask_fills - 2 * both_fills) / total * 100,
            "no_fill_rate": (total - bid_fills - ask_fills + both_fills) / total * 100,
            "gross_spread_bps": gross_spread,
            "net_spread_bps": net_spread,
            "expected_pnl_per_candle_bps": both_rate * net_spread,
            "sample_size": total,
        })

    return pd.DataFrame(results)


def estimate_with_inventory_risk(
    df: pd.DataFrame,
    distances_bps: list[float] | None = None,
) -> pd.DataFrame:
    """Extended analysis: account for inventory risk from one-sided fills.

    When only the bid fills, we accumulate inventory that may lose value.
    When only the ask fills, we go short and may face losses.
    This estimates the average adverse move after a one-sided fill.
    """
    if distances_bps is None:
        distances_bps = [10, 20, 30, 50, 100, 200]

    results = []
    for dist_bps in distances_bps:
        dist_pct = dist_bps / 10000
        adverse_after_bid = []
        adverse_after_ask = []
        holding_periods = [1, 5, 10, 30, 60]  # candles to hold

        for i in range(len(df) - max(holding_periods) - 1):
            mid = (df.iloc[i]["high"] + df.iloc[i]["low"]) / 2
            bid_price = mid * (1 - dist_pct)
            ask_price = mid * (1 + dist_pct)

            next_candle = df.iloc[i + 1]
            bid_hit = next_candle["low"] <= bid_price
            ask_hit = next_candle["high"] >= ask_price

            if bid_hit and not ask_hit:
                # Bought at bid, now holding long — track adverse move
                for hp in holding_periods:
                    if i + 1 + hp < len(df):
                        future_mid = (df.iloc[i + 1 + hp]["high"] + df.iloc[i + 1 + hp]["low"]) / 2
                        move_pct = (future_mid - bid_price) / bid_price * 100
                        adverse_after_bid.append({"holding": hp, "move_pct": move_pct})

            elif ask_hit and not bid_hit:
                for hp in holding_periods:
                    if i + 1 + hp < len(df):
                        future_mid = (df.iloc[i + 1 + hp]["high"] + df.iloc[i + 1 + hp]["low"]) / 2
                        move_pct = (ask_price - future_mid) / ask_price * 100
                        adverse_after_ask.append({"holding": hp, "move_pct": move_pct})

        if adverse_after_bid:
            bid_df = pd.DataFrame(adverse_after_bid)
            for hp in holding_periods:
                subset = bid_df[bid_df["holding"] == hp]["move_pct"]
                if len(subset) > 0:
                    results.append({
                        "distance_bps": dist_bps,
                        "fill_side": "bid_only",
                        "holding_candles": hp,
                        "mean_move_pct": subset.mean(),
                        "median_move_pct": subset.median(),
                        "p25_move_pct": subset.quantile(0.25),
                        "p75_move_pct": subset.quantile(0.75),
                        "worst_move_pct": subset.min(),
                        "count": len(subset),
                    })

        if adverse_after_ask:
            ask_df = pd.DataFrame(adverse_after_ask)
            for hp in holding_periods:
                subset = ask_df[ask_df["holding"] == hp]["move_pct"]
                if len(subset) > 0:
                    results.append({
                        "distance_bps": dist_bps,
                        "fill_side": "ask_only",
                        "holding_candles": hp,
                        "mean_move_pct": subset.mean(),
                        "median_move_pct": subset.median(),
                        "p25_move_pct": subset.quantile(0.25),
                        "p75_move_pct": subset.quantile(0.75),
                        "worst_move_pct": subset.min(),
                        "count": len(subset),
                    })

    return pd.DataFrame(results) if results else pd.DataFrame()


def print_fill_curve(fill_df: pd.DataFrame):
    """Print a formatted fill probability curve."""
    print(f"\n{'='*80}")
    print(f"  FILL PROBABILITY CURVE")
    print(f"{'='*80}")
    print(
        f"  {'Dist(bps)':>9} {'Dist(%)':>7} {'Bid Fill':>9} {'Ask Fill':>9} "
        f"{'Both':>7} {'None':>7} {'Net Spr':>8} {'E[PnL]/c':>9}"
    )
    print(f"  {'-'*74}")

    for _, row in fill_df.iterrows():
        marker = ""
        if row["expected_pnl_per_candle_bps"] == fill_df["expected_pnl_per_candle_bps"].max():
            marker = " <-- OPTIMAL"
        print(
            f"  {row['distance_bps']:>9.0f} {row['distance_pct']:>6.2f}% "
            f"{row['bid_fill_rate']:>8.1f}% {row['ask_fill_rate']:>8.1f}% "
            f"{row['both_fill_rate']:>6.1f}% {row['no_fill_rate']:>6.1f}% "
            f"{row['net_spread_bps']:>7.0f}bp "
            f"{row['expected_pnl_per_candle_bps']:>8.3f}bp{marker}"
        )

    # Summary
    optimal = fill_df.loc[fill_df["expected_pnl_per_candle_bps"].idxmax()]
    print(f"\n  Optimal distance: {optimal['distance_bps']:.0f} bps ({optimal['distance_pct']:.2f}%)")
    print(f"  At optimal: {optimal['both_fill_rate']:.1f}% both-fill rate, "
          f"{optimal['net_spread_bps']:.0f}bp net spread")
    print(f"  Expected P&L per candle: {optimal['expected_pnl_per_candle_bps']:.3f} bps")


def print_inventory_risk(inv_df: pd.DataFrame):
    """Print inventory risk analysis."""
    if inv_df.empty:
        return

    print(f"\n{'='*80}")
    print(f"  INVENTORY RISK AFTER ONE-SIDED FILLS")
    print(f"{'='*80}")

    for dist in inv_df["distance_bps"].unique():
        subset = inv_df[inv_df["distance_bps"] == dist]
        print(f"\n  Distance: {dist} bps")
        for side in ["bid_only", "ask_only"]:
            side_data = subset[subset["fill_side"] == side]
            if side_data.empty:
                continue
            label = "Long (bid fill)" if side == "bid_only" else "Short (ask fill)"
            print(f"    {label}:")
            for _, row in side_data.iterrows():
                hp = int(row["holding_candles"])
                print(
                    f"      After {hp:>2} candles: "
                    f"mean {row['mean_move_pct']:+.3f}% "
                    f"median {row['median_move_pct']:+.3f}% "
                    f"worst {row['worst_move_pct']:+.3f}% "
                    f"(n={int(row['count'])})"
                )


def main():
    parser = argparse.ArgumentParser(description="Estimate fill probability curve")
    parser.add_argument("--exchange", default="okx", choices=list(EXCHANGE_SYMBOLS))
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument(
        "--use-cached", type=str, default=None,
        help="Use cached CSV instead of downloading",
    )
    parser.add_argument(
        "--lookahead", type=int, default=1,
        help="Number of candles to look ahead for fills",
    )
    parser.add_argument(
        "--inventory-risk", action="store_true",
        help="Also estimate inventory risk from one-sided fills",
    )
    parser.add_argument("--output", default="data")
    args = parser.parse_args()

    # Load or download data
    if args.use_cached:
        cached_path = Path(args.use_cached)
        if not cached_path.exists():
            print(f"Cached file not found: {cached_path}")
            sys.exit(1)
        print(f"Using cached data: {cached_path}")
        df = pd.read_csv(cached_path, parse_dates=["timestamp"])
    else:
        df = download_1m_data(args.exchange, args.days)
        # Save the downloaded data
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        symbol = EXCHANGE_SYMBOLS[args.exchange].replace("/", "").lower()
        cache_path = output_dir / f"{args.exchange}_{symbol}_1m.csv"
        df.to_csv(cache_path, index=False)
        print(f"Saved to {cache_path}")

    print(f"\nData: {len(df):,} candles, "
          f"{df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")

    # Estimate fill probabilities
    print("\nEstimating fill probabilities...")
    fill_df = estimate_fill_probabilities(df, lookahead_candles=args.lookahead)

    print_fill_curve(fill_df)

    # Save curve
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    curve_path = output_dir / "fill_probability_curve.csv"
    fill_df.to_csv(curve_path, index=False)
    print(f"\n  Fill curve saved to: {curve_path}")

    # Inventory risk analysis
    if args.inventory_risk:
        print("\nEstimating inventory risk...")
        inv_df = estimate_with_inventory_risk(df)
        print_inventory_risk(inv_df)
        inv_path = output_dir / "inventory_risk_after_fill.csv"
        inv_df.to_csv(inv_path, index=False)
        print(f"\n  Inventory risk data saved to: {inv_path}")

    # Summary for calibration
    print(f"\n{'='*80}")
    print(f"  CALIBRATION SUMMARY")
    print(f"{'='*80}")
    for _, row in fill_df.iterrows():
        d = row["distance_bps"]
        b = row["both_fill_rate"]
        print(f"  At {d:>5.0f}bps ({row['distance_pct']:.2f}%) from mid: "
              f"fills {b:.1f}% of the time (both sides)")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
