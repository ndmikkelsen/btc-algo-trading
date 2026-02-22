#!/usr/bin/env python3
"""Identify market regime periods in historical BTC data.

Classifies each candle into a market regime:
  - ranging: Low ADX (<25), ideal for mean reversion
  - trending_up: High ADX (>=25) with +DI > -DI
  - trending_down: High ADX (>=25) with -DI > +DI
  - high_volatility: Bandwidth > 90th percentile (volatile, unclear direction)

Usage:
    python scripts/identify_regimes.py --data data/btcusdt_5m.csv
    python scripts/identify_regimes.py --data data/btcusdt_1h.csv --adx-threshold 20
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate ADX, +DI, and -DI.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: Smoothing period (default 14)

    Returns:
        Tuple of (ADX, plus_DI, minus_DI) series
    """
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    # True Range
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Directional Movement
    plus_dm = high - prev_high
    minus_dm = prev_low - low

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    # Smooth with Wilder's method (EMA with alpha=1/period)
    alpha = 1 / period
    atr = tr.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    smooth_plus = plus_dm.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    smooth_minus = minus_dm.ewm(alpha=alpha, min_periods=period, adjust=False).mean()

    plus_di = 100 * smooth_plus / atr
    minus_di = 100 * smooth_minus / atr

    # ADX = smoothed DX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(alpha=alpha, min_periods=period, adjust=False).mean()

    return adx, plus_di, minus_di


