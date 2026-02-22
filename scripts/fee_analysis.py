#!/usr/bin/env python3
"""Fee impact analysis: compare gross vs net-of-fees backtest results.

Runs the optimized preset backtest twice — once without explicit fees (gross)
and once with Bybit VIP0 taker fees (net) — to quantify fee drag on returns.

Usage:
    python scripts/fee_analysis.py --data data/btcusdt_5m.csv
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from strategies.mean_reversion_bb.config import TAKER_FEE
from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.presets import PresetManager
from strategies.mean_reversion_bb.simulator import DirectionalSimulator
from strategies.avellaneda_stoikov.metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
)

PERIODS_PER_YEAR_5M = 105_120
OUTPUT_DIR = Path("backtests/mrbb/fee_analysis")

# Model params extracted from preset (keys that MeanReversionBB accepts)
_MODEL_KEYS = [
    "bb_period", "bb_std_dev", "bb_inner_std_dev", "vwap_period",
    "kc_period", "kc_atr_multiplier", "rsi_period", "adx_period",
    "adx_threshold", "use_regime_filter", "rsi_oversold", "rsi_overbought",
    "vwap_confirmation_pct", "stop_atr_multiplier", "reversion_target",
    "max_holding_bars", "risk_per_trade", "max_position_pct", "side_filter",
    "use_squeeze_filter", "use_band_walking_exit", "short_bb_std_dev",
    "short_rsi_threshold", "short_max_holding_bars", "short_position_pct",
    "use_trend_filter", "trend_ema_period",
    "stop_decay_phase_1", "stop_decay_phase_2",
    "stop_decay_mult_1", "stop_decay_mult_2",
]


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    ts = df["timestamp"]
    if pd.api.types.is_numeric_dtype(ts):
        df["timestamp"] = pd.to_datetime(ts, unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(ts)
    return df.set_index("timestamp")


def run_single(df: pd.DataFrame, preset: dict, taker_fee: float, seed: int = 42) -> dict:
    """Run one backtest with given fee setting, return results + metrics."""
    model_kwargs = {k: preset[k] for k in _MODEL_KEYS if k in preset}
    model = MeanReversionBB(**model_kwargs)
    sim = DirectionalSimulator(
        model=model,
        initial_equity=10_000.0,
        slippage_pct=0.0005,
        random_seed=seed,
        taker_fee=taker_fee,
    )
    results = sim.run_backtest_fast(df)

    ec = results["equity_curve"]
    sr = sharpe_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    so = sortino_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    dd = max_drawdown(ec)
    cr = calmar_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)

    trades = results["trade_log"]
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))

    return {
        "final_equity": results["final_equity"],
        "total_return_pct": results["total_return_pct"],
        "sharpe": sr,
        "sortino": so,
        "max_dd_pct": dd["max_drawdown_pct"],
        "calmar": cr,
        "total_trades": results["total_trades"],
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
        "avg_pnl": sum(t["pnl"] for t in trades) / len(trades) if trades else 0.0,
        "total_pnl": sum(t["pnl"] for t in trades),
    }


def main():
    parser = argparse.ArgumentParser(description="Fee impact analysis")
    parser.add_argument("--data", required=True, help="Path to 5m OHLCV CSV")
    parser.add_argument("--preset", default="optimized", help="Preset name")
    parser.add_argument("--days", type=int, default=None, help="Limit to last N days")
    args = parser.parse_args()

    df = load_data(args.data)
    if args.days:
        df = df.tail(args.days * 24 * 12)

    pm = PresetManager()
    preset = pm.load(args.preset)

    print(f"Fee Impact Analysis — preset: {args.preset}")
    print(f"Data: {len(df)} candles, {df.index[0]} to {df.index[-1]}")
    print(f"Taker fee rate: {TAKER_FEE * 100:.3f}%")
    print("=" * 70)

    # Run gross (no fees) and net (with fees)
    print("\nRunning GROSS backtest (taker_fee=0) ...")
    gross = run_single(df, preset, taker_fee=0.0)

    print("Running NET backtest (taker_fee={:.4f}) ...".format(TAKER_FEE))
    net = run_single(df, preset, taker_fee=TAKER_FEE)

    # Calculate fee drag
    fee_drag_pct = gross["total_return_pct"] - net["total_return_pct"]
    fee_drag_abs = gross["final_equity"] - net["final_equity"]

    # Estimate total fees paid
    # Each trade: entry fee + exit fee = 2 × avg_position_value × taker_fee
    # Plus partial exits add another 0.5 leg on average
    total_fees_est = fee_drag_abs  # The equity difference IS the total fees

    print("\n{:<30} {:>15} {:>15} {:>15}".format("Metric", "Gross", "Net", "Difference"))
    print("-" * 75)

    metrics = [
        ("Total Return (%)", "total_return_pct", ".2f"),
        ("Final Equity ($)", "final_equity", ",.2f"),
        ("Sharpe Ratio", "sharpe", ".4f"),
        ("Sortino Ratio", "sortino", ".4f"),
        ("Max Drawdown (%)", "max_dd_pct", ".2f"),
        ("Calmar Ratio", "calmar", ".4f"),
        ("Total Trades", "total_trades", "d"),
        ("Win Rate", "win_rate", ".3f"),
        ("Profit Factor", "profit_factor", ".3f"),
        ("Avg Trade PnL ($)", "avg_pnl", ".4f"),
    ]

    for label, key, fmt in metrics:
        g = gross[key]
        n = net[key]
        if isinstance(g, float) and (g == float("inf") or g == float("-inf")):
            g_str = str(g)
        else:
            g_str = format(g, fmt)
        if isinstance(n, float) and (n == float("inf") or n == float("-inf")):
            n_str = str(n)
        else:
            n_str = format(n, fmt)
        if key == "total_trades":
            d_str = format(g - n, "d")
        elif isinstance(g, float) and isinstance(n, float):
            diff = g - n
            d_str = format(diff, fmt) if not (diff == float("inf") or diff == float("-inf")) else str(diff)
        else:
            d_str = "—"
        print(f"{label:<30} {g_str:>15} {n_str:>15} {d_str:>15}")

    print()
    print(f"Total fee drag: ${fee_drag_abs:,.2f} ({fee_drag_pct:.2f}% of equity)")
    avg_fee_per_trade = fee_drag_abs / gross["total_trades"] if gross["total_trades"] > 0 else 0
    print(f"Average fee per trade: ${avg_fee_per_trade:.4f}")
    print(f"Fee as % of avg gross PnL: {abs(avg_fee_per_trade / gross['avg_pnl']) * 100:.1f}%" if gross["avg_pnl"] != 0 else "")

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "preset": args.preset,
        "taker_fee_rate": TAKER_FEE,
        "data_candles": len(df),
        "data_range": f"{df.index[0]} to {df.index[-1]}",
        "gross": gross,
        "net": net,
        "fee_impact": {
            "return_drag_pct": fee_drag_pct,
            "return_drag_abs": fee_drag_abs,
            "sharpe_drag": gross["sharpe"] - net["sharpe"],
            "avg_fee_per_trade": avg_fee_per_trade,
            "net_still_profitable": net["total_return_pct"] > 0,
        },
    }

    import numpy as np_ser

    def _serialize(obj):
        if isinstance(obj, float) and (obj == float("inf") or obj == float("-inf")):
            return str(obj)
        if isinstance(obj, (np_ser.bool_, np_ser.integer)):
            return int(obj)
        if isinstance(obj, np_ser.floating):
            return float(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    out_path = OUTPUT_DIR / "fee_impact.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=_serialize)
    print(f"\nSaved results to {out_path}")


if __name__ == "__main__":
    main()
