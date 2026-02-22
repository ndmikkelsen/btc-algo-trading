#!/usr/bin/env python3
"""Backtest sweep for asymmetric bidirectional MRBB strategy.

Runs systematic backtests comparing:
1. Baseline: long-only optimized preset (current production)
2. Bidirectional: longs + asymmetric shorts (trend-filtered)
3. Parameter sweep: vary short thresholds (RSI, BB SD, max hold)

Usage:
    python3 scripts/sweep_bidirectional.py
    python3 scripts/sweep_bidirectional.py --days 90
"""

import argparse
import json
import os
import sys
import time
from itertools import product
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
OUTPUT_DIR = Path("backtests/mrbb/bidirectional_sweep")


def load_data(path: Path, days: int = None) -> pd.DataFrame:
    df = pd.read_csv(path)
    ts = df["timestamp"]
    if pd.api.types.is_numeric_dtype(ts):
        df["timestamp"] = pd.to_datetime(ts, unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(ts)
    df = df.set_index("timestamp")
    if days:
        candles_per_day = 24 * 12
        df = df.tail(days * candles_per_day)
    return df


def run_single(df: pd.DataFrame, params: dict, label: str) -> dict:
    """Run one backtest with given params and return stats."""
    # Separate model kwargs from metadata
    model_keys = {
        "bb_period", "bb_std_dev", "bb_inner_std_dev", "vwap_period",
        "vwap_confirmation_pct", "kc_period", "kc_atr_multiplier",
        "rsi_period", "rsi_oversold", "rsi_overbought",
        "adx_period", "adx_threshold", "use_regime_filter",
        "reversion_target", "max_holding_bars",
        "risk_per_trade", "max_position_pct", "stop_atr_multiplier",
        "side_filter", "use_squeeze_filter", "use_band_walking_exit",
        "short_bb_std_dev", "short_rsi_threshold",
        "short_max_holding_bars", "short_position_pct",
        "use_trend_filter", "trend_ema_period",
    }
    model_params = {k: v for k, v in params.items() if k in model_keys}

    model = MeanReversionBB(**model_params)
    sim = DirectionalSimulator(model=model, initial_equity=10_000.0,
                               slippage_pct=0.0005, random_seed=42)

    t0 = time.time()
    results = sim.run_backtest_fast(df)
    elapsed = time.time() - t0

    ec = results["equity_curve"]
    sr = sharpe_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    so = sortino_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    dd = max_drawdown(ec)
    cr = calmar_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)

    # Trade breakdown by side
    trades = results["trade_log"]
    long_trades = [t for t in trades if t["side"] == "long"]
    short_trades = [t for t in trades if t["side"] == "short"]
    long_pnl = sum(t["pnl"] for t in long_trades)
    short_pnl = sum(t["pnl"] for t in short_trades)
    long_wins = sum(1 for t in long_trades if t["pnl"] > 0)
    short_wins = sum(1 for t in short_trades if t["pnl"] > 0)

    return {
        "label": label,
        "final_equity": results["final_equity"],
        "total_return_pct": results["total_return_pct"],
        "sharpe": sr,
        "sortino": so,
        "max_dd_pct": dd["max_drawdown_pct"],
        "calmar": cr,
        "total_trades": results["total_trades"],
        "long_trades": len(long_trades),
        "short_trades": len(short_trades),
        "long_pnl": long_pnl,
        "short_pnl": short_pnl,
        "long_win_rate": long_wins / len(long_trades) if long_trades else 0,
        "short_win_rate": short_wins / len(short_trades) if short_trades else 0,
        "elapsed_sec": round(elapsed, 1),
        "params": params,
    }


def print_result(r: dict):
    """Pretty-print one result row."""
    sr = r["sharpe"]
    sr_str = f"{sr:.2f}" if sr != float("inf") else "inf"
    print(
        f"  {r['label']:<45} "
        f"Return: {r['total_return_pct']:+7.2f}%  "
        f"Sharpe: {sr_str:>6}  "
        f"MaxDD: {r['max_dd_pct']:5.2f}%  "
        f"Trades: {r['total_trades']:3d} "
        f"(L:{r['long_trades']} S:{r['short_trades']})  "
        f"L_PnL: ${r['long_pnl']:+.2f}  S_PnL: ${r['short_pnl']:+.2f}  "
        f"[{r['elapsed_sec']}s]"
    )


