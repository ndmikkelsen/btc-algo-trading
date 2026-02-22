"""Monte Carlo simulation methods for strategy robustness testing.

Provides three complementary approaches to assess strategy robustness:
1. Trade shuffle - tests if trade ordering matters (path dependency)
2. Return bootstrap - confidence intervals for performance metrics
3. Parameter perturbation - sensitivity to parameter noise

References:
- Pardo (2008) "The Evaluation and Optimization of Trading Strategies"
- Davison & Hinkley (1997) "Bootstrap Methods and their Application"
"""

import numpy as np
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class DrawdownResult:
    """Result of max drawdown analysis across simulations."""
    observed_max_dd: float
    mean_max_dd: float
    median_max_dd: float
    percentile_95: float
    percentile_99: float
    p_value: float  # fraction of sims with worse drawdown than observed
    n_simulations: int


@dataclass
class SharpeCI:
    """Confidence interval for Sharpe ratio via bootstrap."""
    observed_sharpe: float
    mean_sharpe: float
    ci_lower: float
    ci_upper: float
    confidence_level: float
    n_bootstraps: int


@dataclass
class SensitivityResult:
    """Result of parameter perturbation analysis."""
    param_name: str
    base_metric: Optional[float]
    mean_metric: Optional[float]
    std_metric: Optional[float]
    pct_degraded: Optional[float]  # fraction of perturbations that degrade metric
    n_perturbations: int


def _max_drawdown(equity_curve: np.ndarray) -> float:
    """Compute maximum drawdown from an equity curve.

    Args:
        equity_curve: Cumulative equity values (not returns).

    Returns:
        Maximum drawdown as a positive fraction (0 to 1+).
    """
    if len(equity_curve) < 2:
        return 0.0
    peak = np.maximum.accumulate(equity_curve)
    drawdowns = (peak - equity_curve) / np.where(peak > 0, peak, 1.0)
    return float(np.max(drawdowns))


def _equity_from_pnls(pnls: np.ndarray, initial: float = 10000.0) -> np.ndarray:
    """Build equity curve from a sequence of trade P&Ls."""
    return initial + np.cumsum(pnls)


def trade_shuffle(
    trade_pnls: np.ndarray,
    n_simulations: int = 1000,
    initial_equity: float = 10000.0,
    seed: Optional[int] = None,
) -> DrawdownResult:
    """Monte Carlo via trade order shuffling.

    Shuffles the sequence of trade P&Ls to test if the observed drawdown
    is sensitive to trade ordering (path dependency).

    Args:
        trade_pnls: Array of individual trade P&L values.
        n_simulations: Number of shuffle simulations.
        initial_equity: Starting equity for drawdown calculation.
        seed: Random seed for reproducibility.

    Returns:
        DrawdownResult with observed vs simulated drawdown distribution.
    """
    if len(trade_pnls) < 2:
        raise ValueError("Need at least 2 trades")

    rng = np.random.RandomState(seed)

    # Observed drawdown
    equity = _equity_from_pnls(trade_pnls, initial_equity)
    observed_dd = _max_drawdown(equity)

    # Simulate shuffled orderings
    sim_drawdowns = np.empty(n_simulations)
    for i in range(n_simulations):
        shuffled = rng.permutation(trade_pnls)
        sim_equity = _equity_from_pnls(shuffled, initial_equity)
        sim_drawdowns[i] = _max_drawdown(sim_equity)

    # p-value: fraction of sims with drawdown >= observed
    p_value = float(np.mean(sim_drawdowns >= observed_dd))

    return DrawdownResult(
        observed_max_dd=observed_dd,
        mean_max_dd=float(np.mean(sim_drawdowns)),
        median_max_dd=float(np.median(sim_drawdowns)),
        percentile_95=float(np.percentile(sim_drawdowns, 95)),
        percentile_99=float(np.percentile(sim_drawdowns, 99)),
        p_value=p_value,
        n_simulations=n_simulations,
    )


