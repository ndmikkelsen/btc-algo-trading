#!/usr/bin/env python3
"""Validate and assess quality of downloaded BTC OHLCV data.

Checks for gaps, outliers, cross-exchange consistency, and generates
a data quality report.

Usage:
    python scripts/validate_data.py [--data-dir data] [--timeframe 1h]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TIMEFRAME_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


def load_exchange_data(data_dir: str, timeframe: str) -> dict[str, pd.DataFrame]:
    """Load all exchange CSV files matching the timeframe."""
    data_path = Path(data_dir)
    datasets = {}

    for filepath in sorted(data_path.glob(f"*_{timeframe}.csv")):
        exchange = filepath.stem.split("_")[0]
        try:
            df = pd.read_csv(filepath, parse_dates=["timestamp"])
            df = df.sort_values("timestamp").reset_index(drop=True)
            datasets[exchange] = df
            print(f"  Loaded {exchange}: {len(df):,} candles")
        except Exception as e:
            print(f"  Failed to load {filepath.name}: {e}")

    return datasets


def check_gaps(df: pd.DataFrame, timeframe: str, exchange: str) -> dict:
    """Check for missing candles (gaps) in the data."""
    interval_s = TIMEFRAME_SECONDS.get(timeframe, 3600)
    expected_delta = pd.Timedelta(seconds=interval_s)

    deltas = df["timestamp"].diff().dropna()
    gaps = deltas[deltas > expected_delta * 1.5]  # Allow 50% tolerance

    gap_details = []
    for idx in gaps.index:
        gap_start = df["timestamp"].iloc[idx - 1]
        gap_end = df["timestamp"].iloc[idx]
        gap_duration = gap_end - gap_start
        missing_candles = int(gap_duration / expected_delta) - 1
        gap_details.append({
            "start": gap_start,
            "end": gap_end,
            "duration": gap_duration,
            "missing_candles": missing_candles,
        })

    total_expected = int(
        (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).total_seconds()
        / interval_s
    ) + 1
    total_missing = sum(g["missing_candles"] for g in gap_details)
    completeness = (len(df) / total_expected * 100) if total_expected > 0 else 0

    return {
        "exchange": exchange,
        "total_candles": len(df),
        "expected_candles": total_expected,
        "gap_count": len(gap_details),
        "total_missing": total_missing,
        "completeness_pct": completeness,
        "largest_gap": max(gap_details, key=lambda g: g["missing_candles"]) if gap_details else None,
        "gaps": gap_details,
    }


def check_outliers(df: pd.DataFrame, exchange: str, window: int = 20) -> dict:
    """Detect price outliers using rolling z-score on close prices."""
    close = df["close"]
    rolling_mean = close.rolling(window, min_periods=5).mean()
    rolling_std = close.rolling(window, min_periods=5).std()

    z_scores = ((close - rolling_mean) / rolling_std).abs()
    outlier_mask = z_scores > 4  # 4 sigma
    outliers = df[outlier_mask].copy()

    # Also check for impossible OHLC relationships
    bad_ohlc = df[
        (df["high"] < df["low"])
        | (df["open"] < df["low"])
        | (df["open"] > df["high"])
        | (df["close"] < df["low"])
        | (df["close"] > df["high"])
    ]

    # Check for zero/negative volumes
    zero_vol = df[df["volume"] <= 0]

    return {
        "exchange": exchange,
        "z_score_outliers": len(outliers),
        "outlier_timestamps": outliers["timestamp"].tolist()[:10],
        "bad_ohlc_count": len(bad_ohlc),
        "zero_volume_count": len(zero_vol),
        "max_z_score": float(z_scores.max()) if len(z_scores) > 0 else 0,
    }


def cross_exchange_check(
    datasets: dict[str, pd.DataFrame],
) -> dict:
    """Compare prices across exchanges at aligned timestamps."""
    if len(datasets) < 2:
        return {"error": "Need at least 2 exchanges for cross-validation"}

    # Merge all on timestamp (inner join for common timestamps)
    merged = None
    for exchange, df in datasets.items():
        close_df = df[["timestamp", "close"]].copy()
        close_df = close_df.rename(columns={"close": f"close_{exchange}"})
        # Round timestamps to nearest minute for alignment
        close_df["timestamp"] = close_df["timestamp"].dt.floor("min")
        close_df = close_df.drop_duplicates(subset=["timestamp"], keep="first")

        if merged is None:
            merged = close_df
        else:
            merged = merged.merge(close_df, on="timestamp", how="inner")

    if merged is None or len(merged) == 0:
        return {"error": "No overlapping timestamps found"}

    close_cols = [c for c in merged.columns if c.startswith("close_")]
    exchanges = [c.replace("close_", "") for c in close_cols]

    # Pairwise deviation analysis
    pairwise = {}
    for i, ex1 in enumerate(exchanges):
        for ex2 in exchanges[i + 1:]:
            col1 = f"close_{ex1}"
            col2 = f"close_{ex2}"
            pct_diff = ((merged[col1] - merged[col2]) / merged[col1] * 100).abs()
            pairwise[f"{ex1}_vs_{ex2}"] = {
                "mean_deviation_pct": float(pct_diff.mean()),
                "max_deviation_pct": float(pct_diff.max()),
                "std_deviation_pct": float(pct_diff.std()),
                "median_deviation_pct": float(pct_diff.median()),
                "above_0_5_pct": int((pct_diff > 0.5).sum()),
                "above_1_pct": int((pct_diff > 1.0).sum()),
            }

    # Consensus: flag points where any exchange deviates >1% from median
    median_close = merged[close_cols].median(axis=1)
    suspect_points = []
    for col in close_cols:
        exchange = col.replace("close_", "")
        deviation = ((merged[col] - median_close) / median_close * 100).abs()
        suspect_mask = deviation > 1.0
        for idx in merged[suspect_mask].index:
            suspect_points.append({
                "timestamp": str(merged.loc[idx, "timestamp"]),
                "exchange": exchange,
                "price": float(merged.loc[idx, col]),
                "median_price": float(median_close.iloc[idx]),
                "deviation_pct": float(deviation.iloc[idx]),
            })

    return {
        "overlapping_candles": len(merged),
        "exchanges_compared": exchanges,
        "pairwise_deviations": pairwise,
        "suspect_points_count": len(suspect_points),
        "suspect_points_sample": suspect_points[:20],
    }


def generate_report(
    datasets: dict[str, pd.DataFrame],
    gap_results: list[dict],
    outlier_results: list[dict],
    cross_results: dict,
    timeframe: str,
    output_dir: str,
) -> str:
    """Generate a human-readable data quality report."""
    lines = []
    lines.append("=" * 70)
    lines.append("  BTC DATA QUALITY REPORT")
    lines.append(f"  Timeframe: {timeframe}")
    lines.append(f"  Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 70)

    # Per-exchange summary
    lines.append("\n1. DATA COMPLETENESS")
    lines.append("-" * 40)
    for gap in gap_results:
        ex = gap["exchange"]
        lines.append(f"\n  {ex.upper()}")
        lines.append(f"    Candles:      {gap['total_candles']:>8,} / {gap['expected_candles']:>8,}")
        lines.append(f"    Completeness: {gap['completeness_pct']:>8.2f}%")
        lines.append(f"    Gaps:         {gap['gap_count']:>8}")
        lines.append(f"    Missing:      {gap['total_missing']:>8} candles")
        if gap["largest_gap"]:
            lg = gap["largest_gap"]
            lines.append(f"    Largest gap:  {lg['missing_candles']} candles ({lg['start']} to {lg['end']})")

    # Outlier summary
    lines.append("\n\n2. OUTLIER DETECTION")
    lines.append("-" * 40)
    for outlier in outlier_results:
        ex = outlier["exchange"]
        lines.append(f"\n  {ex.upper()}")
        lines.append(f"    Z-score outliers (>4σ): {outlier['z_score_outliers']}")
        lines.append(f"    Bad OHLC records:       {outlier['bad_ohlc_count']}")
        lines.append(f"    Zero volume candles:    {outlier['zero_volume_count']}")
        lines.append(f"    Max z-score:            {outlier['max_z_score']:.2f}")

    # Cross-exchange
    lines.append("\n\n3. CROSS-EXCHANGE COMPARISON")
    lines.append("-" * 40)
    if "error" in cross_results:
        lines.append(f"  {cross_results['error']}")
    else:
        lines.append(f"  Overlapping candles: {cross_results['overlapping_candles']:,}")
        lines.append(f"  Exchanges compared:  {', '.join(cross_results['exchanges_compared'])}")
        lines.append(f"\n  Pairwise price deviations:")
        for pair, stats in cross_results["pairwise_deviations"].items():
            lines.append(f"\n    {pair}:")
            lines.append(f"      Mean:   {stats['mean_deviation_pct']:.4f}%")
            lines.append(f"      Median: {stats['median_deviation_pct']:.4f}%")
            lines.append(f"      Max:    {stats['max_deviation_pct']:.4f}%")
            lines.append(f"      Std:    {stats['std_deviation_pct']:.4f}%")
            lines.append(f"      >0.5%:  {stats['above_0_5_pct']} candles")
            lines.append(f"      >1.0%:  {stats['above_1_pct']} candles")

        lines.append(f"\n  Suspect data points (>1% from median): {cross_results['suspect_points_count']}")

    # Quality grades
    lines.append("\n\n4. QUALITY GRADES")
    lines.append("-" * 40)
    for gap in gap_results:
        ex = gap["exchange"]
        outlier = next((o for o in outlier_results if o["exchange"] == ex), None)
        completeness = gap["completeness_pct"]
        outlier_count = outlier["z_score_outliers"] if outlier else 0
        bad_ohlc = outlier["bad_ohlc_count"] if outlier else 0

        if completeness >= 99.5 and outlier_count <= 5 and bad_ohlc == 0:
            grade = "A"
        elif completeness >= 98 and outlier_count <= 20:
            grade = "B"
        elif completeness >= 95:
            grade = "C"
        else:
            grade = "D"

        lines.append(f"  {ex.upper():>10}: Grade {grade}  (completeness={completeness:.1f}%, outliers={outlier_count}, bad_ohlc={bad_ohlc})")

    lines.append("\n" + "=" * 70)

    report = "\n".join(lines)

    # Save report
    report_path = Path(output_dir) / f"data_quality_report_{timeframe}.txt"
    report_path.write_text(report)
    print(f"\nReport saved to {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Validate BTC OHLCV data quality")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    parser.add_argument("--timeframe", "-t", default="1h", help="Timeframe to validate")
    args = parser.parse_args()

    print(f"Validating {args.timeframe} data in {args.data_dir}/\n")

    # Load data
    datasets = load_exchange_data(args.data_dir, args.timeframe)
    if not datasets:
        print("No data files found!")
        sys.exit(1)

    # Run checks
    gap_results = []
    outlier_results = []
    for exchange, df in datasets.items():
        gap_results.append(check_gaps(df, args.timeframe, exchange))
        outlier_results.append(check_outliers(df, exchange))

    # Cross-exchange comparison
    cross_results = cross_exchange_check(datasets)

    # Generate report
    report = generate_report(
        datasets, gap_results, outlier_results, cross_results,
        args.timeframe, args.data_dir,
    )
    print(report)


if __name__ == "__main__":
    main()
