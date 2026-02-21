#!/usr/bin/env python3
"""Regime analysis: break down MRBB returns by market condition per quarter.

Segments the 3-year backtest (Jan 2023 – Feb 2026) into quarterly windows,
runs backtests on each, and classifies the BTC regime for that period.

Regime classification:
    - trending_up:   trend > +10%
    - trending_down:  trend < -10%
    - volatile_chop: high vol (> median) + abs(trend) < 10%
    - ranging:       abs(trend) < 10% + vol < median

Usage:
    python3 scripts/regime_analysis.py
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.simulator import DirectionalSimulator
from strategies.mean_reversion_bb.presets import PresetManager
from strategies.avellaneda_stoikov.metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
)

PERIODS_PER_YEAR_5M = 105_120
DATA_PATH = Path("data/btcusdt_5m.csv")
OUTPUT_DIR = Path("backtests/mrbb/regime_analysis")

# Model param keys (same set as sweep_stop_decay.py)
MODEL_KEYS = {
    "bb_period", "bb_std_dev", "bb_inner_std_dev", "vwap_period",
    "vwap_confirmation_pct", "kc_period", "kc_atr_multiplier",
    "rsi_period", "rsi_oversold", "rsi_overbought",
    "adx_period", "adx_threshold", "use_regime_filter",
    "reversion_target", "max_holding_bars",
    "risk_per_trade", "max_position_pct", "stop_atr_multiplier",
    "stop_decay_phase_1", "stop_decay_phase_2",
    "stop_decay_mult_1", "stop_decay_mult_2",
    "side_filter", "use_squeeze_filter", "use_band_walking_exit",
    "short_bb_std_dev", "short_rsi_threshold",
    "short_max_holding_bars", "short_position_pct",
    "use_trend_filter", "trend_ema_period",
}


def load_data(path: Path) -> pd.DataFrame:
    """Load OHLCV CSV and parse timestamps."""
    df = pd.read_csv(path)
    ts = df["timestamp"]
    if pd.api.types.is_numeric_dtype(ts):
        df["timestamp"] = pd.to_datetime(ts, unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(ts)
    df = df.set_index("timestamp")
    return df


def get_quarterly_slices(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """Split dataframe into quarterly windows, returning (label, df) pairs."""
    quarters = []
    start = df.index.min()
    end = df.index.max()

    # Generate quarter boundaries
    year = start.year
    quarter = (start.month - 1) // 3 + 1

    while True:
        q_start_month = (quarter - 1) * 3 + 1
        q_start = pd.Timestamp(year=year, month=q_start_month, day=1, tz=start.tz)
        # Next quarter start
        if quarter == 4:
            q_end = pd.Timestamp(year=year + 1, month=1, day=1, tz=start.tz)
        else:
            q_end = pd.Timestamp(year=year, month=q_start_month + 3, day=1, tz=start.tz)

        if q_start > end:
            break

        slice_df = df[(df.index >= q_start) & (df.index < q_end)]
        if len(slice_df) > 100:  # Need enough data for indicators
            label = f"Q{quarter} {year}"
            quarters.append((label, slice_df))

        # Advance
        quarter += 1
        if quarter > 4:
            quarter = 1
            year += 1

    return quarters


def classify_regime(trend_pct: float, real_vol: float, median_vol: float) -> str:
    """Classify market regime based on trend and volatility."""
    if trend_pct > 10.0:
        return "trending_up"
    elif trend_pct < -10.0:
        return "trending_down"
    elif real_vol > median_vol and abs(trend_pct) < 10.0:
        return "volatile_chop"
    else:
        return "ranging"


def compute_btc_stats(df: pd.DataFrame) -> dict:
    """Compute BTC regime indicators for a data slice."""
    closes = df["close"].values
    returns = np.diff(np.log(closes))

    # Annualized realized volatility
    real_vol = np.std(returns) * np.sqrt(PERIODS_PER_YEAR_5M) * 100

    # Trend: price change % over the period
    trend_pct = (closes[-1] / closes[0] - 1) * 100

    return {
        "start_price": float(closes[0]),
        "end_price": float(closes[-1]),
        "trend_pct": round(trend_pct, 2),
        "real_vol_pct": round(real_vol, 2),
    }


def run_quarter(df: pd.DataFrame, model_params: dict) -> dict:
    """Run a backtest on a single quarter slice."""
    model = MeanReversionBB(**model_params)
    sim = DirectionalSimulator(
        model=model,
        initial_equity=10_000.0,
        slippage_pct=0.0005,
        random_seed=42,
    )

    t0 = time.time()
    results = sim.run_backtest_fast(df)
    elapsed = time.time() - t0

    ec = results["equity_curve"]
    sr = sharpe_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    so = sortino_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    dd = max_drawdown(ec)

    trades = results["trade_log"]
    wins = [t for t in trades if t["pnl"] > 0]
    avg_pnl = sum(t["pnl"] for t in trades) / len(trades) if trades else 0.0

    return {
        "total_return_pct": results["total_return_pct"],
        "sharpe": sr,
        "sortino": so,
        "max_dd_pct": dd["max_drawdown_pct"],
        "total_trades": results["total_trades"],
        "win_rate": len(wins) / len(trades) * 100 if trades else 0.0,
        "avg_pnl": avg_pnl,
        "final_equity": results["final_equity"],
        "elapsed_sec": round(elapsed, 1),
    }


def fmt(v, width=7, decimals=2):
    """Format float with inf handling."""
    if isinstance(v, float) and (v == float("inf") or v == float("-inf")):
        return f"{'inf' if v > 0 else '-inf':>{width}}"
    return f"{v:>{width}.{decimals}f}"


def main():
    print("=" * 120)
    print("MRBB Regime Analysis — Quarterly Performance Breakdown")
    print("=" * 120)

    # Load data
    df = load_data(DATA_PATH)
    print(f"Data: {len(df)} candles, {df.index[0]} to {df.index[-1]}")

    # Load optimized preset and extract model params
    pm = PresetManager()
    preset = pm.load("optimized")
    model_params = {k: v for k, v in preset.items() if k in MODEL_KEYS}
    print(f"Preset: optimized (side_filter={model_params.get('side_filter', 'both')})")
    print()

    # Get quarterly slices
    quarters = get_quarterly_slices(df)
    print(f"Quarters found: {len(quarters)}")
    print()

    # First pass: compute BTC stats to get median vol for regime classification
    btc_stats = []
    for label, qdf in quarters:
        stats = compute_btc_stats(qdf)
        btc_stats.append(stats)

    median_vol = np.median([s["real_vol_pct"] for s in btc_stats])
    print(f"Median quarterly realized vol: {median_vol:.1f}%")
    print()

    # Second pass: run backtests and classify regimes
    all_results = []
    for i, (label, qdf) in enumerate(quarters):
        stats = btc_stats[i]
        regime = classify_regime(stats["trend_pct"], stats["real_vol_pct"], median_vol)

        print(f"[{i+1}/{len(quarters)}] {label}: BTC {stats['trend_pct']:+.1f}%, "
              f"vol {stats['real_vol_pct']:.1f}%, regime={regime}, "
              f"{len(qdf)} candles")

        bt = run_quarter(qdf, model_params)

        result = {
            "quarter": label,
            "btc_change_pct": stats["trend_pct"],
            "real_vol_pct": stats["real_vol_pct"],
            "regime": regime,
            "return_pct": bt["total_return_pct"],
            "sharpe": bt["sharpe"],
            "sortino": bt["sortino"],
            "trades": bt["total_trades"],
            "win_rate": bt["win_rate"],
            "avg_pnl": bt["avg_pnl"],
            "max_dd_pct": bt["max_dd_pct"],
            "final_equity": bt["final_equity"],
            "start_price": stats["start_price"],
            "end_price": stats["end_price"],
        }
        all_results.append(result)

        print(f"         Return: {bt['total_return_pct']:+.2f}%, "
              f"Sharpe: {fmt(bt['sharpe']).strip()}, "
              f"Trades: {bt['total_trades']}, "
              f"WinRate: {bt['win_rate']:.1f}%, "
              f"MaxDD: {bt['max_dd_pct']:.2f}% "
              f"[{bt['elapsed_sec']}s]")

    # Print summary table
    print()
    print("=" * 120)
    print("PER-QUARTER RESULTS")
    print("=" * 120)
    header = (
        f"{'Quarter':<10} {'BTC_Chg%':>9} {'RealVol%':>9} {'Regime':<15} "
        f"{'Return%':>8} {'Sharpe':>7} {'Trades':>6} {'WinRate%':>8} "
        f"{'AvgPnL':>8} {'MaxDD%':>7}"
    )
    print(header)
    print("-" * 120)

    for r in all_results:
        print(
            f"{r['quarter']:<10} "
            f"{r['btc_change_pct']:+8.1f}% "
            f"{r['real_vol_pct']:8.1f}% "
            f"{r['regime']:<15} "
            f"{r['return_pct']:+7.2f}% "
            f"{fmt(r['sharpe'])} "
            f"{r['trades']:>6} "
            f"{r['win_rate']:7.1f}% "
            f"${r['avg_pnl']:+7.2f} "
            f"{r['max_dd_pct']:6.2f}%"
        )

    # Regime summary
    print()
    print("=" * 120)
    print("REGIME SUMMARY")
    print("=" * 120)

    regimes = {}
    for r in all_results:
        regime = r["regime"]
        if regime not in regimes:
            regimes[regime] = []
        regimes[regime].append(r)

    for regime, entries in sorted(regimes.items()):
        returns = [e["return_pct"] for e in entries]
        sharpes = [e["sharpe"] for e in entries]
        # Filter out inf sharpes for averaging
        finite_sharpes = [s for s in sharpes if abs(s) < 1e6]
        trades = [e["trades"] for e in entries]
        win_rates = [e["win_rate"] for e in entries]

        avg_ret = np.mean(returns)
        total_ret = np.sum(returns)
        avg_sharpe = np.mean(finite_sharpes) if finite_sharpes else float("nan")
        avg_trades = np.mean(trades)
        avg_wr = np.mean(win_rates)
        n_quarters = len(entries)
        n_profitable = sum(1 for r in returns if r > 0)

        print(f"\n  {regime.upper()} ({n_quarters} quarters, {n_profitable}/{n_quarters} profitable)")
        print(f"    Avg Return:  {avg_ret:+.2f}%  |  Total Return:  {total_ret:+.2f}%")
        print(f"    Avg Sharpe:  {avg_sharpe:.2f}  |  Avg Trades:  {avg_trades:.0f}")
        print(f"    Avg WinRate: {avg_wr:.1f}%")
        print(f"    Quarters: {', '.join(e['quarter'] for e in entries)}")

    # Profitability clustering
    print()
    print("=" * 120)
    print("PROFITABILITY CLUSTERING")
    print("=" * 120)

    profitable = [r for r in all_results if r["return_pct"] > 0]
    unprofitable = [r for r in all_results if r["return_pct"] <= 0]

    print(f"\n  Profitable quarters ({len(profitable)}/{len(all_results)}):")
    for r in sorted(profitable, key=lambda x: x["return_pct"], reverse=True):
        print(f"    {r['quarter']:<10} {r['return_pct']:+7.2f}%  regime={r['regime']:<15} "
              f"BTC={r['btc_change_pct']:+.1f}%")

    print(f"\n  Unprofitable quarters ({len(unprofitable)}/{len(all_results)}):")
    for r in sorted(unprofitable, key=lambda x: x["return_pct"]):
        print(f"    {r['quarter']:<10} {r['return_pct']:+7.2f}%  regime={r['regime']:<15} "
              f"BTC={r['btc_change_pct']:+.1f}%")

    # Check if returns cluster in specific periods
    print(f"\n  Top 3 best quarters:")
    for r in sorted(all_results, key=lambda x: x["return_pct"], reverse=True)[:3]:
        print(f"    {r['quarter']}: {r['return_pct']:+.2f}% (BTC {r['btc_change_pct']:+.1f}%, {r['regime']})")

    print(f"\n  Top 3 worst quarters:")
    for r in sorted(all_results, key=lambda x: x["return_pct"])[:3]:
        print(f"    {r['quarter']}: {r['return_pct']:+.2f}% (BTC {r['btc_change_pct']:+.1f}%, {r['regime']})")

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _ser(v):
        if isinstance(v, float) and (v == float("inf") or v == float("-inf")):
            return str(v)
        raise TypeError

    with open(OUTPUT_DIR / "quarterly_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=_ser)

    pd.DataFrame(all_results).to_csv(OUTPUT_DIR / "quarterly_results.csv", index=False)

    print(f"\nResults saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
