#!/usr/bin/env python3
"""
Run backtests across multiple timeranges and save organized results.

Usage:
    python scripts/run_backtests.py --strategy BTCMomentumScalper --label optimized_30d
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def run_backtest(config_path: str, strategy: str, strategy_path: str, timerange: str) -> dict:
    """Run a single backtest and return results."""
    cmd = [
        ".venv/bin/freqtrade", "backtesting",
        "-c", config_path,
        "--strategy", strategy,
        "--strategy-path", strategy_path,
        "--timerange", timerange,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse key metrics from output
    output = result.stdout + result.stderr

    metrics = {
        "timerange": timerange,
        "raw_output": output,
    }

    # Extract metrics from STRATEGY SUMMARY table
    lines = output.split("\n")
    for i, line in enumerate(lines):
        if "STRATEGY SUMMARY" in line:
            # Find the data row (after the header row)
            for j in range(i+1, min(i+10, len(lines))):
                if "BTCMomentumScalper" in lines[j]:
                    parts = lines[j].split("│")
                    if len(parts) >= 8:
                        metrics["trades"] = parts[2].strip()
                        metrics["avg_profit_pct"] = parts[3].strip()
                        metrics["total_profit_usdt"] = parts[4].strip()
                        metrics["total_profit_pct"] = parts[5].strip()
                        metrics["avg_duration"] = parts[6].strip()
                        metrics["win_draw_loss"] = parts[7].strip()
                        metrics["drawdown"] = parts[8].strip() if len(parts) > 8 else "N/A"
                    break

        if "Market change" in line:
            parts = line.split("│")
            if len(parts) >= 2:
                metrics["market_change"] = parts[2].strip()

    return metrics


def generate_summary(results: list, output_dir: Path, label: str) -> str:
    """Generate a markdown summary of backtest results."""
    summary = f"""# Backtest Results: {label}

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary Table

| Timerange | Trades | Total Profit | Win/Draw/Loss | Drawdown | Market |
|-----------|--------|--------------|---------------|----------|--------|
"""

    for r in results:
        summary += f"| {r.get('timerange', 'N/A')} | {r.get('trades', 'N/A')} | {r.get('total_profit_pct', 'N/A')} | {r.get('win_draw_loss', 'N/A')} | {r.get('drawdown', 'N/A')} | {r.get('market_change', 'N/A')} |\n"

    summary += """
## Analysis

### Key Observations
- Compare total profit % to market change % to assess strategy performance
- Win rate alone is misleading - check if "draws" (0% profit) dominate
- Drawdown indicates risk - higher drawdown = more risk

### Recommendations
- If strategy underperforms market on longer timeframes, consider re-optimization
- Walk-forward validation: train on older data, test on recent data
- Avoid overfitting by using larger training datasets
"""

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run backtests across multiple timeranges")
    parser.add_argument("--strategy", default="BTCMomentumScalper", help="Strategy name")
    parser.add_argument("--strategy-path", default="strategies/btc_momentum_scalper/", help="Strategy path")
    parser.add_argument("--config", default="config/config.json", help="Config file")
    parser.add_argument("--label", required=True, help="Label for this test run (e.g., optimized_30d)")
    parser.add_argument("--output-dir", default="backtests", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) / args.strategy.lower() / args.label
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    # Define timeranges
    timeranges = {
        "all_data_1yr": "20250202-20260203",
        "last_90d": "20251106-20260203",
        "last_60d": "20251205-20260203",
        "last_30d": "20260104-20260203",
    }

    results = []

    for name, timerange in timeranges.items():
        print(f"\n{'='*60}")
        print(f"Running backtest: {name} ({timerange})")
        print('='*60)

        metrics = run_backtest(args.config, args.strategy, args.strategy_path, timerange)
        metrics["name"] = name
        results.append(metrics)

        # Save raw results
        raw_file = raw_dir / f"{name}.json"
        with open(raw_file, "w") as f:
            json.dump(metrics, f, indent=2, default=str)

        print(f"  Trades: {metrics.get('trades', 'N/A')}")
        print(f"  Profit: {metrics.get('total_profit_pct', 'N/A')}")
        print(f"  Win/Draw/Loss: {metrics.get('win_draw_loss', 'N/A')}")

    # Generate summary
    summary = generate_summary(results, output_dir, args.label)
    summary_file = output_dir / "results.md"
    with open(summary_file, "w") as f:
        f.write(summary)

    print(f"\n{'='*60}")
    print(f"Results saved to: {output_dir}")
    print(f"Summary: {summary_file}")
    print('='*60)

    # Also save combined results JSON
    combined_file = output_dir / "all_results.json"
    with open(combined_file, "w") as f:
        # Remove raw_output for combined file (too verbose)
        clean_results = [{k: v for k, v in r.items() if k != "raw_output"} for r in results]
        json.dump(clean_results, f, indent=2)


if __name__ == "__main__":
    main()
