#!/usr/bin/env python3
"""Backtest runner for Mean Reversion Bollinger Band strategy.

Usage:
    python scripts/run_mrbb_backtest.py --data data/btcusdt_5m.csv
    python scripts/run_mrbb_backtest.py --data data/btcusdt_5m.csv --bb-period 30 --bb-std 2.5
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.simulator import DirectionalSimulator
from strategies.mean_reversion_bb.config import (
    BB_PERIOD,
    BB_STD_DEV,
    BB_INNER_STD_DEV,
    VWAP_PERIOD,
    KC_PERIOD,
    KC_ATR_MULTIPLIER,
    RSI_PERIOD,
    ADX_PERIOD,
    ADX_THRESHOLD,
    USE_REGIME_FILTER,
)
from strategies.avellaneda_stoikov.metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
)


# 5-minute candles per year: 365.25 * 24 * 12
PERIODS_PER_YEAR_5M = 105_120

OUTPUT_DIR = Path("backtests/mrbb")


def load_data(data_path: str) -> pd.DataFrame:
    """Load OHLCV CSV data."""
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

    # Handle both Unix ms timestamps and ISO datetime strings
    ts = df["timestamp"]
    if pd.api.types.is_numeric_dtype(ts):
        df["timestamp"] = pd.to_datetime(ts, unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(ts)

    df = df.set_index("timestamp")
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
        "win_rate": len(wins) / len(trade_log) if trade_log else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
        "avg_pnl": avg_pnl,
    }


def run_backtest(
    df: pd.DataFrame,
    initial_equity: float = 10_000.0,
    bb_period: int = BB_PERIOD,
    bb_std_dev: float = BB_STD_DEV,
    bb_inner_std_dev: float = BB_INNER_STD_DEV,
    vwap_period: int = VWAP_PERIOD,
    kc_period: int = KC_PERIOD,
    kc_atr_multiplier: float = KC_ATR_MULTIPLIER,
    rsi_period: int = RSI_PERIOD,
    adx_period: int = ADX_PERIOD,
    adx_threshold: float = ADX_THRESHOLD,
    use_regime_filter: bool = USE_REGIME_FILTER,
    slippage_pct: float = 0.0005,
    random_seed: int = 42,
    verbose: bool = True,
    **extra_model_kwargs,
) -> dict:
    """Run the MRBB backtest and return results."""
    model = MeanReversionBB(
        bb_period=bb_period,
        bb_std_dev=bb_std_dev,
        bb_inner_std_dev=bb_inner_std_dev,
        vwap_period=vwap_period,
        kc_period=kc_period,
        kc_atr_multiplier=kc_atr_multiplier,
        rsi_period=rsi_period,
        adx_period=adx_period,
        adx_threshold=adx_threshold,
        use_regime_filter=use_regime_filter,
        **extra_model_kwargs,
    )

    sim = DirectionalSimulator(
        model=model,
        initial_equity=initial_equity,
        slippage_pct=slippage_pct,
        random_seed=random_seed,
    )

    if verbose:
        print("Mean Reversion Bollinger Band Backtest")
        print("=" * 50)
        print(f"Data: {len(df)} candles from {df.index[0]} to {df.index[-1]}")
        print(f"Initial equity: ${initial_equity:,.2f}")
        print(f"BB: period={bb_period}, std={bb_std_dev}, inner={bb_inner_std_dev}")
        print(f"VWAP period: {vwap_period}")
        print(f"KC: period={kc_period}, ATR mult={kc_atr_multiplier}")
        print(f"RSI period: {rsi_period}")
        print(f"ADX: period={adx_period}, threshold={adx_threshold}, filter={'ON' if use_regime_filter else 'OFF'}")
        print(f"Slippage: {slippage_pct * 100:.2f}%")
        print()

    results = sim.run_backtest_fast(df)

    # Performance metrics from equity curve
    ec = results["equity_curve"]
    sr = sharpe_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    so = sortino_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    dd = max_drawdown(ec)
    cr = calmar_ratio(ec, periods_per_year=PERIODS_PER_YEAR_5M)
    ts = compute_trade_stats(results["trade_log"])

    stats = {
        "initial_equity": initial_equity,
        "final_equity": results["final_equity"],
        "total_return_pct": results["total_return_pct"],
        "sharpe_ratio": sr,
        "sortino_ratio": so,
        "max_drawdown_pct": dd["max_drawdown_pct"],
        "calmar_ratio": cr,
        "win_rate": ts["win_rate"],
        "profit_factor": ts["profit_factor"],
        "avg_trade_pnl": ts["avg_pnl"],
        "total_trades": results["total_trades"],
        "params": {
            "bb_period": bb_period,
            "bb_std_dev": bb_std_dev,
            "bb_inner_std_dev": bb_inner_std_dev,
            "vwap_period": vwap_period,
            "kc_period": kc_period,
            "kc_atr_multiplier": kc_atr_multiplier,
            "rsi_period": rsi_period,
            "adx_period": adx_period,
            "adx_threshold": adx_threshold,
            "use_regime_filter": use_regime_filter,
            "slippage_pct": slippage_pct,
        },
    }

    if verbose:
        print("Results")
        print("-" * 50)
        print(f"Final Equity:    ${results['final_equity']:,.2f}")
        print(f"Total Return:    {results['total_return_pct']:+.2f}%")
        print(f"Max Drawdown:    {dd['max_drawdown_pct']:.2f}%")
        print()
        print("Risk Metrics")
        print("-" * 50)
        print(f"Sharpe Ratio:    {sr:.2f}" if sr != float("inf") else "Sharpe Ratio:    inf")
        print(f"Sortino Ratio:   {so:.2f}" if so != float("inf") else "Sortino Ratio:   inf")
        print(f"Calmar Ratio:    {cr:.2f}")
        print()
        print("Trade Statistics")
        print("-" * 50)
        print(f"Total Trades:    {results['total_trades']}")
        print(f"Win Rate:        {ts['win_rate'] * 100:.1f}%")
        pf = ts["profit_factor"]
        print(f"Profit Factor:   {pf:.2f}" if pf != float("inf") else "Profit Factor:   inf")
        print(f"Avg Trade P&L:   ${ts['avg_pnl']:,.2f}")

    return {
        "stats": stats,
        "equity_curve": ec,
        "trade_log": results["trade_log"],
    }


def save_results(results: dict, output_dir: Path) -> None:
    """Save backtest results to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Summary stats JSON
    stats_path = output_dir / "summary.json"

    def _serialize(obj):
        if isinstance(obj, float) and (obj == float("inf") or obj == float("-inf")):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(stats_path, "w") as f:
        json.dump(results["stats"], f, indent=2, default=_serialize)
    print(f"\nSaved summary:     {stats_path}")

    # Trade log CSV
    if results["trade_log"]:
        trades_df = pd.DataFrame(results["trade_log"])
        trades_path = output_dir / "trades.csv"
        trades_df.to_csv(trades_path, index=False)
        print(f"Saved trade log:   {trades_path}")

    # Equity curve CSV
    eq_df = pd.DataFrame(results["equity_curve"])
    eq_path = output_dir / "equity_curve.csv"
    eq_df.to_csv(eq_path, index=False)
    print(f"Saved equity curve: {eq_path}")


