#!/usr/bin/env python3
"""
Log backtest results to the knowledge base.

This script runs a backtest and generates a markdown finding report
that can be synced to Cognee for future querying.

Usage:
    python scripts/log_backtest.py --strategy MACDBB --notes "Initial test"
    python scripts/log_backtest.py --strategy MACDBB --timerange 20250601-20260101
"""

import argparse
import json
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


def run_backtest(strategy: str, config: str, datadir: str, timerange: str = None) -> dict:
    """Run freqtrade backtest and return parsed results."""
    cmd = [
        sys.executable, "-m", "freqtrade", "backtesting",
        "-c", config,
        "--strategy", strategy,
        "--datadir", datadir,
        "--export", "signals",
    ]

    if timerange:
        cmd.extend(["--timerange", timerange])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Backtest failed:\n{result.stderr}")
        return None

    # Parse the latest result file
    results_dir = Path("user_data/backtest_results")
    result_files = sorted(results_dir.glob("backtest-result-*.json"), reverse=True)

    if not result_files:
        print("No result files found")
        return None

    # Find the non-meta result file
    for rf in result_files:
        if ".meta." not in rf.name:
            with open(rf) as f:
                return json.load(f)

    return None


def extract_metrics(results: dict, strategy: str) -> dict:
    """Extract key metrics from backtest results."""
    if not results or "strategy" not in results:
        return {}

    strat_data = results["strategy"].get(strategy, {})

    return {
        "total_trades": strat_data.get("total_trades", 0),
        "win_rate": strat_data.get("wins", 0) / max(strat_data.get("total_trades", 1), 1) * 100,
        "profit_total": strat_data.get("profit_total", 0),
        "profit_total_abs": strat_data.get("profit_total_abs", 0),
        "max_drawdown": strat_data.get("max_drawdown", 0),
        "max_drawdown_abs": strat_data.get("max_drawdown_abs", 0),
        "sharpe": strat_data.get("sharpe", 0),
        "sortino": strat_data.get("sortino", 0),
        "profit_factor": strat_data.get("profit_factor", 0),
        "avg_duration": strat_data.get("holding_avg_s", 0) / 3600,  # Convert to hours
        "wins": strat_data.get("wins", 0),
        "losses": strat_data.get("losses", 0),
        "backtest_start": strat_data.get("backtest_start", ""),
        "backtest_end": strat_data.get("backtest_end", ""),
        "market_change": strat_data.get("market_change", 0),
        "stake_currency": strat_data.get("stake_currency", "USDT"),
    }


def generate_finding_report(
    strategy: str,
    metrics: dict,
    notes: str = "",
    config_snapshot: dict = None,
    tags: list = None,
) -> str:
    """Generate a markdown finding report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_slug = datetime.now().strftime("%Y-%m-%d")

    tags = tags or ["backtest", strategy.lower()]
    tags_str = ", ".join(f"`{t}`" for t in tags)

    # Determine outcome
    profit_pct = metrics.get("profit_total", 0) * 100
    market_change = metrics.get("market_change", 0) * 100
    outperformance = profit_pct - market_change

    if profit_pct > 0:
        outcome = "profitable"
    elif outperformance > 0:
        outcome = "outperformed-market"
    else:
        outcome = "underperformed"

    report = f"""# Backtest Finding: {strategy} ({date_slug})

**Date**: {timestamp}
**Strategy**: {strategy}
**Tags**: {tags_str}
**Outcome**: {outcome}

## Summary

| Metric | Value |
|--------|-------|
| Period | {metrics.get('backtest_start', 'N/A')} to {metrics.get('backtest_end', 'N/A')} |
| Total Trades | {metrics.get('total_trades', 0)} |
| Win Rate | {metrics.get('win_rate', 0):.1f}% |
| Total Profit | {profit_pct:.2f}% ({metrics.get('profit_total_abs', 0):.2f} {metrics.get('stake_currency', 'USDT')}) |
| Market Change | {market_change:.2f}% |
| Outperformance | {outperformance:+.2f}% |
| Max Drawdown | {metrics.get('max_drawdown', 0) * 100:.2f}% |
| Sharpe Ratio | {metrics.get('sharpe', 0):.2f} |
| Sortino Ratio | {metrics.get('sortino', 0):.2f} |
| Profit Factor | {metrics.get('profit_factor', 0):.2f} |
| Avg Duration | {metrics.get('avg_duration', 0):.1f} hours |
| Wins / Losses | {metrics.get('wins', 0)} / {metrics.get('losses', 0)} |

## Analysis

"""

    # Add automated analysis
    if metrics.get('win_rate', 0) >= 60:
        report += f"- **Strong win rate** ({metrics.get('win_rate', 0):.1f}%) indicates reliable entry signals\n"
    elif metrics.get('win_rate', 0) >= 50:
        report += f"- **Moderate win rate** ({metrics.get('win_rate', 0):.1f}%) - entries are okay but could improve\n"
    else:
        report += f"- **Low win rate** ({metrics.get('win_rate', 0):.1f}%) - entry conditions need refinement\n"

    if metrics.get('profit_factor', 0) >= 1.5:
        report += f"- **Good profit factor** ({metrics.get('profit_factor', 0):.2f}) - wins outweigh losses\n"
    elif metrics.get('profit_factor', 0) >= 1.0:
        report += f"- **Break-even profit factor** ({metrics.get('profit_factor', 0):.2f}) - marginal edge\n"
    else:
        report += f"- **Negative profit factor** ({metrics.get('profit_factor', 0):.2f}) - losses exceed wins\n"

    if outperformance > 0:
        report += f"- **Outperformed buy-and-hold** by {outperformance:.2f}%\n"
    else:
        report += f"- **Underperformed buy-and-hold** by {abs(outperformance):.2f}%\n"

    if metrics.get('max_drawdown', 0) * 100 > 10:
        report += f"- **High drawdown** ({metrics.get('max_drawdown', 0) * 100:.2f}%) - risk management needs improvement\n"
    else:
        report += f"- **Acceptable drawdown** ({metrics.get('max_drawdown', 0) * 100:.2f}%)\n"

    # Add notes if provided
    if notes:
        report += f"""
