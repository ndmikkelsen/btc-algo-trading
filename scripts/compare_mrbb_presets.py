#!/usr/bin/env python3
"""Compare MRBB parameter presets via backtesting.

Usage:
    python scripts/compare_mrbb_presets.py --data data/btcusdt_5m.csv
    python scripts/compare_mrbb_presets.py --data data/btcusdt_5m.csv --presets conservative aggressive
    python scripts/compare_mrbb_presets.py --data data/btcusdt_5m.csv --presets all --days 365
"""

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from strategies.mean_reversion_bb.presets import PresetManager
from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.simulator import DirectionalSimulator
from strategies.avellaneda_stoikov.metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
)

# 5-minute candles per year: 365.25 * 24 * 12
PERIODS_PER_YEAR_5M = 105_120

DEFAULT_OUTPUT_DIR = Path("backtests/mrbb/comparisons")

# Params that map directly from preset YAML to MeanReversionBB constructor
MODEL_PARAMS = [
    "bb_period",
    "bb_std_dev",
    "bb_inner_std_dev",
    "vwap_period",
    "vwap_confirmation_pct",
    "kc_period",
    "kc_atr_multiplier",
    "rsi_period",
    "rsi_oversold",
    "rsi_overbought",
    "adx_period",
    "adx_threshold",
    "use_regime_filter",
    "reversion_target",
    "max_holding_bars",
    "risk_per_trade",
    "max_position_pct",
    "stop_atr_multiplier",
]


