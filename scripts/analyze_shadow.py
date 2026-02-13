#!/usr/bin/env python3
"""Analyze shadow trading results and compare with backtester predictions.

Loads shadow trading CSV/JSON output and produces a comparison report:
- Theoretical vs actual fill rate
- Effective spread captured
- Regime detection accuracy
- Backtester prediction comparison (when data available)

Usage:
    python scripts/analyze_shadow.py
    python scripts/analyze_shadow.py --file data/shadow_trading/shadow_okx_20260209_120000.csv
    python scripts/analyze_shadow.py --compare-backtest data/okx_btcusdt_1m.csv
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from strategies.avellaneda_stoikov.model import AvellanedaStoikov
from strategies.avellaneda_stoikov.order_manager import OrderManager, OrderSide
from strategies.avellaneda_stoikov.simulator import MarketSimulator
from strategies.avellaneda_stoikov.regime import RegimeDetector


def load_shadow_data(path: Path) -> tuple[pd.DataFrame, dict | None]:
    """Load shadow trading CSV and its companion JSON summary."""
    df = pd.read_csv(path, parse_dates=["timestamp"])
    summary_path = path.with_suffix("").with_name(
        path.stem + "_summary.json"
    )
    # The summary might use a different naming pattern
    possible_summaries = [
        path.parent / (path.stem + "_summary.json"),
        path.parent / (path.stem.replace(".csv", "") + "_summary.json"),
    ]
    summary = None
    for sp in possible_summaries:
        if sp.exists():
            summary = json.loads(sp.read_text())
            break
    return df, summary


def find_latest_shadow(shadow_dir: Path) -> Path | None:
    """Find the most recent shadow trading CSV."""
    csvs = sorted(shadow_dir.glob("shadow_*.csv"), reverse=True)
    return csvs[0] if csvs else None


def analyze_fills(df: pd.DataFrame) -> dict:
    """Analyze fill statistics."""
    total = len(df)
    if total == 0:
        return {}

    # Only consider ticks where quotes were active
    quoted = df[df["bid_quote"].notna() & (df["bid_quote"] != "")]
    quoted_count = len(quoted)

    if quoted_count == 0:
        return {"quoted_ticks": 0, "total_ticks": total}

    bid_fills = (quoted["bid_would_fill"] == True).sum()
    ask_fills = (quoted["ask_would_fill"] == True).sum()
    both_fills = (
        (quoted["bid_would_fill"] == True) & (quoted["ask_would_fill"] == True)
    ).sum()
    neither = (
        (quoted["bid_would_fill"] != True) & (quoted["ask_would_fill"] != True)
    ).sum()

    return {
        "total_ticks": total,
        "quoted_ticks": quoted_count,
        "unquoted_ticks": total - quoted_count,
        "bid_fill_rate": bid_fills / quoted_count * 100,
        "ask_fill_rate": ask_fills / quoted_count * 100,
        "both_fill_rate": both_fills / quoted_count * 100,
        "no_fill_rate": neither / quoted_count * 100,
        "bid_only_rate": (bid_fills - both_fills) / quoted_count * 100,
        "ask_only_rate": (ask_fills - both_fills) / quoted_count * 100,
    }


def analyze_spreads(df: pd.DataFrame) -> dict:
    """Analyze spread statistics."""
    spreads = pd.to_numeric(df["spread_bps"], errors="coerce").dropna()
    spreads = spreads[spreads > 0]

    if len(spreads) == 0:
        return {}

    return {
        "mean_spread_bps": spreads.mean(),
        "median_spread_bps": spreads.median(),
        "min_spread_bps": spreads.min(),
        "max_spread_bps": spreads.max(),
        "std_spread_bps": spreads.std(),
        "p25_spread_bps": spreads.quantile(0.25),
        "p75_spread_bps": spreads.quantile(0.75),
    }


def analyze_regime(df: pd.DataFrame) -> dict:
    """Analyze regime detection statistics."""
    regimes = df["regime"].dropna()
    if len(regimes) == 0:
        return {}

    total = len(regimes)
    counts = regimes.value_counts()

    result = {"total_periods": total}
    for regime, count in counts.items():
        result[f"{regime}_count"] = int(count)
        result[f"{regime}_pct"] = count / total * 100

    adx = pd.to_numeric(df["adx"], errors="coerce").dropna()
    if len(adx) > 0:
        result["adx_mean"] = adx.mean()
        result["adx_median"] = adx.median()
        result["adx_min"] = adx.min()
        result["adx_max"] = adx.max()

    return result


def analyze_pnl(df: pd.DataFrame) -> dict:
    """Analyze P&L progression."""
    pnl = pd.to_numeric(df["total_pnl"], errors="coerce").dropna()
    realized = pd.to_numeric(df["realized_pnl"], errors="coerce").dropna()
    trades = pd.to_numeric(df["trade_count"], errors="coerce").dropna()

    if len(pnl) == 0:
        return {}

    return {
        "final_total_pnl": pnl.iloc[-1],
        "final_realized_pnl": realized.iloc[-1] if len(realized) > 0 else 0,
        "max_pnl": pnl.max(),
        "min_pnl": pnl.min(),
        "max_drawdown_from_peak": pnl.max() - pnl.min(),
        "total_trades": int(trades.iloc[-1]) if len(trades) > 0 else 0,
    }


def analyze_effective_spread(df: pd.DataFrame) -> dict:
    """Estimate effective spread captured vs theoretical spread.

    When both bid and ask fill on the same tick, the effective spread
    captured is (ask_fill_price - bid_fill_price).  We approximate this
    from the quoted spread since we don't track individual fill prices
    in the CSV.
    """
    both_mask = (df["bid_would_fill"] == True) & (df["ask_would_fill"] == True)
    both_ticks = df[both_mask]

    if len(both_ticks) == 0:
        return {"round_trips": 0}

    spread_bps = pd.to_numeric(both_ticks["spread_bps"], errors="coerce").dropna()
    if len(spread_bps) == 0:
        return {"round_trips": 0}

    fee_bps = 10 * 2  # 0.1% maker fee each side = 20 bps round trip
    net_spread = spread_bps - fee_bps

    return {
        "round_trips": len(both_ticks),
        "mean_theoretical_spread_bps": spread_bps.mean(),
        "mean_net_spread_bps": net_spread.mean(),
        "pct_profitable_spreads": (net_spread > 0).mean() * 100,
    }


def run_backtest_comparison(
    shadow_df: pd.DataFrame,
    backtest_data_path: Path,
) -> dict:
    """Run the backtester over the same time period and compare.

    Downloads or reads OHLCV data covering the shadow trading period,
    runs the simulator, and compares results.
    """
    if not backtest_data_path.exists():
        return {"error": f"Backtest data not found: {backtest_data_path}"}

    ohlcv = pd.read_csv(backtest_data_path, parse_dates=["timestamp"])
    ohlcv = ohlcv.set_index("timestamp").sort_index()

    # Determine shadow time range
    shadow_start = pd.to_datetime(shadow_df["timestamp"].iloc[0])
    shadow_end = pd.to_datetime(shadow_df["timestamp"].iloc[-1])

    # Filter OHLCV to overlapping period (with timezone handling)
    if ohlcv.index.tz is None and shadow_start.tzinfo is not None:
        ohlcv.index = ohlcv.index.tz_localize("UTC")
    overlap = ohlcv.loc[shadow_start:shadow_end]

    if len(overlap) < 5:
        return {
            "error": "Insufficient overlapping data between shadow and backtest",
            "shadow_range": f"{shadow_start} to {shadow_end}",
            "data_range": f"{ohlcv.index[0]} to {ohlcv.index[-1]}",
        }

    # Run backtester with same params
    model = AvellanedaStoikov(
        risk_aversion=0.1,
        order_book_liquidity=2.5,
        volatility_window=20,
        min_spread=0.004,
        max_spread=0.03,
    )
    om = OrderManager(initial_cash=0.0, max_inventory=10, maker_fee=0.001)
    sim = MarketSimulator(
        model=model,
        order_manager=om,
        order_size=0.003,
        use_regime_filter=True,
    )
    results = sim.run_backtest(overlap)

    # Compare
    shadow_pnl = analyze_pnl(shadow_df)
    bt_pnl = results["final_pnl"]
    bt_trades = results["total_trades"]

    return {
        "overlap_candles": len(overlap),
        "overlap_range": f"{overlap.index[0]} to {overlap.index[-1]}",
        "shadow_pnl": shadow_pnl.get("final_total_pnl", 0),
        "shadow_trades": shadow_pnl.get("total_trades", 0),
        "backtest_pnl": bt_pnl,
        "backtest_trades": bt_trades,
        "pnl_difference": shadow_pnl.get("final_total_pnl", 0) - bt_pnl,
        "trade_count_difference": shadow_pnl.get("total_trades", 0) - bt_trades,
        "backtest_regime_stats": results.get("regime_stats", {}),
    }


def print_report(
    fills: dict,
    spreads: dict,
    regime: dict,
    pnl: dict,
    effective: dict,
    backtest: dict | None = None,
):
    """Print a formatted analysis report."""
    print(f"\n{'='*70}")
    print(f"  SHADOW TRADING ANALYSIS REPORT")
    print(f"{'='*70}")

    # Fill analysis
    print(f"\n--- Fill Analysis ---")
    if fills:
        print(f"  Total ticks:         {fills.get('total_ticks', 0)}")
        print(f"  Quoted ticks:        {fills.get('quoted_ticks', 0)}")
        print(f"  Unquoted (trending): {fills.get('unquoted_ticks', 0)}")
        print(f"  Bid fill rate:       {fills.get('bid_fill_rate', 0):.1f}%")
        print(f"  Ask fill rate:       {fills.get('ask_fill_rate', 0):.1f}%")
        print(f"  Both-side fill rate: {fills.get('both_fill_rate', 0):.1f}%")
        print(f"  No fill rate:        {fills.get('no_fill_rate', 0):.1f}%")
        print(f"  Bid-only fills:      {fills.get('bid_only_rate', 0):.1f}%")
        print(f"  Ask-only fills:      {fills.get('ask_only_rate', 0):.1f}%")

    # Spread analysis
    print(f"\n--- Spread Analysis ---")
    if spreads:
        print(f"  Mean spread:         {spreads.get('mean_spread_bps', 0):.1f} bps")
        print(f"  Median spread:       {spreads.get('median_spread_bps', 0):.1f} bps")
        print(f"  Spread range:        {spreads.get('min_spread_bps', 0):.1f} - {spreads.get('max_spread_bps', 0):.1f} bps")
        print(f"  25th-75th pctl:      {spreads.get('p25_spread_bps', 0):.1f} - {spreads.get('p75_spread_bps', 0):.1f} bps")

    # Effective spread
    print(f"\n--- Effective Spread (Round-trips) ---")
    if effective:
        print(f"  Round-trip fills:    {effective.get('round_trips', 0)}")
        print(f"  Theoretical spread:  {effective.get('mean_theoretical_spread_bps', 0):.1f} bps")
        print(f"  Net spread (- fees): {effective.get('mean_net_spread_bps', 0):.1f} bps")
        print(f"  % profitable:        {effective.get('pct_profitable_spreads', 0):.1f}%")

    # Regime
    print(f"\n--- Regime Detection ---")
    if regime:
        print(f"  Total periods:       {regime.get('total_periods', 0)}")
        for key in sorted(regime):
            if key.endswith("_pct"):
                name = key.replace("_pct", "")
                print(f"  {name:20s}: {regime[key]:.1f}%")
        if "adx_mean" in regime:
            print(f"  ADX mean:            {regime['adx_mean']:.1f}")
            print(f"  ADX range:           {regime.get('adx_min', 0):.1f} - {regime.get('adx_max', 0):.1f}")

    # P&L
    print(f"\n--- Shadow P&L ---")
    if pnl:
        print(f"  Total P&L:           {pnl.get('final_total_pnl', 0):.4f}")
        print(f"  Realized P&L:        {pnl.get('final_realized_pnl', 0):.4f}")
        print(f"  Max P&L:             {pnl.get('max_pnl', 0):.4f}")
        print(f"  Min P&L:             {pnl.get('min_pnl', 0):.4f}")
        print(f"  Total trades:        {pnl.get('total_trades', 0)}")

    # Backtester comparison
    if backtest:
        print(f"\n--- Backtester Comparison ---")
        if "error" in backtest:
            print(f"  Error: {backtest['error']}")
        else:
            print(f"  Overlap candles:     {backtest.get('overlap_candles', 0)}")
            print(f"  Shadow P&L:          {backtest.get('shadow_pnl', 0):.4f}")
            print(f"  Backtest P&L:        {backtest.get('backtest_pnl', 0):.4f}")
            print(f"  P&L difference:      {backtest.get('pnl_difference', 0):.4f}")
            print(f"  Shadow trades:       {backtest.get('shadow_trades', 0)}")
            print(f"  Backtest trades:     {backtest.get('backtest_trades', 0)}")
            diff = backtest.get("trade_count_difference", 0)
            print(f"  Trade diff:          {diff}")

    print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Analyze shadow trading results")
    parser.add_argument(
        "--file", type=str, default=None,
        help="Path to shadow CSV (default: latest in data/shadow_trading/)",
    )
    parser.add_argument(
        "--compare-backtest", type=str, default=None,
        help="Path to OHLCV CSV for backtester comparison",
    )
    args = parser.parse_args()

    shadow_dir = Path("data/shadow_trading")

    if args.file:
        csv_path = Path(args.file)
    else:
        csv_path = find_latest_shadow(shadow_dir)
        if csv_path is None:
            print("No shadow trading data found in data/shadow_trading/")
            print("Run scripts/run_shadow_trader.py first.")
            sys.exit(1)

    print(f"Analyzing: {csv_path}")
    df, summary = load_shadow_data(csv_path)

    fills = analyze_fills(df)
    spreads = analyze_spreads(df)
    regime = analyze_regime(df)
    pnl = analyze_pnl(df)
    effective = analyze_effective_spread(df)

    backtest = None
    if args.compare_backtest:
        backtest = run_backtest_comparison(df, Path(args.compare_backtest))

    print_report(fills, spreads, regime, pnl, effective, backtest)


if __name__ == "__main__":
    main()
