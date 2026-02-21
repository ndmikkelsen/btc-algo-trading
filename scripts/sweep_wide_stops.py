#!/usr/bin/env python3
"""Wide stop-loss sweep: test 3.5x–6.0x ATR with decay variants.

Tests 6 ATR multipliers × 3 decay schedules = 18 configurations.
Phase thresholds calibrated for max_holding_bars=288.

ATR multipliers: 3.5, 4.0, 4.5, 5.0, 5.5, 6.0
Decay schedules per multiplier:
  1. No decay (flat)
  2. Gentle decay (mult_1 = 80%, mult_2 = 65% of initial)
  3. Moderate decay (mult_1 = 60%, mult_2 = 40% of initial)

Usage:
    python3 scripts/sweep_wide_stops.py
    python3 scripts/sweep_wide_stops.py --days 90
"""

import argparse
import json
import os
import sys
import time
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
OUTPUT_DIR = Path("backtests/mrbb/wide_stop_sweep")

# Phase thresholds calibrated for max_holding_bars=288
PHASE_1 = 0.035
PHASE_2 = 0.069

ATR_MULTIPLIERS = [3.5, 4.0, 4.5, 5.0, 5.5, 6.0]

DECAY_SCHEDULES = [
    {"tag": "flat", "description": "no decay", "mult_1_pct": 1.0, "mult_2_pct": 1.0},
    {"tag": "gentle", "description": "gentle decay (80%/65%)", "mult_1_pct": 0.80, "mult_2_pct": 0.65},
    {"tag": "moderate", "description": "moderate decay (60%/40%)", "mult_1_pct": 0.60, "mult_2_pct": 0.40},
]


def build_configs():
    """Generate 18 stop configurations (6 ATR × 3 decay schedules)."""
    configs = []
    idx = 1
    for atr in ATR_MULTIPLIERS:
        for decay in DECAY_SCHEDULES:
            mult_1 = round(atr * decay["mult_1_pct"], 2)
            mult_2 = round(atr * decay["mult_2_pct"], 2)
            label = f"{idx:02d}_{atr:.1f}x_{decay['tag']}"
            desc = f"{atr:.1f}x ATR, {decay['description']}"
            if decay["tag"] != "flat":
                desc += f" → {mult_1:.2f}x → {mult_2:.2f}x"
            configs.append({
                "label": label,
                "description": desc,
                "stop_atr_multiplier": atr,
                "stop_decay_phase_1": PHASE_1,
                "stop_decay_phase_2": PHASE_2,
                "stop_decay_mult_1": mult_1,
                "stop_decay_mult_2": mult_2,
            })
            idx += 1
    return configs


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


