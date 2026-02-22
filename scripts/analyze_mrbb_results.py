#!/usr/bin/env python3
"""Analyze optimization results for Mean Reversion Bollinger Band strategy.

Loads optimization JSON files, ranks parameter sets, computes parameter
sensitivity, and prints summary tables.

Usage:
    python scripts/analyze_mrbb_results.py
    python scripts/analyze_mrbb_results.py --dir backtests/mrbb/optimization
    python scripts/analyze_mrbb_results.py --max-dd 0.10 --top 10
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

DEFAULT_RESULTS_DIR = "backtests/mrbb/optimization"
DEFAULT_MAX_DD = 0.15
DEFAULT_TOP_N = 5

# Parameters we expect in each result's params dict
PARAM_NAMES = [
    "bb_period",
    "bb_std_dev",
    "bb_inner_std_dev",
    "vwap_period",
    "kc_period",
    "kc_atr_multiplier",
    "rsi_period",
]


def load_results(results_dir: str) -> List[dict]:
    """Load all optimization result entries from JSON files.

    Each JSON file has a 'results' array. We flatten all entries
    from all files into a single list.
    """
    path = Path(results_dir)
    if not path.exists():
        print(f"Error: results directory not found: {path}", file=sys.stderr)
        sys.exit(1)

    all_entries = []
    json_files = sorted(path.glob("*.json"))

    if not json_files:
        print(f"Error: no JSON files found in {path}", file=sys.stderr)
        sys.exit(1)

    for f in json_files:
        with open(f) as fh:
            data = json.load(fh)
        entries = data.get("results", [])
        for entry in entries:
            entry["_source_file"] = f.name
        all_entries.extend(entries)

    return all_entries


def filter_feasible(entries: List[dict], max_dd: float) -> List[dict]:
    """Filter entries by max drawdown constraint."""
    return [e for e in entries if e.get("max_drawdown", 1.0) <= max_dd]


def rank_by_sharpe(entries: List[dict]) -> List[dict]:
    """Sort entries by Sharpe ratio descending."""
    return sorted(entries, key=lambda e: e.get("sharpe", 0), reverse=True)


def compute_param_sensitivity(entries: List[dict]) -> Dict[str, float]:
    """Compute correlation between each parameter value and Sharpe.

    Returns dict mapping param_name -> Pearson correlation coefficient.
    Only includes numeric parameters with variance > 0.
    """
    if len(entries) < 3:
        return {}

    sharpes = np.array([e.get("sharpe", 0) for e in entries])
    if np.std(sharpes) == 0:
        return {name: 0.0 for name in PARAM_NAMES}

    correlations = {}
    for name in PARAM_NAMES:
        values = []
        for e in entries:
            params = e.get("params", {})
            val = params.get(name)
            if isinstance(val, (int, float)):
                values.append(val)
            else:
                values.append(np.nan)

        values = np.array(values)
        valid = ~np.isnan(values)
        if valid.sum() < 3 or np.std(values[valid]) == 0:
            correlations[name] = 0.0
            continue

        # Correlation with Sharpe (only valid entries)
        corr = np.corrcoef(values[valid], sharpes[valid])[0, 1]
        correlations[name] = float(corr) if np.isfinite(corr) else 0.0

    return correlations


def print_summary_stats(all_entries: List[dict], feasible: List[dict]) -> None:
    """Print overall summary statistics."""
    sharpes = [e.get("sharpe", 0) for e in all_entries]
    print("Summary Statistics")
    print("=" * 60)
    print(f"Total combinations tested:   {len(all_entries)}")
    print(f"Meeting DD constraint:       {len(feasible)} ({len(feasible)/len(all_entries)*100:.1f}%)")
    print(f"Mean Sharpe:                 {np.mean(sharpes):.4f}")
    print(f"Median Sharpe:               {np.median(sharpes):.4f}")
    print(f"Std Sharpe:                  {np.std(sharpes):.4f}")
    print(f"Max Sharpe:                  {np.max(sharpes):.4f}")
    print(f"Min Sharpe:                  {np.min(sharpes):.4f}")
    print()


def print_top_n(ranked: List[dict], n: int) -> None:
    """Print top-N parameter sets comparison table."""
    top = ranked[:n]
    if not top:
        print("No feasible parameter sets found.")
        return

    print(f"Top {min(n, len(top))} Parameter Sets (by Sharpe)")
    print("=" * 60)

    # Header
    header = f"{'Rank':>4}  {'Sharpe':>8}  {'MaxDD%':>7}  {'Return%':>8}  {'Trades':>6}"
    print(header)
    print("-" * len(header))

    for i, entry in enumerate(top, 1):
        sharpe = entry.get("sharpe", 0)
        max_dd = entry.get("max_drawdown", 0) * 100
        ret = entry.get("total_return_pct", 0)
        trades = entry.get("total_trades", 0)
        print(f"{i:>4}  {sharpe:>8.4f}  {max_dd:>6.2f}%  {ret:>+7.2f}%  {trades:>6}")

    # Print params for each
    print()
    print("Parameters:")
    print("-" * 60)
    for i, entry in enumerate(top, 1):
        params = entry.get("params", {})
        param_str = ", ".join(
            f"{k}={v}" for k, v in sorted(params.items()) if k in PARAM_NAMES
        )
        print(f"  #{i}: {param_str}")

    print()


def print_param_importance(correlations: Dict[str, float]) -> None:
    """Print parameter importance ranking (by absolute correlation with Sharpe)."""
    if not correlations:
        print("Insufficient data for parameter sensitivity analysis.")
        return

    print("Parameter Importance (|correlation| with Sharpe)")
    print("=" * 60)

    ranked = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)

    header = f"{'Rank':>4}  {'Parameter':>20}  {'Corr':>8}  {'|Corr|':>8}"
    print(header)
    print("-" * len(header))

    for i, (name, corr) in enumerate(ranked, 1):
        print(f"{i:>4}  {name:>20}  {corr:>+8.4f}  {abs(corr):>8.4f}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Analyze MRBB optimization results")
    parser.add_argument(
        "--dir", default=DEFAULT_RESULTS_DIR,
        help=f"Results directory (default: {DEFAULT_RESULTS_DIR})"
    )
    parser.add_argument(
        "--max-dd", type=float, default=DEFAULT_MAX_DD,
        help=f"Max drawdown constraint (default: {DEFAULT_MAX_DD})"
    )
    parser.add_argument(
        "--top", type=int, default=DEFAULT_TOP_N,
        help=f"Number of top parameter sets to show (default: {DEFAULT_TOP_N})"
    )
    args = parser.parse_args()

    # Load all results
    all_entries = load_results(args.dir)
    print(f"Loaded {len(all_entries)} results from {args.dir}\n")

    # Filter by DD constraint
    feasible = filter_feasible(all_entries, args.max_dd)

    # Summary stats
    print_summary_stats(all_entries, feasible)

    # Rank feasible by Sharpe
    ranked = rank_by_sharpe(feasible)

    # Top-N table
    print_top_n(ranked, args.top)

    # Parameter sensitivity
    correlations = compute_param_sensitivity(all_entries)
    print_param_importance(correlations)


if __name__ == "__main__":
    main()
