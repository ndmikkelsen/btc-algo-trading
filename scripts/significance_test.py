"""Statistical significance tests for MRBB strategy edge.

Tests two configurations:
1. Current optimized preset (3.0x ATR, gentle decay)
2. Best wide-stop sweep config (5.0x ATR, gentle decay)

For each, runs:
- Bootstrap significance test (H0: Sharpe = 0, 10k resamples)
- Monte Carlo permutation test (shuffle PnL signs/order, 10k trials)
- 95% confidence interval for Sharpe via bootstrap
- Deflated Sharpe Ratio (adjusting for multiple testing)

Results saved to backtests/mrbb/significance/significance_results.json
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.simulator import DirectionalSimulator
from strategies.mean_reversion_bb.presets import PresetManager
from strategies.mean_reversion_bb.significance import sharpe_t_stat, deflated_sharpe_ratio
from strategies.mean_reversion_bb.monte_carlo import return_bootstrap, trade_shuffle
from strategies.avellaneda_stoikov.metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calculate_returns,
)

PERIODS_PER_YEAR_5M = 105_120
N_BOOTSTRAPS = 10_000
SEED = 42


def load_data() -> pd.DataFrame:
    """Load 5m OHLCV data."""
    csv_path = ROOT / "data" / "btcusdt_5m.csv"
    df = pd.read_csv(csv_path, parse_dates=["timestamp"], index_col="timestamp")
    print(f"Loaded {len(df):,} candles: {df.index[0]} to {df.index[-1]}")
    return df


def build_model(params: dict) -> MeanReversionBB:
    """Build a MeanReversionBB model from a flat param dict."""
    model_kwargs = {}
    # Map preset keys to model constructor args
    model_keys = [
        "bb_period", "bb_std_dev", "bb_inner_std_dev",
        "vwap_period", "vwap_confirmation_pct",
        "kc_period", "kc_atr_multiplier",
        "rsi_period", "rsi_oversold", "rsi_overbought",
        "adx_period", "adx_threshold", "use_regime_filter",
        "reversion_target", "max_holding_bars",
        "risk_per_trade", "max_position_pct",
        "stop_atr_multiplier",
        "stop_decay_phase_1", "stop_decay_phase_2",
        "stop_decay_mult_1", "stop_decay_mult_2",
        "side_filter", "use_squeeze_filter", "use_band_walking_exit",
        "short_bb_std_dev", "short_rsi_threshold",
        "short_max_holding_bars", "short_position_pct",
        "use_trend_filter", "trend_ema_period",
    ]
    for key in model_keys:
        if key in params:
            model_kwargs[key] = params[key]
    return MeanReversionBB(**model_kwargs)


def run_backtest(df: pd.DataFrame, params: dict, label: str) -> dict:
    """Run a backtest and return results + metrics."""
    print(f"\n{'='*60}")
    print(f"Running backtest: {label}")
    print(f"{'='*60}")

    model = build_model(params)
    sim = DirectionalSimulator(
        model=model,
        initial_equity=10_000.0,
        slippage_pct=0.0005,
        random_seed=SEED,
    )

    t0 = time.time()
    results = sim.run_backtest_fast(df)
    elapsed = time.time() - t0

    equity_curve = results["equity_curve"]
    trade_log = results["trade_log"]

    # Compute metrics
    sr = sharpe_ratio(equity_curve, periods_per_year=PERIODS_PER_YEAR_5M)
    so = sortino_ratio(equity_curve, periods_per_year=PERIODS_PER_YEAR_5M)
    dd = max_drawdown(equity_curve)

    print(f"  Trades: {len(trade_log)}")
    print(f"  Final equity: ${results['final_equity']:,.2f}")
    print(f"  Return: {results['total_return_pct']:+.2f}%")
    print(f"  Sharpe: {sr:.3f}")
    print(f"  Sortino: {so:.3f}")
    print(f"  Max DD: {dd['max_drawdown_pct']:.2f}%")
    print(f"  Elapsed: {elapsed:.1f}s")

    return {
        "equity_curve": equity_curve,
        "trade_log": trade_log,
        "metrics": {
            "total_trades": len(trade_log),
            "final_equity": results["final_equity"],
            "total_return_pct": results["total_return_pct"],
            "sharpe": sr,
            "sortino": so,
            "max_drawdown_pct": dd["max_drawdown_pct"],
        },
    }


def bootstrap_sharpe_test(trade_pnls: np.ndarray, n_boot: int, seed: int) -> dict:
    """Bootstrap test: H0 is Sharpe = 0.

    Resamples trade PnLs with replacement, computes per-resample Sharpe,
    p-value = fraction of bootstrap Sharpes <= 0.
    """
    rng = np.random.RandomState(seed)
    n = len(trade_pnls)
    observed_sharpe = np.mean(trade_pnls) / np.std(trade_pnls, ddof=1)

    boot_sharpes = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choice(trade_pnls, size=n, replace=True)
        std = np.std(sample, ddof=1)
        if std == 0:
            boot_sharpes[i] = 0.0
        else:
            boot_sharpes[i] = np.mean(sample) / std

    # One-sided p-value: fraction of bootstrap Sharpes <= 0
    p_value = float(np.mean(boot_sharpes <= 0))

    # 95% CI
    ci_lower = float(np.percentile(boot_sharpes, 2.5))
    ci_upper = float(np.percentile(boot_sharpes, 97.5))

    return {
        "observed_sharpe_per_trade": float(observed_sharpe),
        "bootstrap_mean_sharpe": float(np.mean(boot_sharpes)),
        "p_value": p_value,
        "ci_95_lower": ci_lower,
        "ci_95_upper": ci_upper,
        "n_bootstraps": n_boot,
        "significant_at_05": p_value < 0.05,
        "significant_at_01": p_value < 0.01,
    }


def monte_carlo_permutation(trade_pnls: np.ndarray, n_perms: int, seed: int) -> dict:
    """Monte Carlo permutation test.

    Randomly flips the sign of each trade PnL with 50% probability,
    then computes Sharpe. p-value = fraction producing Sharpe >= observed.
    """
    rng = np.random.RandomState(seed)
    n = len(trade_pnls)
    std = np.std(trade_pnls, ddof=1)
    observed_sharpe = np.mean(trade_pnls) / std if std > 0 else 0.0

    perm_sharpes = np.empty(n_perms)
    for i in range(n_perms):
        # Random sign flip
        signs = rng.choice([-1, 1], size=n)
        perm = trade_pnls * signs
        perm_std = np.std(perm, ddof=1)
        if perm_std == 0:
            perm_sharpes[i] = 0.0
        else:
            perm_sharpes[i] = np.mean(perm) / perm_std

    p_value = float(np.mean(perm_sharpes >= observed_sharpe))

    return {
        "observed_sharpe_per_trade": float(observed_sharpe),
        "p_value": p_value,
        "perm_mean_sharpe": float(np.mean(perm_sharpes)),
        "perm_std_sharpe": float(np.std(perm_sharpes)),
        "n_permutations": n_perms,
        "significant_at_05": p_value < 0.05,
        "significant_at_01": p_value < 0.01,
    }


def run_significance_suite(bt_result: dict, label: str, n_trials: int = 1) -> dict:
    """Run the full significance test suite on a backtest result."""
    equity_curve = bt_result["equity_curve"]
    trade_log = bt_result["trade_log"]
    trade_pnls = np.array([t["pnl"] for t in trade_log])
    returns = calculate_returns(equity_curve).values

    n_trades = len(trade_pnls)
    print(f"\n--- Significance tests: {label} ({n_trades} trades) ---")

    # 1. Sharpe t-stat (from significance.py)
    print("  [1/5] Sharpe t-statistic...")
    tstat_result = sharpe_t_stat(returns)
    print(f"        Sharpe={tstat_result.sharpe:.4f}, t={tstat_result.t_stat:.2f}, p={tstat_result.p_value:.4f}")

    # 2. Bootstrap Sharpe test on trade PnLs
    print("  [2/5] Bootstrap significance (10k resamples)...")
    boot_result = bootstrap_sharpe_test(trade_pnls, N_BOOTSTRAPS, SEED)
    print(f"        p={boot_result['p_value']:.4f}, CI=[{boot_result['ci_95_lower']:.4f}, {boot_result['ci_95_upper']:.4f}]")

    # 3. Monte Carlo permutation test
    print("  [3/5] Monte Carlo permutation (10k trials)...")
    mc_result = monte_carlo_permutation(trade_pnls, N_BOOTSTRAPS, SEED)
    print(f"        p={mc_result['p_value']:.4f}")

    # 4. Sharpe confidence interval via return_bootstrap (from monte_carlo.py)
    print("  [4/5] Return bootstrap CI...")
    ci_result = return_bootstrap(returns, n_bootstraps=N_BOOTSTRAPS, confidence_level=0.95, seed=SEED)
    # Annualize
    ann_factor = np.sqrt(PERIODS_PER_YEAR_5M)
    ann_sharpe = ci_result.observed_sharpe * ann_factor
    ann_ci_lower = ci_result.ci_lower * ann_factor
    ann_ci_upper = ci_result.ci_upper * ann_factor
    print(f"        Annualized Sharpe: {ann_sharpe:.3f} [{ann_ci_lower:.3f}, {ann_ci_upper:.3f}]")

    # 5. Deflated Sharpe Ratio
    print("  [5/5] Deflated Sharpe Ratio...")
    dsr_result = deflated_sharpe_ratio(
        observed_sr=tstat_result.sharpe,
        n_trials=n_trials,
        returns=returns,
        sr_benchmark=0.0,
    )
    print(f"        DSR p={dsr_result.p_value:.4f}, significant={dsr_result.is_significant}")

    # 6. Trade shuffle (path dependency)
    print("  [bonus] Trade shuffle (path dependency)...")
    shuffle_result = trade_shuffle(trade_pnls, n_simulations=N_BOOTSTRAPS, seed=SEED)
    print(f"        Observed DD={shuffle_result.observed_max_dd:.4f}, p={shuffle_result.p_value:.4f}")

    # Trade stats
    wins = sum(1 for t in trade_log if t["pnl"] > 0)
    losses = sum(1 for t in trade_log if t["pnl"] <= 0)
    win_rate = wins / n_trades if n_trades > 0 else 0.0
    avg_win = np.mean([t["pnl"] for t in trade_log if t["pnl"] > 0]) if wins > 0 else 0.0
    avg_loss = np.mean([t["pnl"] for t in trade_log if t["pnl"] <= 0]) if losses > 0 else 0.0

    return {
        "label": label,
        "n_trades": n_trades,
        "win_rate": float(win_rate),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "metrics": bt_result["metrics"],
        "sharpe_tstat": {
            "per_period_sharpe": float(tstat_result.sharpe),
            "t_stat": float(tstat_result.t_stat),
            "p_value": float(tstat_result.p_value),
            "n_obs": tstat_result.n_obs,
        },
        "bootstrap_sharpe": boot_result,
        "monte_carlo_permutation": mc_result,
        "annualized_sharpe_ci": {
            "observed": float(ann_sharpe),
            "ci_95_lower": float(ann_ci_lower),
            "ci_95_upper": float(ann_ci_upper),
            "n_bootstraps": N_BOOTSTRAPS,
        },
        "deflated_sharpe": {
            "observed_sharpe": float(dsr_result.observed_sharpe),
            "deflated_sharpe": float(dsr_result.deflated_sharpe),
            "p_value": float(dsr_result.p_value),
            "n_trials": dsr_result.n_trials,
            "is_significant": dsr_result.is_significant,
        },
        "trade_shuffle": {
            "observed_max_dd": float(shuffle_result.observed_max_dd),
            "mean_max_dd": float(shuffle_result.mean_max_dd),
            "p95_max_dd": float(shuffle_result.percentile_95),
            "p_value": float(shuffle_result.p_value),
        },
    }


def print_verdict(result: dict) -> None:
    """Print clear verdict for a config."""
    label = result["label"]
    sharpe = result["metrics"]["sharpe"]
    boot_p = result["bootstrap_sharpe"]["p_value"]
    mc_p = result["monte_carlo_permutation"]["p_value"]
    tstat_p = result["sharpe_tstat"]["p_value"]
    ci_lo = result["annualized_sharpe_ci"]["ci_95_lower"]
    ci_hi = result["annualized_sharpe_ci"]["ci_95_upper"]

    # Use the most conservative p-value
    max_p = max(boot_p, mc_p, tstat_p)

    print(f"\n{'='*60}")
    print(f"  VERDICT: {label}")
    print(f"{'='*60}")
    print(f"  Annualized Sharpe: {sharpe:.3f}")
    print(f"  95% CI: [{ci_lo:.3f}, {ci_hi:.3f}]")
    print(f"  p-values: t-stat={tstat_p:.4f}, bootstrap={boot_p:.4f}, MC={mc_p:.4f}")
    print(f"  Trades: {result['n_trades']}, Win rate: {result['win_rate']:.1%}")
    print(f"  Avg win: ${result['avg_win']:.2f}, Avg loss: ${result['avg_loss']:.2f}")

    if max_p < 0.01:
        print(f"\n  >>> SIGNIFICANT EDGE (p={max_p:.4f}) <<<")
        print(f"  Strong evidence of strategy edge at 1% significance level")
    elif max_p < 0.05:
        print(f"\n  >>> SIGNIFICANT EDGE (p={max_p:.4f}) <<<")
        print(f"  Evidence of strategy edge at 5% significance level")
    elif max_p < 0.10:
        print(f"\n  >>> MARGINAL EDGE (p={max_p:.4f}) <<<")
        print(f"  Weak evidence; edge not significant at 5% level")
    else:
        print(f"\n  >>> NO SIGNIFICANT EDGE (p={max_p:.4f}) <<<")
        print(f"  Cannot reject null hypothesis of Sharpe = 0")


def main():
    print("MRBB Statistical Significance Analysis")
    print("=" * 60)

    # Load data
    df = load_data()

    # Load optimized preset
    pm = PresetManager()
    opt_params = pm.load("optimized")
    print(f"\nOptimized preset loaded: {opt_params.get('description', '')[:80]}...")

    # Config 1: Current optimized (3.0x gentle decay)
    bt_opt = run_backtest(df, opt_params, "Optimized (3.0x gentle decay)")

    # Config 2: Best sweep config (5.0x ATR gentle decay)
    sweep_overrides = {
        "stop_atr_multiplier": 5.0,
        "stop_decay_mult_1": 4.0,
        "stop_decay_mult_2": 3.25,
        "stop_decay_phase_1": 0.035,
        "stop_decay_phase_2": 0.069,
    }
    sweep_params = pm.load("optimized", overrides=sweep_overrides)
    bt_sweep = run_backtest(df, sweep_params, "Best sweep (5.0x gentle decay)")

    # Run significance tests
    # n_trials: we've tested ~30 configs across sweeps (conservative estimate)
    sig_opt = run_significance_suite(bt_opt, "Optimized (3.0x)", n_trials=30)
    sig_sweep = run_significance_suite(bt_sweep, "Best sweep (5.0x)", n_trials=30)

    # Print verdicts
    print_verdict(sig_opt)
    print_verdict(sig_sweep)

    # Save results
    output = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "data_range": f"{df.index[0]} to {df.index[-1]}",
        "n_candles": len(df),
        "n_bootstraps": N_BOOTSTRAPS,
        "seed": SEED,
        "periods_per_year": PERIODS_PER_YEAR_5M,
        "configs": {
            "optimized_3x": sig_opt,
            "best_sweep_5x": sig_sweep,
        },
    }

    out_path = ROOT / "backtests" / "mrbb" / "significance" / "significance_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