def main():
    parser = argparse.ArgumentParser(description="Bidirectional MRBB sweep")
    parser.add_argument("--days", type=int, default=None, help="Limit to last N days")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print("=" * 100)
    print("MRBB Bidirectional Backtest Sweep")
    print("=" * 100)

    df = load_data(DATA_PATH, days=args.days)
    print(f"Data: {len(df)} candles, {df.index[0]} to {df.index[-1]}")
    print()

    pm = PresetManager()
    all_results = []

    # ── 1. Baseline: long-only optimized ─────────────────────────────────
    print("Phase 1: Baseline (long-only optimized)")
    print("-" * 60)
    baseline_preset = pm.load("optimized")
    baseline_params = {k: v for k, v in baseline_preset.items()
                       if k not in ("name", "description", "regime")}
    r = run_single(df, baseline_params, "baseline_long_only")
    print_result(r)
    all_results.append(r)
    print()

    # ── 2. Bidirectional with preset defaults ────────────────────────────
    print("Phase 2: Bidirectional preset (3.0σ, RSI>80, 4h hold, 10% size)")
    print("-" * 60)
    bidir_preset = pm.load("optimized_bidirectional")
    bidir_params = {k: v for k, v in bidir_preset.items()
                    if k not in ("name", "description", "regime")}
    r = run_single(df, bidir_params, "bidir_default")
    print_result(r)
    all_results.append(r)
    print()

    # ── 3. Bidirectional WITHOUT trend filter ────────────────────────────
    print("Phase 3: Bidirectional without trend filter")
    print("-" * 60)
    no_trend = dict(bidir_params)
    no_trend["use_trend_filter"] = False
    r = run_single(df, no_trend, "bidir_no_trend_filter")
    print_result(r)
    all_results.append(r)
    print()

    # ── 4. Parameter sweep on short thresholds ───────────────────────────
    print("Phase 4: Parameter sweep (short_rsi_threshold x short_bb_std_dev x short_max_holding_bars)")
    print("-" * 60)

    rsi_values = [75, 80, 85]
    bb_sd_values = [2.5, 3.0, 3.5]
    hold_values = [24, 48, 96]

    sweep_results = []
    total = len(rsi_values) * len(bb_sd_values) * len(hold_values)
    idx = 0

    for rsi_th, bb_sd, hold in product(rsi_values, bb_sd_values, hold_values):
        idx += 1
        label = f"RSI>{rsi_th}_BB{bb_sd}_hold{hold}"
        params = dict(bidir_params)
        params["short_rsi_threshold"] = rsi_th
        params["short_bb_std_dev"] = bb_sd
        params["short_max_holding_bars"] = hold
        r = run_single(df, params, label)
        print_result(r)
        all_results.append(r)
        sweep_results.append(r)

    print()

    # ── 5. Summary ───────────────────────────────────────────────────────
    print("=" * 100)
    print("SUMMARY — Top 10 by Sharpe Ratio")
    print("=" * 100)

    def sort_key(r):
        s = r["sharpe"]
        return s if s != float("inf") else 999

    ranked = sorted(all_results, key=sort_key, reverse=True)
    for i, r in enumerate(ranked[:10], 1):
        sr = r["sharpe"]
        sr_str = f"{sr:.2f}" if sr != float("inf") else "inf"
        print(
            f"  {i:2d}. {r['label']:<45} "
            f"Return: {r['total_return_pct']:+7.2f}%  "
            f"Sharpe: {sr_str:>6}  "
            f"MaxDD: {r['max_dd_pct']:5.2f}%  "
            f"Trades: {r['total_trades']:3d} "
            f"(L:{r['long_trades']} S:{r['short_trades']})"
        )

    print()
    print("SUMMARY — Top 10 by Total Return")
    print("=" * 100)
    ranked_return = sorted(all_results, key=lambda r: r["total_return_pct"], reverse=True)
    for i, r in enumerate(ranked_return[:10], 1):
        sr = r["sharpe"]
        sr_str = f"{sr:.2f}" if sr != float("inf") else "inf"
        print(
            f"  {i:2d}. {r['label']:<45} "
            f"Return: {r['total_return_pct']:+7.2f}%  "
            f"Sharpe: {sr_str:>6}  "
            f"MaxDD: {r['max_dd_pct']:5.2f}%  "
            f"Trades: {r['total_trades']:3d} "
            f"(L:{r['long_trades']} S:{r['short_trades']})"
        )

    # Save all results
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Summary JSON
    summary = []
    for r in all_results:
        row = {k: v for k, v in r.items() if k != "params"}

        def _ser(v):
            if isinstance(v, float) and (v == float("inf") or v == float("-inf")):
                return str(v)
            raise TypeError

        row["params"] = r["params"]
        summary.append(row)

    with open(output_dir / "sweep_results.json", "w") as f:
        json.dump(summary, f, indent=2, default=_ser)

    # CSV for easy analysis
    rows = []
    for r in all_results:
        row = {k: v for k, v in r.items() if k != "params"}
        row["short_rsi_threshold"] = r["params"].get("short_rsi_threshold", "")
        row["short_bb_std_dev"] = r["params"].get("short_bb_std_dev", "")
        row["short_max_holding_bars"] = r["params"].get("short_max_holding_bars", "")
        row["short_position_pct"] = r["params"].get("short_position_pct", "")
        row["use_trend_filter"] = r["params"].get("use_trend_filter", "")
        row["side_filter"] = r["params"].get("side_filter", "")
        rows.append(row)
    pd.DataFrame(rows).to_csv(output_dir / "sweep_results.csv", index=False)

    print(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    main()