def return_bootstrap(
    returns: np.ndarray,
    n_bootstraps: int = 1000,
    confidence_level: float = 0.95,
    seed: Optional[int] = None,
) -> SharpeCI:
    """Bootstrap confidence interval for the Sharpe ratio.

    Resamples returns with replacement to estimate the sampling
    distribution of the Sharpe ratio.

    Args:
        returns: Array of period returns.
        n_bootstraps: Number of bootstrap replications.
        confidence_level: CI level (e.g., 0.95 for 95% CI).
        seed: Random seed for reproducibility.

    Returns:
        SharpeCI with observed Sharpe and confidence bounds.
    """
    if len(returns) < 2:
        raise ValueError("Need at least 2 return observations")
    if not (0 < confidence_level < 1):
        raise ValueError("confidence_level must be between 0 and 1")

    rng = np.random.RandomState(seed)
    n = len(returns)

    # Observed Sharpe
    observed_sharpe = float(np.mean(returns) / np.std(returns, ddof=1))

    # Bootstrap
    boot_sharpes = np.empty(n_bootstraps)
    for i in range(n_bootstraps):
        sample = rng.choice(returns, size=n, replace=True)
        std = np.std(sample, ddof=1)
        if std == 0:
            boot_sharpes[i] = 0.0
        else:
            boot_sharpes[i] = np.mean(sample) / std

    # Percentile CI
    alpha = 1.0 - confidence_level
    ci_lower = float(np.percentile(boot_sharpes, 100 * alpha / 2))
    ci_upper = float(np.percentile(boot_sharpes, 100 * (1 - alpha / 2)))

    return SharpeCI(
        observed_sharpe=observed_sharpe,
        mean_sharpe=float(np.mean(boot_sharpes)),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        confidence_level=confidence_level,
        n_bootstraps=n_bootstraps,
    )


def parameter_perturbation(
    base_params: dict,
    param_name: str,
    noise_pct: float = 0.10,
    n_perturbations: int = 100,
    evaluate_fn: Optional[Callable[[dict], float]] = None,
    seed: Optional[int] = None,
) -> SensitivityResult:
    """Parameter perturbation for sensitivity analysis.

    Adds Gaussian noise to a single parameter and evaluates
    the impact on a performance metric.

    Args:
        base_params: Dict of parameter name -> value.
        param_name: Which parameter to perturb.
        noise_pct: Noise as fraction of parameter value (e.g., 0.10 = 10%).
        n_perturbations: Number of perturbations to run.
        evaluate_fn: Callable that takes a param dict and returns a metric.
            If None, only generates perturbed param sets (no evaluation).
        seed: Random seed for reproducibility.

    Returns:
        SensitivityResult. If evaluate_fn is None, metric fields are None.
    """
    if param_name not in base_params:
        raise ValueError(f"Parameter '{param_name}' not in base_params")

    base_value = base_params[param_name]
    if not isinstance(base_value, (int, float)):
        raise ValueError(f"Can only perturb numeric parameters, got {type(base_value)}")

    rng = np.random.RandomState(seed)

    if evaluate_fn is None:
        return SensitivityResult(
            param_name=param_name,
            base_metric=None,
            mean_metric=None,
            std_metric=None,
            pct_degraded=None,
            n_perturbations=n_perturbations,
        )

    base_metric = evaluate_fn(base_params)
    metrics = np.empty(n_perturbations)

    for i in range(n_perturbations):
        perturbed = dict(base_params)
        noise = rng.normal(0, noise_pct * abs(base_value))
        perturbed[param_name] = base_value + noise
        metrics[i] = evaluate_fn(perturbed)

    pct_degraded = float(np.mean(metrics < base_metric))

    return SensitivityResult(
        param_name=param_name,
        base_metric=float(base_metric),
        mean_metric=float(np.mean(metrics)),
        std_metric=float(np.std(metrics)),
        pct_degraded=pct_degraded,
        n_perturbations=n_perturbations,
    )