## Notes

{notes}
"""

    # Add config snapshot if provided
    if config_snapshot:
        report += f"""
## Configuration

```json
{json.dumps(config_snapshot, indent=2)}
```
"""

    report += f"""
## Lessons Learned

<!-- Add your key takeaways here -->

1.
2.
3.

## Next Steps

<!-- What to try next based on these results -->

- [ ]
- [ ]
- [ ]

---
*Generated by log_backtest.py*
"""

    return report


def save_finding(report: str, strategy: str) -> Path:
    """Save the finding report to backtests/findings/."""
    findings_dir = Path("backtests/findings")
    findings_dir.mkdir(parents=True, exist_ok=True)

    date_slug = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"{date_slug}_{strategy.lower()}.md"
    filepath = findings_dir / filename

    with open(filepath, "w") as f:
        f.write(report)

    print(f"Finding saved to: {filepath}")
    return filepath


def get_strategy_config(strategy: str) -> dict:
    """Get current strategy configuration for snapshot."""
    import importlib.util

    try:
        # Try to import strategy config dynamically
        if strategy == "MACDBB":
            config_path = Path("strategies/macd_bb/config.py")
            if config_path.exists():
                spec = importlib.util.spec_from_file_location("config", config_path)
                config = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config)
                return {
                    "MACD_FAST": config.MACD_FAST,
                    "MACD_SLOW": config.MACD_SLOW,
                    "MACD_SIGNAL": config.MACD_SIGNAL,
                    "BB_PERIOD": config.BB_PERIOD,
                    "BB_STD": config.BB_STD,
                    "BB_NEAR_THRESHOLD": config.BB_NEAR_THRESHOLD,
                    "BB_LOOKBACK": config.BB_LOOKBACK,
                    "EXIT_ON_UPPER_BB": config.EXIT_ON_UPPER_BB,
                    "STOPLOSS": config.STOPLOSS,
                    "TRAILING_STOP": config.TRAILING_STOP,
                    "TRAILING_STOP_POSITIVE": config.TRAILING_STOP_POSITIVE,
                    "TRAILING_STOP_POSITIVE_OFFSET": config.TRAILING_STOP_POSITIVE_OFFSET,
                }
    except Exception as e:
        print(f"Could not load strategy config: {e}")

    return {}


def main():
    parser = argparse.ArgumentParser(description="Log backtest results to knowledge base")
    parser.add_argument("--strategy", "-s", required=True, help="Strategy name")
    parser.add_argument("--config", "-c", default="config/config.json", help="Config file")
    parser.add_argument("--datadir", "-d", default="user_data/data", help="Data directory")
    parser.add_argument("--timerange", "-t", help="Timerange (e.g., 20250601-20260101)")
    parser.add_argument("--notes", "-n", default="", help="Notes about this backtest")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--no-run", action="store_true", help="Don't run backtest, use latest result")
    parser.add_argument("--sync", action="store_true", help="Sync to Cognee after saving")

    args = parser.parse_args()

    # Run backtest or use latest results
    results = None
    if not args.no_run:
        results = run_backtest(args.strategy, args.config, args.datadir, args.timerange)
    else:
        # Load latest result from zip file
        results_dir = Path("user_data/backtest_results")

        # First try to find zip files (newer format)
        result_files = sorted(results_dir.glob("backtest-result-*.zip"), reverse=True)
        for rf in result_files:
            try:
                with zipfile.ZipFile(rf) as zf:
                    # Find the JSON file inside
                    json_files = [n for n in zf.namelist() if n.endswith(".json") and "_config" not in n]
                    if json_files:
                        with zf.open(json_files[0]) as jf:
                            results = json.load(jf)
                        print(f"Loaded results from: {rf}")
                        break
            except Exception as e:
                print(f"Error reading {rf}: {e}")
                continue

        # Fall back to plain JSON files
        if results is None:
            result_files = sorted(results_dir.glob("backtest-result-*.json"), reverse=True)
            for rf in result_files:
                if ".meta." not in rf.name:
                    with open(rf) as f:
                        results = json.load(f)
                    print(f"Loaded results from: {rf}")
                    break

    if results is None:
        print("No backtest results to log")
        sys.exit(1)

    # Extract metrics
    metrics = extract_metrics(results, args.strategy)

    if not metrics:
        print(f"Could not extract metrics for strategy: {args.strategy}")
        sys.exit(1)

    # Get config snapshot
    config_snapshot = get_strategy_config(args.strategy)

    # Parse tags
    tags = args.tags.split(",") if args.tags else None

    # Generate report
    report = generate_finding_report(
        strategy=args.strategy,
        metrics=metrics,
        notes=args.notes,
        config_snapshot=config_snapshot,
        tags=tags,
    )

    # Save finding
    filepath = save_finding(report, args.strategy)

    # Sync to Cognee if requested
    if args.sync:
        print("Syncing to Cognee...")
        subprocess.run([
            ".claude/scripts/sync-to-cognee.sh",
            "backtests"
        ])

    print(f"\nBacktest logged successfully!")
    print(f"View finding: {filepath}")
    print(f"Query in Cognee: /query 'What were the results of {args.strategy} backtest?'")


if __name__ == "__main__":
    main()