def load_data(data_path: str, days: int | None = None) -> pd.DataFrame:
    """Load OHLCV CSV data, optionally limited to last N days."""
    path = Path(data_path)
    if not path.exists():
        print(f"Error: data file not found: {path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(path)
    required = {"open", "high", "low", "close", "volume", "timestamp"}
    missing = required - set(df.columns)
    if missing:
        print(f"Error: CSV missing columns: {missing}", file=sys.stderr)
        sys.exit(1)

    ts = df["timestamp"]
    if pd.api.types.is_numeric_dtype(ts):
        df["timestamp"] = pd.to_datetime(ts, unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(ts)

    df = df.set_index("timestamp")

    if days:
        candles_per_day = 24 * 12  # 5m candles
        df = df.tail(days * candles_per_day)

    return df


def compute_trade_stats(trade_log: list) -> dict:
    """Compute win rate and profit factor from the trade log."""
    if not trade_log:
        return {"win_rate": 0.0, "profit_factor": 0.0, "avg_pnl": 0.0}

    wins = [t for t in trade_log if t["pnl"] > 0]
    losses = [t for t in trade_log if t["pnl"] <= 0]
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    avg_pnl = sum(t["pnl"] for t in trade_log) / len(trade_log)

    return {
        "win_rate": len(wins) / len(trade_log),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
        "avg_pnl": avg_pnl,
    }


def backtest_preset(
    preset_name: str,
    preset_params: dict,
    df: pd.DataFrame,
    initial_equity: float,
) -> dict:
    """Run a single preset backtest and return results dict."""
    # Extract model params from preset
    model_kwargs = {}
    for key in MODEL_PARAMS:
        if key in preset_params:
            model_kwargs[key] = preset_params[key]

    model = MeanReversionBB(**model_kwargs)
    sim = DirectionalSimulator(
        model=model,
        initial_equity=initial_equity,
        slippage_pct=0.0005,
        random_seed=42,
    )

    results = sim.run_backtest_fast(df)

    ec = results["equity_curve"]
    if not ec:
        return {
            "preset": preset_name,
            "return_pct": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_dd_pct": 0.0,
            "calmar": 0.0,
            "trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_pnl": 0.0,
            "final_equity": initial_equity,
        }

    sr = sharpe_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    so = sortino_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    dd = max_drawdown(ec)
    cr = calmar_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    ts = compute_trade_stats(results["trade_log"])

    return {
        "preset": preset_name,
        "return_pct": results["total_return_pct"],
        "sharpe": sr,
        "sortino": so,
        "max_dd_pct": dd["max_drawdown_pct"],
        "calmar": cr,
        "trades": results["total_trades"],
        "win_rate": ts["win_rate"],
        "profit_factor": ts["profit_factor"],
        "avg_pnl": ts["avg_pnl"],
        "final_equity": results["final_equity"],
    }


def _backtest_worker(args: tuple) -> dict:
    """Worker function for multiprocessing."""
    preset_name, preset_params, data_path, days, initial_equity = args

    # Reimport in subprocess
    df = load_data(data_path, days=days)
    return backtest_preset(preset_name, preset_params, df, initial_equity)


def format_table(results: list[dict]) -> str:
    """Format comparison results as an aligned text table."""
    if not results:
        return "No results to display."

    def _fmt_float(v, fmt_str):
        if v == float("inf"):
            return "inf"
        if v == float("-inf"):
            return "-inf"
        return fmt_str.format(v)

    header = (
        f"{'Preset':<20} | {'Return':>8} | {'Sharpe':>7} | {'Sortino':>8} | "
        f"{'Max DD':>8} | {'Calmar':>7} | {'Trades':>6} | {'Win Rate':>8} | "
        f"{'PF':>6} | {'Avg P&L':>10}"
    )
    separator = "-" * len(header)

    rows = [header, separator]
    for r in results:
        row = (
            f"{r['preset']:<20} | "
            f"{_fmt_float(r['return_pct'], '{:+.2f}%'):>8} | "
            f"{_fmt_float(r['sharpe'], '{:.2f}'):>7} | "
            f"{_fmt_float(r['sortino'], '{:.2f}'):>8} | "
            f"{_fmt_float(r['max_dd_pct'], '{:.1f}%'):>8} | "
            f"{_fmt_float(r['calmar'], '{:.2f}'):>7} | "
            f"{r['trades']:>6} | "
            f"{_fmt_float(r['win_rate'] * 100, '{:.1f}%'):>8} | "
            f"{_fmt_float(r['profit_factor'], '{:.2f}'):>6} | "
            f"${r['avg_pnl']:>+9.2f}"
        )
        rows.append(row)

    return "\n".join(rows)


def _sanitize_for_json(obj):
    """Replace inf/-inf with string representations for JSON compatibility."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (obj == float("inf") or obj == float("-inf")):
        return str(obj)
    return obj


def save_results(results: list[dict], output_dir: Path) -> Path:
    """Save comparison results to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / "comparison.json"
    with open(out_path, "w") as f:
        json.dump(_sanitize_for_json(results), f, indent=2)

    return out_path


def run_comparison(
    data_path: str,
    preset_names: list[str] | None = None,
    initial_equity: float = 10_000.0,
    days: int | None = None,
    output_dir: Path | None = None,
    parallel: bool = False,
) -> list[dict]:
    """Run backtests for multiple presets and return comparison results.

    Args:
        data_path: Path to OHLCV CSV.
        preset_names: List of preset names, or None for all.
        initial_equity: Starting equity per backtest.
        days: Limit to last N days of data.
        output_dir: Where to save results JSON.
        parallel: Use multiprocessing.

    Returns:
        List of result dicts, one per preset.
    """
    pm = PresetManager()

    if preset_names is None or preset_names == ["all"]:
        preset_names = pm.list()

    if not preset_names:
        print("No presets found.", file=sys.stderr)
        return []

    # Load all preset params upfront
    presets = {}
    for name in preset_names:
        try:
            presets[name] = pm.load(name)
        except FileNotFoundError:
            print(f"Warning: preset '{name}' not found, skipping.", file=sys.stderr)

    if not presets:
        print("No valid presets to backtest.", file=sys.stderr)
        return []

    results = []

    if parallel and len(presets) > 1:
        worker_args = [
            (name, params, data_path, days, initial_equity)
            for name, params in presets.items()
        ]
        with ProcessPoolExecutor() as executor:
            results = list(executor.map(_backtest_worker, worker_args))
    else:
        df = load_data(data_path, days=days)
        for name, params in presets.items():
            print(f"  Backtesting preset: {name}...", flush=True)
            result = backtest_preset(name, params, df, initial_equity)
            results.append(result)

    # Sort by return descending
    results.sort(key=lambda r: r["return_pct"], reverse=True)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Compare MRBB parameter presets via backtesting"
    )
    parser.add_argument("--data", required=True, help="Path to OHLCV CSV file")
    parser.add_argument(
        "--presets",
        nargs="*",
        default=None,
        help='Preset names to compare, or "all" (default: all)',
    )
    parser.add_argument(
        "--equity", type=float, default=10_000.0, help="Initial equity"
    )
    parser.add_argument("--days", type=int, default=None, help="Limit to last N days")
    parser.add_argument(
        "--output",
        default=None,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--parallel", action="store_true", help="Run backtests in parallel"
    )

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR

    print("MRBB Preset Comparison")
    print("=" * 60)
    print(f"Data: {args.data}")
    print(f"Equity: ${args.equity:,.2f}")
    if args.days:
        print(f"Period: last {args.days} days")
    print()

    results = run_comparison(
        data_path=args.data,
        preset_names=args.presets,
        initial_equity=args.equity,
        days=args.days,
        output_dir=output_dir,
        parallel=args.parallel,
    )

    if not results:
        return

    print()
    print(format_table(results))
    print()

    json_path = save_results(results, output_dir)
    print(f"Results saved to: {json_path}")


if __name__ == "__main__":
    main()
