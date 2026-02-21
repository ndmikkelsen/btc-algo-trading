#!/usr/bin/env python3
"""Walk-forward and CPCV validation of optimized MRBB parameters.

Validates that the best config from the wide stop sweep (5.0x ATR, gentle
decay) is not overfit by checking IS vs OOS Sharpe degradation.

Two methods:
  1. Walk-Forward: rolling 6-month train, 3-month test windows
  2. CPCV: 6 folds, C(6,2)=15 combinations with purge gap

Verdict: NOT OVERFIT if OOS/IS Sharpe ratio > 50%.

Usage:
    python3 scripts/walk_forward_validation.py
"""

import json
import os
import sys
import time
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.simulator import DirectionalSimulator
from strategies.mean_reversion_bb.presets import PresetManager
from strategies.avellaneda_stoikov.metrics import sharpe_ratio

PERIODS_PER_YEAR_5M = 105_120
DATA_PATH = Path("data/btcusdt_5m.csv")
OUTPUT_DIR = Path("backtests/mrbb/walk_forward")

# Best config from wide stop sweep: 5.0x ATR with gentle decay
STOP_OVERRIDES = {
    "stop_atr_multiplier": 5.0,
    "stop_decay_mult_1": 4.0,
    "stop_decay_mult_2": 3.25,
    "stop_decay_phase_1": 0.035,
    "stop_decay_phase_2": 0.069,
}