def calculate_bollinger_bandwidth(
    close: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> pd.Series:
    """Calculate Bollinger Band Width as percentage.

    BW = (upper - lower) / middle * 100
    """
    middle = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return (upper - lower) / middle * 100


def classify_regimes(
    df: pd.DataFrame,
    adx_threshold: float = 25.0,
    adx_period: int = 14,
    bb_period: int = 20,
    vol_percentile: float = 90.0,
) -> pd.DataFrame:
    """Classify each candle into a market regime.

    Args:
        df: OHLCV DataFrame with columns: open, high, low, close, volume
        adx_threshold: ADX above this = trending (default 25)
        adx_period: ADX calculation period
        bb_period: Bollinger Band period for bandwidth calc
        vol_percentile: Bandwidth percentile for high-vol regime

    Returns:
        DataFrame with added columns: adx, plus_di, minus_di, bandwidth, regime
    """
    result = df.copy()

    adx, plus_di, minus_di = calculate_adx(
        result["high"], result["low"], result["close"], period=adx_period
    )
    result["adx"] = adx
    result["plus_di"] = plus_di
    result["minus_di"] = minus_di

    bw = calculate_bollinger_bandwidth(result["close"], period=bb_period)
    result["bandwidth"] = bw

    # Bandwidth percentile rank (rolling 100-period)
    bw_pctile = bw.rolling(100, min_periods=20).apply(
        lambda x: (x < x.iloc[-1]).sum() / len(x) * 100, raw=False
    )
    result["bandwidth_percentile"] = bw_pctile

    # Classify
    conditions = [
        (adx >= adx_threshold) & (bw_pctile >= vol_percentile),          # high_volatility (checked first)
        (adx >= adx_threshold) & (plus_di > minus_di),                     # trending_up
        (adx >= adx_threshold) & (minus_di >= plus_di),                    # trending_down
    ]
    choices = ["high_volatility", "trending_up", "trending_down"]
    result["regime"] = np.select(conditions, choices, default="ranging")

    return result


def summarize_regimes(df: pd.DataFrame, timeframe: str = "5m") -> dict:
    """Summarize regime distribution and statistics.

    Args:
        df: DataFrame with 'regime' column from classify_regimes
        timeframe: Data timeframe for duration calculation

    Returns:
        Summary statistics dictionary
    """
    # Minutes per candle
    tf_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
    min_per_candle = tf_minutes.get(timeframe, 5)

    total = len(df)
    regimes = df["regime"].value_counts()
    regime_pcts = df["regime"].value_counts(normalize=True) * 100

    summary = {"total_candles": total, "timeframe": timeframe, "regimes": {}}

    for regime in ["ranging", "trending_up", "trending_down", "high_volatility"]:
        count = int(regimes.get(regime, 0))
        pct = float(regime_pcts.get(regime, 0.0))
        hours = count * min_per_candle / 60
        days = hours / 24

        # Price stats during this regime
        mask = df["regime"] == regime
        if mask.any():
            regime_data = df[mask]
            returns = regime_data["close"].pct_change().dropna()
            avg_return = float(returns.mean()) * 100
            vol = float(returns.std()) * 100
            avg_adx = float(regime_data["adx"].mean())
        else:
            avg_return = 0.0
            vol = 0.0
            avg_adx = 0.0

        summary["regimes"][regime] = {
            "count": count,
            "pct": round(pct, 1),
            "hours": round(hours, 1),
            "days": round(days, 1),
            "avg_return_pct": round(avg_return, 4),
            "volatility_pct": round(vol, 4),
            "avg_adx": round(avg_adx, 1),
        }

    # Identify regime transition periods
    transitions = (df["regime"] != df["regime"].shift(1)).sum()
    avg_regime_duration = total / max(transitions, 1)
    summary["transitions"] = int(transitions)
    summary["avg_regime_duration_candles"] = round(avg_regime_duration, 1)
    summary["avg_regime_duration_hours"] = round(
        avg_regime_duration * min_per_candle / 60, 1
    )

    return summary


def print_summary(summary: dict) -> None:
    """Print regime summary in a readable format."""
    print("\nMarket Regime Analysis")
    print("=" * 60)
    print(f"Total candles: {summary['total_candles']:,} ({summary['timeframe']})")
    print(f"Regime transitions: {summary['transitions']:,}")
    print(f"Avg regime duration: {summary['avg_regime_duration_candles']:.0f} candles "
          f"({summary['avg_regime_duration_hours']:.1f} hours)")
    print()

    print(f"{'Regime':<20} {'Count':>8} {'%':>7} {'Days':>7} {'Avg ADX':>8} {'Avg Ret':>10} {'Vol':>8}")
    print("-" * 70)

    for regime in ["ranging", "trending_up", "trending_down", "high_volatility"]:
        r = summary["regimes"].get(regime, {})
        tag = "*" if regime == "ranging" else " "
        print(
            f"{regime:<20} {r.get('count', 0):>8,} {r.get('pct', 0):>6.1f}% "
            f"{r.get('days', 0):>6.1f}d {r.get('avg_adx', 0):>7.1f} "
            f"{r.get('avg_return_pct', 0):>9.4f}% {r.get('volatility_pct', 0):>7.4f}%{tag}"
        )

    print()
    ranging_pct = summary["regimes"].get("ranging", {}).get("pct", 0)
    print(f"Mean reversion favorable (ranging): {ranging_pct:.1f}% of data")
    if ranging_pct >= 40:
        print("  -> Good: sufficient ranging periods for MR strategy")
    else:
        print("  -> Warning: limited ranging periods — regime filter is critical")


def save_regime_data(df: pd.DataFrame, output_path: Path) -> None:
    """Save regime-labeled data to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=True)
    print(f"\nSaved regime-labeled data: {output_path} ({len(df):,} rows)")


def main():
    parser = argparse.ArgumentParser(
        description="Identify market regime periods in historical BTC data"
    )
    parser.add_argument("--data", required=True, help="Path to OHLCV CSV file")
    parser.add_argument("--adx-threshold", type=float, default=25.0,
                        help="ADX threshold for trending (default: 25)")
    parser.add_argument("--adx-period", type=int, default=14,
                        help="ADX period (default: 14)")
    parser.add_argument("--bb-period", type=int, default=20,
                        help="BB period for bandwidth (default: 20)")
    parser.add_argument("--vol-percentile", type=float, default=90.0,
                        help="Bandwidth percentile for high-vol regime (default: 90)")
    parser.add_argument("--timeframe", "-t", default="5m",
                        help="Data timeframe (default: 5m)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output CSV path (default: data/<name>_regimes.csv)")
    parser.add_argument("--quiet", "-q", action="store_true")

    args = parser.parse_args()

    # Load data
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Error: file not found: {data_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(data_path)
    required = {"open", "high", "low", "close", "volume", "timestamp"}
    missing = required - set(df.columns)
    if missing:
        print(f"Error: missing columns: {missing}", file=sys.stderr)
        sys.exit(1)

    # Convert timestamp
    ts = df["timestamp"]
    if pd.api.types.is_numeric_dtype(ts):
        df["timestamp"] = pd.to_datetime(ts, unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(ts)
    df = df.set_index("timestamp")

    if not args.quiet:
        print(f"Loaded {len(df):,} candles from {df.index[0]} to {df.index[-1]}")

    # Classify regimes
    labeled = classify_regimes(
        df,
        adx_threshold=args.adx_threshold,
        adx_period=args.adx_period,
        bb_period=args.bb_period,
        vol_percentile=args.vol_percentile,
    )

    # Summary
    summary = summarize_regimes(labeled, timeframe=args.timeframe)
    if not args.quiet:
        print_summary(summary)

    # Save
    if args.output:
        output_path = Path(args.output)
    else:
        stem = data_path.stem
        output_path = Path("data") / f"{stem}_regimes.csv"
    save_regime_data(labeled, output_path)


if __name__ == "__main__":
    main()
