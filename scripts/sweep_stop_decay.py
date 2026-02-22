#!/usr/bin/env python3
"""Backtest sweep comparing stop-loss configurations for MRBB strategy.

Compares 5 stop configurations using the optimized preset as base.
Phase thresholds are calibrated for the optimized preset's max_holding_bars=288:
avg trade ~10-19 bars, so phases must activate within that window.

1. Wide fixed (5.0x, no decay) — baseline
2. Fixed 3.0x (no decay) — new default ATR multiplier baseline
3. Fast decay (3.0→2.0→1.0, P1@bar6 P2@bar14) — aggressive tightening
4. Medium decay (3.0→2.0→1.5, P1@bar8 P2@bar18) — balanced
5. Gentle decay (3.0→2.5→2.0, P1@bar10 P2@bar20) — conservative

Measures: Sharpe, max DD, worst single trade, total return, win rate, trade duration.

Usage:
    python3 scripts/sweep_stop_decay.py
    python3 scripts/sweep_stop_decay.py --days 90
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
OUTPUT_DIR = Path("backtests/mrbb/stop_decay_sweep")

# Phase thresholds calibrated for optimized preset (max_holding_bars=288).
# avg trade ~10-19 bars, so phases must activate within that window.
# phase = bar_number / max_holding_bars → fraction
# e.g. bar 6 / 288 = 0.021, bar 14 / 288 = 0.049

STOP_CONFIGS = [
    {
        "label": "1_wide_fixed_5x",
        "description": "Wide fixed stop (5.0x ATR, no decay) — baseline",
        "stop_atr_multiplier": 5.0,
        "stop_decay_phase_1": 0.021,  # bar 6
        "stop_decay_phase_2": 0.049,  # bar 14
        "stop_decay_mult_1": 5.0,  # flat — no tightening
        "stop_decay_mult_2": 5.0,
    },
    {
        "label": "2_fixed_3x",
        "description": "Fixed 3.0x ATR (new default, no decay)",
        "stop_atr_multiplier": 3.0,
        "stop_decay_phase_1": 0.021,
        "stop_decay_phase_2": 0.049,
        "stop_decay_mult_1": 3.0,  # flat
        "stop_decay_mult_2": 3.0,
    },
    {
        "label": "3_fast_decay",
        "description": "Fast decay (3.0x → 2.0x → 1.0x, P1@bar6 P2@bar14)",
        "stop_atr_multiplier": 3.0,
        "stop_decay_phase_1": 0.021,   # bar 6
        "stop_decay_phase_2": 0.049,   # bar 14
        "stop_decay_mult_1": 2.0,
        "stop_decay_mult_2": 1.0,
    },
    {
        "label": "4_medium_decay",
        "description": "Medium decay (3.0x → 2.0x → 1.5x, P1@bar8 P2@bar18)",
        "stop_atr_multiplier": 3.0,
        "stop_decay_phase_1": 0.028,   # bar 8
        "stop_decay_phase_2": 0.063,   # bar 18
        "stop_decay_mult_1": 2.0,
        "stop_decay_mult_2": 1.5,
    },
    {
        "label": "5_gentle_decay",
        "description": "Gentle decay (3.0x → 2.5x → 2.0x, P1@bar10 P2@bar20)",
        "stop_atr_multiplier": 3.0,
        "stop_decay_phase_1": 0.035,   # bar 10
        "stop_decay_phase_2": 0.069,   # bar 20
        "stop_decay_mult_1": 2.5,
        "stop_decay_mult_2": 2.0,
    },
]


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
    # Merge base params with stop config overrides
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

    # Override stop params
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
    losses = [t for t in trades if t["pnl"] <= 0]
    worst_trade = min((t["pnl"] for t in trades), default=0.0)
    best_trade = max((t["pnl"] for t in trades), default=0.0)
    stop_exits = sum(1 for t in trades if t["reason"] == "stop_loss")

    # Trade duration analysis
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


def main():
    parser = argparse.ArgumentParser(description="Stop-decay backtest sweep")
    parser.add_argument("--days", type=int, default=None, help="Limit to last N days")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print("=" * 110)
    print("MRBB Stop-Decay Backtest Sweep — Phase 5 Validation")
    print("=" * 110)

    df = load_data(DATA_PATH, days=args.days)
    print(f"Data: {len(df)} candles, {df.index[0]} to {df.index[-1]}")
    print()

    # Load optimized preset as base
    pm = PresetManager()
    base_preset = pm.load("optimized")
    base_params = {k: v for k, v in base_preset.items()
                   if k not in ("name", "description", "regime")}
    print(f"Base preset: optimized (side_filter={base_params.get('side_filter', 'both')})")
    print()

    # Run all 5 configurations
    all_results = []
    for i, cfg in enumerate(STOP_CONFIGS, 1):
        print(f"[{i}/5] {cfg['description']}")
        r = run_single(df, base_params, cfg)
        all_results.append(r)
        sr_str = fmt_float(r["sharpe"])
        print(
            f"      Return: {r['total_return_pct']:+7.2f}%  "
            f"Sharpe: {sr_str}  "
            f"MaxDD: {r['max_dd_pct']:5.2f}%  "
            f"Worst: ${r['worst_trade']:+.2f}  "
            f"Trades: {r['total_trades']}  "
            f"WinRate: {r['win_rate']*100:.1f}%  "
            f"StopExits: {r['stop_exits']} ({r['stop_exit_pct']:.1f}%)  "
            f"[{r['elapsed_sec']}s]"
        )
        print(
            f"      AvgBars: {r['avg_bars_held']:.1f}  "
            f"MaxBars: {r['max_bars_held']}  "
            f"ReachP1(bar{r['phase_1_bar']}): {r['trades_reaching_p1']}/{r['total_trades']}  "
            f"ReachP2(bar{r['phase_2_bar']}): {r['trades_reaching_p2']}/{r['total_trades']}"
        )
        print()

    # Summary comparison table
    print("=" * 110)
    print("COMPARISON TABLE")
    print("=" * 110)
    header = (
        f"{'Config':<30} {'Return':>8} {'Sharpe':>7} {'Sortino':>8} "
        f"{'MaxDD':>6} {'Worst$':>9} {'Trades':>6} {'WinR%':>6} "
        f"{'Stops':>5} {'Stop%':>6} {'AvgPnL':>8}"
    )
    print(header)
    print("-" * 110)

    for r in all_results:
        sr_str = fmt_float(r["sharpe"])
        so_str = fmt_float(r["sortino"], 8)
        print(
            f"{r['label']:<30} "
            f"{r['total_return_pct']:+7.2f}% "
            f"{sr_str} "
            f"{so_str} "
            f"{r['max_dd_pct']:5.2f}% "
            f"${r['worst_trade']:+8.2f} "
            f"{r['total_trades']:>6} "
            f"{r['win_rate']*100:5.1f}% "
            f"{r['stop_exits']:>5} "
            f"{r['stop_exit_pct']:5.1f}% "
            f"${r['avg_pnl']:+7.2f}"
        )

    # Highlight winner
    print()
    best_sharpe = max(all_results, key=lambda r: r["sharpe"] if r["sharpe"] != float("inf") else -999)
    best_return = max(all_results, key=lambda r: r["total_return_pct"])
    best_dd = min(all_results, key=lambda r: r["max_dd_pct"])
    best_worst = max(all_results, key=lambda r: r["worst_trade"])

    print("WINNERS:")
    print(f"  Best Sharpe:       {best_sharpe['label']} ({fmt_float(best_sharpe['sharpe']).strip()})")
    print(f"  Best Return:       {best_return['label']} ({best_return['total_return_pct']:+.2f}%)")
    print(f"  Lowest MaxDD:      {best_dd['label']} ({best_dd['max_dd_pct']:.2f}%)")
    print(f"  Best Worst Trade:  {best_worst['label']} (${best_worst['worst_trade']:+.2f})")

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