# Model constructor keys (same set as sweep script)
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
    """Load OHLCV data with DatetimeIndex."""
    df = pd.read_csv(path)
    ts = df["timestamp"]
    if pd.api.types.is_numeric_dtype(ts):
        df["timestamp"] = pd.to_datetime(ts, unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(ts)
    df = df.set_index("timestamp")
    return df


def build_params() -> dict:
    """Load optimized preset and apply stop overrides."""
    pm = PresetManager()
    preset = pm.load("optimized")
    params = {k: v for k, v in preset.items() if k in MODEL_KEYS}
    params.update(STOP_OVERRIDES)
    return params


def run_backtest_sharpe(df: pd.DataFrame, params: dict) -> tuple:
    """Run backtest on a data slice and return (sharpe, total_return, n_trades)."""
    model = MeanReversionBB(**params)
    sim = DirectionalSimulator(
        model=model,
        initial_equity=10_000.0,
        slippage_pct=0.0005,
        random_seed=42,
    )
    results = sim.run_backtest_fast(df)
    ec = results["equity_curve"]
    sr = sharpe_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    return sr, results["total_return_pct"], results["total_trades"]


# ── Walk-Forward Validation ──────────────────────────────────────────


def generate_rolling_windows(
    df: pd.DataFrame, train_months: int = 6, test_months: int = 3
) -> list:
    """Generate rolling (non-anchored) walk-forward windows."""
    idx = df.index
    data_start = idx.min()
    data_end = idx.max()

    windows = []
    window_id = 0
    train_start = data_start

    while True:
        train_end = train_start + pd.DateOffset(months=train_months)
        test_start = train_end
        test_end = test_start + pd.DateOffset(months=test_months)

        if test_end > data_end:
            test_end = data_end

        # Need meaningful data in both windows
        train_mask = (idx >= train_start) & (idx < train_end)
        test_mask = (idx >= test_start) & (idx < test_end)

        if train_mask.sum() < 100 or test_mask.sum() < 100:
            break

        windows.append({
            "window_id": window_id,
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
        })
        window_id += 1

        # Step forward by test_months
        train_start = train_start + pd.DateOffset(months=test_months)

    return windows


def run_walk_forward(df: pd.DataFrame, params: dict) -> dict:
    """Run rolling walk-forward validation with fixed params."""
    windows = generate_rolling_windows(df, train_months=6, test_months=3)

    print(f"Walk-Forward: {len(windows)} rolling windows (6m train / 3m test)")
    print("-" * 90)
    print(
        f"{'Window':<8} {'Train Period':<28} {'Test Period':<28} "
        f"{'IS Sharpe':>10} {'OOS Sharpe':>10} {'OOS/IS':>8}"
    )
    print("-" * 90)

    results = []
    for w in windows:
        idx = df.index
        train_df = df.loc[(idx >= w["train_start"]) & (idx < w["train_end"])]
        test_df = df.loc[(idx >= w["test_start"]) & (idx < w["test_end"])]

        is_sharpe, is_ret, is_trades = run_backtest_sharpe(train_df, params)
        oos_sharpe, oos_ret, oos_trades = run_backtest_sharpe(test_df, params)

        ratio = oos_sharpe / is_sharpe if is_sharpe != 0 else float("nan")

        results.append({
            "window_id": w["window_id"],
            "train_start": str(w["train_start"]),
            "train_end": str(w["train_end"]),
            "test_start": str(w["test_start"]),
            "test_end": str(w["test_end"]),
            "is_sharpe": round(is_sharpe, 4),
            "oos_sharpe": round(oos_sharpe, 4),
            "oos_is_ratio": round(ratio, 4) if ratio == ratio else None,
            "is_return_pct": round(is_ret, 2),
            "oos_return_pct": round(oos_ret, 2),
            "is_trades": is_trades,
            "oos_trades": oos_trades,
        })

        train_str = (
            f"{w['train_start'].strftime('%Y-%m-%d')} → "
            f"{w['train_end'].strftime('%Y-%m-%d')}"
        )
        test_str = (
            f"{w['test_start'].strftime('%Y-%m-%d')} → "
            f"{w['test_end'].strftime('%Y-%m-%d')}"
        )
        ratio_str = f"{ratio:.2f}" if ratio == ratio else "N/A"
        print(
            f"  {w['window_id']:<6} {train_str:<28} {test_str:<28} "
            f"{is_sharpe:>10.4f} {oos_sharpe:>10.4f} {ratio_str:>8}"
        )

    # Aggregate
    is_sharpes = [r["is_sharpe"] for r in results]
    oos_sharpes = [r["oos_sharpe"] for r in results]
    valid_ratios = [
        r["oos_is_ratio"] for r in results if r["oos_is_ratio"] is not None
    ]

    avg_is = np.mean(is_sharpes) if is_sharpes else 0
    avg_oos = np.mean(oos_sharpes) if oos_sharpes else 0
    avg_ratio = np.mean(valid_ratios) if valid_ratios else 0
    overall_ratio = avg_oos / avg_is if avg_is != 0 else float("nan")

    summary = {
        "method": "walk_forward",
        "n_windows": len(results),
        "avg_is_sharpe": round(avg_is, 4),
        "avg_oos_sharpe": round(avg_oos, 4),
        "avg_oos_is_ratio": round(avg_ratio, 4),
        "overall_oos_is_ratio": round(overall_ratio, 4),
        "profitable_oos_windows": sum(
            1 for r in results if r["oos_sharpe"] > 0
        ),
        "windows": results,
    }

    print("-" * 90)
    print(f"  AVG IS Sharpe:  {avg_is:.4f}")
    print(f"  AVG OOS Sharpe: {avg_oos:.4f}")
    print(f"  OOS/IS ratio:   {overall_ratio:.4f} ({overall_ratio*100:.1f}%)")
    print(
        f"  Profitable OOS: {summary['profitable_oos_windows']}/{len(results)}"
    )

    return summary


# ── CPCV Validation ──────────────────────────────────────────────────


def run_cpcv_validation(
    df: pd.DataFrame, params: dict, n_groups: int = 6, purge_gap: int = 50
) -> dict:
    """Run CPCV with fixed params: 6 folds, C(6,2)=15 combos."""
    n_samples = len(df)
    group_size = n_samples // n_groups
    groups = []
    for i in range(n_groups):
        start = i * group_size
        end = start + group_size if i < n_groups - 1 else n_samples
        groups.append((start, end))

    # C(6,2) = 15 test-fold combinations (2 test folds, 4 train folds)
    test_fold_combos = list(combinations(range(n_groups), 2))
    n_splits = len(test_fold_combos)

    fold_dates = []
    for i, (s, e) in enumerate(groups):
        fold_dates.append(
            f"  Fold {i}: {df.index[s].strftime('%Y-%m-%d')} → "
            f"{df.index[min(e-1, n_samples-1)].strftime('%Y-%m-%d')} "
            f"({e - s} candles)"
        )

    print(f"\nCPCV: {n_groups} folds, C({n_groups},2) = {n_splits} splits, "
          f"purge_gap = {purge_gap}")
    print("-" * 90)
    for fd in fold_dates:
        print(fd)
    print("-" * 90)
    print(
        f"{'Split':<8} {'Test Folds':<14} {'Train Folds':<20} "
        f"{'IS Sharpe':>10} {'OOS Sharpe':>10} {'OOS/IS':>8}"
    )
    print("-" * 90)

    results = []
    for split_idx, test_folds in enumerate(test_fold_combos):
        train_folds = tuple(i for i in range(n_groups) if i not in test_folds)

        # Build index arrays
        test_idx = np.concatenate(
            [np.arange(groups[g][0], groups[g][1]) for g in test_folds]
        )
        train_idx = np.concatenate(
            [np.arange(groups[g][0], groups[g][1]) for g in train_folds]
        )

        # Apply purge: remove train indices within purge_gap of test boundaries
        if purge_gap > 0:
            test_min = test_idx.min()
            test_max = test_idx.max()
            # Also handle internal boundaries between non-contiguous test folds
            test_boundaries = set()
            for g in test_folds:
                test_boundaries.add(groups[g][0])
                test_boundaries.add(groups[g][1] - 1)
            mask = np.ones(len(train_idx), dtype=bool)
            for boundary in test_boundaries:
                mask &= np.abs(train_idx - boundary) >= purge_gap
            train_idx = train_idx[mask]

        train_df = df.iloc[train_idx].copy()
        test_df = df.iloc[test_idx].copy()

        is_sharpe, is_ret, is_trades = run_backtest_sharpe(train_df, params)
        oos_sharpe, oos_ret, oos_trades = run_backtest_sharpe(test_df, params)

        ratio = oos_sharpe / is_sharpe if is_sharpe != 0 else float("nan")

        results.append({
            "split_idx": split_idx,
            "test_folds": list(test_folds),
            "train_folds": list(train_folds),
            "is_sharpe": round(is_sharpe, 4),
            "oos_sharpe": round(oos_sharpe, 4),
            "oos_is_ratio": round(ratio, 4) if ratio == ratio else None,
            "is_return_pct": round(is_ret, 2),
            "oos_return_pct": round(oos_ret, 2),
            "is_trades": is_trades,
            "oos_trades": oos_trades,
        })

        ratio_str = f"{ratio:.2f}" if ratio == ratio else "N/A"
        print(
            f"  {split_idx:<6} {str(list(test_folds)):<14} "
            f"{str(list(train_folds)):<20} "
            f"{is_sharpe:>10.4f} {oos_sharpe:>10.4f} {ratio_str:>8}"
        )

    # Aggregate
    is_sharpes = [r["is_sharpe"] for r in results]
    oos_sharpes = [r["oos_sharpe"] for r in results]
    valid_ratios = [
        r["oos_is_ratio"] for r in results if r["oos_is_ratio"] is not None
    ]

    avg_is = np.mean(is_sharpes) if is_sharpes else 0
    avg_oos = np.mean(oos_sharpes) if oos_sharpes else 0
    avg_ratio = np.mean(valid_ratios) if valid_ratios else 0
    overall_ratio = avg_oos / avg_is if avg_is != 0 else float("nan")
    pbo = float(np.mean(np.array(oos_sharpes) < 0)) if oos_sharpes else 1.0

    summary = {
        "method": "cpcv",
        "n_groups": n_groups,
        "n_splits": n_splits,
        "purge_gap": purge_gap,
        "avg_is_sharpe": round(avg_is, 4),
        "avg_oos_sharpe": round(avg_oos, 4),
        "avg_oos_is_ratio": round(avg_ratio, 4),
        "overall_oos_is_ratio": round(overall_ratio, 4),
        "pbo": round(pbo, 4),
        "profitable_oos_splits": sum(
            1 for r in results if r["oos_sharpe"] > 0
        ),
        "splits": results,
    }

    print("-" * 90)
    print(f"  AVG IS Sharpe:  {avg_is:.4f}")
    print(f"  AVG OOS Sharpe: {avg_oos:.4f}")
    print(f"  OOS/IS ratio:   {overall_ratio:.4f} ({overall_ratio*100:.1f}%)")
    print(f"  PBO:            {pbo:.4f} ({pbo*100:.1f}%)")
    print(
        f"  Profitable OOS: {summary['profitable_oos_splits']}/{n_splits}"
    )

    return summary


# ── Main ─────────────────────────────────────────────────────────────


def main():
    print("=" * 90)
    print("MRBB Walk-Forward & CPCV Validation")
    print("Config: optimized preset + 5.0x ATR gentle decay")
    print("=" * 90)

    # Load data
    df = load_data(DATA_PATH)
    print(f"Data: {len(df)} candles, {df.index[0]} → {df.index[-1]}")

    # Build params
    params = build_params()
    print(f"Stop config: ATR={params['stop_atr_multiplier']}x, "
          f"decay={params['stop_decay_mult_1']}/{params['stop_decay_mult_2']}x, "
          f"phases={params['stop_decay_phase_1']}/{params['stop_decay_phase_2']}")
    print()

    t0 = time.time()

    # Run walk-forward
    print("=" * 90)
    print("1. WALK-FORWARD VALIDATION (6m train / 3m test, rolling)")
    print("=" * 90)
    wfo_results = run_walk_forward(df, params)

    # Run CPCV
    print()
    print("=" * 90)
    print("2. CPCV VALIDATION (6 folds, C(6,2)=15 splits, purge=50)")
    print("=" * 90)
    cpcv_results = run_cpcv_validation(df, params, n_groups=6, purge_gap=50)

    elapsed = time.time() - t0

    # Combined verdict
    wfo_ratio = wfo_results["overall_oos_is_ratio"]
    cpcv_ratio = cpcv_results["overall_oos_is_ratio"]
    avg_combined = (wfo_ratio + cpcv_ratio) / 2

    print()
    print("=" * 90)
    print("VERDICT")
    print("=" * 90)

    wfo_pct = wfo_ratio * 100
    cpcv_pct = cpcv_ratio * 100
    combined_pct = avg_combined * 100

    print(f"  Walk-Forward:  OOS Sharpe = {wfo_results['avg_oos_sharpe']:.4f} "
          f"({wfo_pct:.1f}% of IS {wfo_results['avg_is_sharpe']:.4f})")
    print(f"  CPCV:          OOS Sharpe = {cpcv_results['avg_oos_sharpe']:.4f} "
          f"({cpcv_pct:.1f}% of IS {cpcv_results['avg_is_sharpe']:.4f})")
    print(f"  CPCV PBO:      {cpcv_results['pbo']:.4f} "
          f"({cpcv_results['pbo']*100:.1f}% probability of overfitting)")
    print()

    if avg_combined > 0.5:
        verdict = "NOT OVERFIT"
        detail = (
            f"OOS retains {combined_pct:.1f}% of IS Sharpe "
            f"(WFO: {wfo_pct:.1f}%, CPCV: {cpcv_pct:.1f}%)"
        )
    else:
        verdict = "LIKELY OVERFIT"
        detail = (
            f"OOS retains only {combined_pct:.1f}% of IS Sharpe "
            f"(WFO: {wfo_pct:.1f}%, CPCV: {cpcv_pct:.1f}%)"
        )

    print(f"  >>> {verdict}: {detail}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print("=" * 90)

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "config": {
            "base_preset": "optimized",
            "stop_overrides": STOP_OVERRIDES,
            "initial_equity": 10_000.0,
            "slippage_pct": 0.0005,
            "periods_per_year": PERIODS_PER_YEAR_5M,
        },
        "data": {
            "path": str(DATA_PATH),
            "candles": len(df),
            "start": str(df.index[0]),
            "end": str(df.index[-1]),
        },
        "walk_forward": wfo_results,
        "cpcv": cpcv_results,
        "verdict": {
            "result": verdict,
            "wfo_oos_is_ratio": round(wfo_ratio, 4),
            "cpcv_oos_is_ratio": round(cpcv_ratio, 4),
            "combined_oos_is_ratio": round(avg_combined, 4),
            "cpcv_pbo": round(cpcv_results["pbo"], 4),
        },
        "elapsed_sec": round(elapsed, 1),
    }

    def _ser(v):
        if isinstance(v, float) and (v == float("inf") or v == float("-inf")):
            return str(v)
        if isinstance(v, np.floating):
            return float(v)
        if isinstance(v, np.integer):
            return int(v)
        raise TypeError(f"Not serializable: {type(v)}")

    out_path = OUTPUT_DIR / "wfo_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=_ser)

    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