def run_single(df: pd.DataFrame, base_params: dict, stop_config: dict) -> dict:
    """Run one backtest with base params + stop override."""
    model_keys = {
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
    params = {k: v for k, v in base_params.items() if k in model_keys}

    for key in ("stop_atr_multiplier", "stop_decay_phase_1", "stop_decay_phase_2",
                "stop_decay_mult_1", "stop_decay_mult_2"):
        if key in stop_config:
            params[key] = stop_config[key]

    model = MeanReversionBB(**params)
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

    trades = results["trade_log"]
    wins = [t for t in trades if t["pnl"] > 0]
    worst_trade = min((t["pnl"] for t in trades), default=0.0)
    best_trade = max((t["pnl"] for t in trades), default=0.0)
    stop_exits = sum(1 for t in trades if t["reason"] == "stop_loss")

    durations = [t.get("bars_held", 0) for t in trades]
    phase_1_threshold = int(model.max_holding_bars * model.stop_decay_phase_1)
    phase_2_threshold = int(model.max_holding_bars * model.stop_decay_phase_2)
    trades_reaching_p1 = sum(1 for d in durations if d >= phase_1_threshold)
    trades_reaching_p2 = sum(1 for d in durations if d >= phase_2_threshold)

    return {
        "label": stop_config["label"],
        "description": stop_config["description"],
        "final_equity": results["final_equity"],
        "total_return_pct": results["total_return_pct"],
        "sharpe": sr,
        "sortino": so,
        "max_dd_pct": dd["max_drawdown_pct"],
        "calmar": cr,
        "total_trades": results["total_trades"],
        "win_rate": len(wins) / len(trades) if trades else 0,
        "worst_trade": worst_trade,
        "best_trade": best_trade,
        "stop_exits": stop_exits,
        "stop_exit_pct": stop_exits / len(trades) * 100 if trades else 0,
        "avg_pnl": sum(t["pnl"] for t in trades) / len(trades) if trades else 0,
        "avg_bars_held": sum(durations) / len(durations) if durations else 0,
        "max_bars_held": max(durations) if durations else 0,
        "trades_reaching_p1": trades_reaching_p1,
        "trades_reaching_p2": trades_reaching_p2,
        "phase_1_bar": phase_1_threshold,
        "phase_2_bar": phase_2_threshold,
        "elapsed_sec": round(elapsed, 1),
        "stop_params": {k: v for k, v in stop_config.items()
                        if k not in ("label", "description")},
    }


def fmt_float(v, width=7, decimals=2):
    if v == float("inf"):
        return f"{'inf':>{width}}"
    if v == float("-inf"):
        return f"{'-inf':>{width}}"
    return f"{v:>{width}.{decimals}f}"


def print_efficient_frontier(all_results):
    """Identify and print the Sharpe/MaxDD efficient frontier."""
    # Bucket MaxDD into ranges and find best Sharpe per bucket
    buckets = [
        (0, 2, "0-2%"),
        (2, 4, "2-4%"),
        (4, 6, "4-6%"),
        (6, 8, "6-8%"),
        (8, 10, "8-10%"),
        (10, 15, "10-15%"),
        (15, 100, "15%+"),
    ]

    print()
    print("=" * 90)
    print("EFFICIENT FRONTIER — Best Sharpe at each MaxDD bucket")
    print("=" * 90)
    print(f"{'MaxDD Bucket':<14} {'Config':<25} {'Sharpe':>7} {'MaxDD%':>7} {'Return%':>9} {'WinR%':>6}")
    print("-" * 90)

    frontier = []
    for lo, hi, label in buckets:
        candidates = [r for r in all_results if lo <= abs(r["max_dd_pct"]) < hi]
        if not candidates:
            print(f"{label:<14} {'(none)':>25}")
            continue
        best = max(candidates, key=lambda r: r["sharpe"] if r["sharpe"] != float("inf") else -999)
        frontier.append(best)
        sr_str = fmt_float(best["sharpe"])
        print(
            f"{label:<14} {best['label']:<25} {sr_str} "
            f"{best['max_dd_pct']:6.2f}% "
            f"{best['total_return_pct']:+8.2f}% "
            f"{best['win_rate']*100:5.1f}%"
        )

    return frontier


def main():
    parser = argparse.ArgumentParser(description="Wide stop-loss ATR sweep")
    parser.add_argument("--days", type=int, default=None, help="Limit to last N days")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    configs = build_configs()
    total = len(configs)

    print("=" * 120)
    print("MRBB Wide Stop Sweep — ATR 3.5x–6.0x × 3 Decay Schedules")
    print("=" * 120)

    df = load_data(DATA_PATH, days=args.days)
    print(f"Data: {len(df)} candles, {df.index[0]} to {df.index[-1]}")
    print(f"Configs: {total} (6 ATR × 3 decay)")
    print(f"Phase thresholds: P1={PHASE_1} P2={PHASE_2}")
    print()

    pm = PresetManager()
    base_preset = pm.load("optimized")
    base_params = {k: v for k, v in base_preset.items()
                   if k not in ("name", "description", "regime")}
    print(f"Base preset: optimized (side_filter={base_params.get('side_filter', 'both')})")
    print()

    all_results = []
    for i, cfg in enumerate(configs, 1):
        print(f"[{i:2d}/{total}] {cfg['description']}")
        r = run_single(df, base_params, cfg)
        all_results.append(r)
        sr_str = fmt_float(r["sharpe"])
        print(
            f"       Return: {r['total_return_pct']:+7.2f}%  "
            f"Sharpe: {sr_str}  "
            f"MaxDD: {r['max_dd_pct']:5.2f}%  "
            f"Worst: ${r['worst_trade']:+.2f}  "
            f"Trades: {r['total_trades']}  "
            f"WinRate: {r['win_rate']*100:.1f}%  "
            f"StopExits: {r['stop_exits']} ({r['stop_exit_pct']:.1f}%)  "
            f"[{r['elapsed_sec']}s]"
        )

    # Comparison table
    print()
    print("=" * 145)
    print("COMPARISON TABLE")
    print("=" * 145)
    header = (
        f"{'Config':<25} {'Return':>8} {'Sharpe':>7} {'Sortino':>8} "
        f"{'MaxDD':>6} {'Calmar':>7} {'Worst$':>9} {'Best$':>9} "
        f"{'Trades':>6} {'WinR%':>6} {'Stops':>5} {'Stop%':>6} "
        f"{'AvgPnL':>8} {'AvgBar':>6} {'MaxBar':>6}"
    )
    print(header)
    print("-" * 145)

    prev_atr = None
    for r in all_results:
        # Extract ATR from stop_params for visual grouping
        cur_atr = r["stop_params"]["stop_atr_multiplier"]
        if prev_atr is not None and cur_atr != prev_atr:
            print("-" * 145)
        prev_atr = cur_atr

        sr_str = fmt_float(r["sharpe"])
        so_str = fmt_float(r["sortino"], 8)
        cr_str = fmt_float(r["calmar"])
        print(
            f"{r['label']:<25} "
            f"{r['total_return_pct']:+7.2f}% "
            f"{sr_str} "
            f"{so_str} "
            f"{r['max_dd_pct']:5.2f}% "
            f"{cr_str} "
            f"${r['worst_trade']:+8.2f} "
            f"${r['best_trade']:+8.2f} "
            f"{r['total_trades']:>6} "
            f"{r['win_rate']*100:5.1f}% "
            f"{r['stop_exits']:>5} "
            f"{r['stop_exit_pct']:5.1f}% "
            f"${r['avg_pnl']:+7.2f} "
            f"{r['avg_bars_held']:5.1f} "
            f"{r['max_bars_held']:>6}"
        )

    # Efficient frontier
    frontier = print_efficient_frontier(all_results)

    # Winners
    print()
    print("=" * 90)
    print("WINNERS")
    print("=" * 90)

    valid = [r for r in all_results if r["sharpe"] != float("inf") and r["sharpe"] != float("-inf")]
    if not valid:
        valid = all_results

    best_sharpe = max(valid, key=lambda r: r["sharpe"])
    best_return = max(all_results, key=lambda r: r["total_return_pct"])
    best_dd = max(all_results, key=lambda r: r["max_dd_pct"])
    best_worst = max(all_results, key=lambda r: r["worst_trade"])
    best_calmar = max(valid, key=lambda r: r["calmar"])

    # Risk-adjusted: best Sharpe among configs with MaxDD < 10%
    risk_adj_candidates = [r for r in valid if r["max_dd_pct"] < 10]
    if not risk_adj_candidates:
        risk_adj_candidates = valid
    best_risk_adj = max(risk_adj_candidates, key=lambda r: r["sharpe"])

    print(f"  Best Sharpe:           {best_sharpe['label']} (Sharpe={fmt_float(best_sharpe['sharpe']).strip()}, DD={best_sharpe['max_dd_pct']:.2f}%)")
    print(f"  Best Risk-Adjusted:    {best_risk_adj['label']} (Sharpe={fmt_float(best_risk_adj['sharpe']).strip()}, DD={best_risk_adj['max_dd_pct']:.2f}%)")
    print(f"  Best Return:           {best_return['label']} ({best_return['total_return_pct']:+.2f}%)")
    print(f"  Lowest MaxDD:          {best_dd['label']} ({best_dd['max_dd_pct']:.2f}%)")
    print(f"  Best Calmar:           {best_calmar['label']} (Calmar={fmt_float(best_calmar['calmar']).strip()})")
    print(f"  Best Worst Trade:      {best_worst['label']} (${best_worst['worst_trade']:+.2f})")

    print()
    print("RECOMMENDATION:")
    print(f"  >>> BEST SHARPE:        {best_sharpe['label']}")
    print(f"      Sharpe={fmt_float(best_sharpe['sharpe']).strip()}, "
          f"Return={best_sharpe['total_return_pct']:+.2f}%, "
          f"MaxDD={best_sharpe['max_dd_pct']:.2f}%, "
          f"WinRate={best_sharpe['win_rate']*100:.1f}%")
    print(f"  >>> BEST RISK-ADJUSTED: {best_risk_adj['label']}")
    print(f"      Sharpe={fmt_float(best_risk_adj['sharpe']).strip()}, "
          f"Return={best_risk_adj['total_return_pct']:+.2f}%, "
          f"MaxDD={best_risk_adj['max_dd_pct']:.2f}%, "
          f"WinRate={best_risk_adj['win_rate']*100:.1f}%")

    # Save results
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    def _ser(v):
        if isinstance(v, float) and (v == float("inf") or v == float("-inf")):
            return str(v)
        raise TypeError

    with open(output_dir / "sweep_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=_ser)

    rows = []
    for r in all_results:
        row = {k: v for k, v in r.items() if k != "stop_params"}
        row.update(r["stop_params"])
        rows.append(row)
    pd.DataFrame(rows).to_csv(output_dir / "sweep_results.csv", index=False)

    print(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    main()