def main():
    parser = argparse.ArgumentParser(description="Run MRBB backtest")
    parser.add_argument("--data", required=True, help="Path to OHLCV CSV file")
    parser.add_argument("--preset", default=None, help="Named preset to load (CLI args override preset values)")
    parser.add_argument("--equity", type=float, default=10_000.0, help="Initial equity")
    parser.add_argument("--bb-period", type=int, default=BB_PERIOD)
    parser.add_argument("--bb-std", type=float, default=BB_STD_DEV)
    parser.add_argument("--bb-inner-std", type=float, default=BB_INNER_STD_DEV)
    parser.add_argument("--vwap-period", type=int, default=VWAP_PERIOD)
    parser.add_argument("--kc-period", type=int, default=KC_PERIOD)
    parser.add_argument("--kc-atr-mult", type=float, default=KC_ATR_MULTIPLIER)
    parser.add_argument("--rsi-period", type=int, default=RSI_PERIOD)
    parser.add_argument("--adx-period", type=int, default=ADX_PERIOD)
    parser.add_argument("--adx-threshold", type=float, default=ADX_THRESHOLD)
    parser.add_argument("--no-regime-filter", action="store_true",
                        help="Disable ADX regime filter")
    parser.add_argument("--slippage", type=float, default=0.0005, help="Slippage fraction")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", default=None, help="Output directory (default: backtests/mrbb/)")
    parser.add_argument("--quiet", "-q", action="store_true")
    parser.add_argument("--days", type=int, default=None, help="Limit to last N days")

    args = parser.parse_args()

    # Load preset defaults (CLI args still take priority)
    if args.preset:
        from strategies.mean_reversion_bb.presets import PresetManager
        pm = PresetManager()
        preset = pm.load(args.preset)
        _PRESET_MAP = {
            "bb_period": "bb_period",
            "bb_std_dev": "bb_std",
            "bb_inner_std_dev": "bb_inner_std",
            "vwap_period": "vwap_period",
            "kc_period": "kc_period",
            "kc_atr_multiplier": "kc_atr_mult",
            "rsi_period": "rsi_period",
            "adx_period": "adx_period",
            "adx_threshold": "adx_threshold",
        }
        for preset_key, arg_dest in _PRESET_MAP.items():
            if preset_key in preset and getattr(args, arg_dest) == parser.get_default(arg_dest):
                setattr(args, arg_dest, preset[preset_key])
        if preset.get("use_regime_filter") is False and not args.no_regime_filter:
            args.no_regime_filter = True
        # Collect extra model params from preset (new toggles, thresholds)
        _EXTRA_MODEL_KEYS = [
            "rsi_oversold", "rsi_overbought", "vwap_confirmation_pct",
            "stop_atr_multiplier", "reversion_target", "max_holding_bars",
            "risk_per_trade", "max_position_pct", "side_filter",
            "use_squeeze_filter", "use_band_walking_exit",
            "short_bb_std_dev", "short_rsi_threshold",
            "short_max_holding_bars", "short_position_pct",
            "use_trend_filter", "trend_ema_period",
        ]
        extra_model_kwargs = {k: preset[k] for k in _EXTRA_MODEL_KEYS if k in preset}
        if not args.quiet:
            print(f"Loaded preset: {args.preset}")
    else:
        extra_model_kwargs = {}

    df = load_data(args.data)
    if args.days:
        candles_per_day = 24 * 12  # 5m candles
        df = df.tail(args.days * candles_per_day)

    results = run_backtest(
        df=df,
        initial_equity=args.equity,
        bb_period=args.bb_period,
        bb_std_dev=args.bb_std,
        bb_inner_std_dev=args.bb_inner_std,
        vwap_period=args.vwap_period,
        kc_period=args.kc_period,
        kc_atr_multiplier=args.kc_atr_mult,
        rsi_period=args.rsi_period,
        adx_period=args.adx_period,
        adx_threshold=args.adx_threshold,
        use_regime_filter=not args.no_regime_filter,
        slippage_pct=args.slippage,
        random_seed=args.seed,
        verbose=not args.quiet,
        **extra_model_kwargs,
    )

    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    save_results(results, output_dir)


if __name__ == "__main__":
    main()
