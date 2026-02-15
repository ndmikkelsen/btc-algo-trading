"""Statistical significance tests for backtest validation.

Implements methods to guard against overfitting and multiple testing bias:
- Deflated Sharpe Ratio (de Prado, 2014)
- White's Reality Check (White, 2000)
- t-statistic for mean return
- Minimum backtest length estimation

References:
- de Prado (2014) "The Deflated Sharpe Ratio"
- White (2000) "A Reality Check for Data Snooping"
- Bailey & de Prado (2012) "The Sharpe Ratio Efficient Frontier"
"""

import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Optional


@dataclass
class SharpeResult:
    """Result of a Sharpe ratio significance test."""
    sharpe: float
    t_stat: float
    p_value: float
    n_obs: int


@dataclass
class DSRResult:
    """Result of Deflated Sharpe Ratio test."""
    observed_sharpe: float
    deflated_sharpe: float
    p_value: float
    n_trials: int
    is_significant: bool


@dataclass
class RealityCheckResult:
    """Result of White's Reality Check."""
    observed_max_return: float
    p_value: float
    n_strategies: int
    n_bootstraps: int
    is_significant: bool


def sharpe_t_stat(returns: np.ndarray) -> SharpeResult:
    """Compute t-statistic and p-value for the Sharpe ratio.

    Tests H0: mean return = 0.

    Args:
        returns: Array of period returns.

    Returns:
        SharpeResult with Sharpe, t-stat, and two-sided p-value.
    """
    n = len(returns)
    if n < 2:
        raise ValueError("Need at least 2 observations")

    mean_r = np.mean(returns)
    std_r = np.std(returns, ddof=1)

    if std_r == 0:
        raise ValueError("Zero standard deviation in returns")

    sharpe = mean_r / std_r
    t = mean_r / (std_r / np.sqrt(n))
    p_value = 2.0 * (1.0 - stats.t.cdf(abs(t), df=n - 1))

    return SharpeResult(sharpe=sharpe, t_stat=t, p_value=p_value, n_obs=n)


def deflated_sharpe_ratio(
    observed_sr: float,
    n_trials: int,
    returns: np.ndarray,
    sr_benchmark: float = 0.0,
    alpha: float = 0.05,
) -> DSRResult:
    """Deflated Sharpe Ratio adjusting for multiple testing.

    Adjusts the observed Sharpe ratio for the number of strategy variations
    tested, accounting for skewness and kurtosis of the return distribution.

    Based on de Prado (2014): the expected maximum Sharpe from n_trials
    independent strategies under the null is approximated via the
    Euler-Mascheroni correction.

    Args:
        observed_sr: Observed (annualized or per-period) Sharpe ratio.
        n_trials: Number of strategy variations tested.
        returns: Array of returns used to compute skewness/kurtosis.
        sr_benchmark: Benchmark Sharpe to test against (default 0).
        alpha: Significance level.

    Returns:
        DSRResult with deflated Sharpe and significance flag.
    """
    n = len(returns)
    if n < 3:
        raise ValueError("Need at least 3 observations for skewness/kurtosis")
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")

    skew = float(stats.skew(returns))
    kurt = float(stats.kurtosis(returns, fisher=True))  # excess kurtosis

    # Expected max Sharpe under null (de Prado 2014)
    # E[max(SR)] = SR_benchmark + SE(SR_0) * Z_max
    # where SE(SR_0) = 1/sqrt(n-1) under H0 and
    # Z_max ≈ sqrt(2*log(K)) * (1 - γ/(2*log(K)))
    euler_mascheroni = 0.5772156649
    sr_std_null = 1.0 / np.sqrt(n - 1)  # SE of SR estimator under null

    if n_trials == 1:
        e_max_sr = sr_benchmark
    else:
        z_max = np.sqrt(2.0 * np.log(n_trials)) * (
            1.0 - euler_mascheroni / (2.0 * np.log(n_trials))
        )
        e_max_sr = sr_benchmark + sr_std_null * z_max

    # Variance of Sharpe ratio estimator (Lo, 2002)
    sr_var = (
        1.0
        - skew * observed_sr
        + ((kurt - 1) / 4.0) * observed_sr**2
    ) / (n - 1)

    if sr_var <= 0:
        sr_var = 1e-10  # guard against numerical issues

    sr_std = np.sqrt(sr_var)

    # PSR: probability that observed SR exceeds expected max SR
    z_score = (observed_sr - e_max_sr) / sr_std
    p_value = float(1.0 - stats.norm.cdf(z_score))

    deflated_sr = float(observed_sr - e_max_sr)

    return DSRResult(
        observed_sharpe=observed_sr,
        deflated_sharpe=deflated_sr,
        p_value=p_value,
        n_trials=n_trials,
        is_significant=bool(p_value < alpha),
    )


def whites_reality_check(
    returns_matrix: np.ndarray,
    n_bootstraps: int = 1000,
    alpha: float = 0.05,
    seed: Optional[int] = None,
) -> RealityCheckResult:
    """White's Reality Check for data snooping.

    Tests whether the best strategy's mean return is significantly different
    from zero after accounting for multiple strategies tested.

    Args:
        returns_matrix: (n_periods, n_strategies) array of returns.
        n_bootstraps: Number of bootstrap replications.
        alpha: Significance level.
        seed: Random seed for reproducibility.

    Returns:
        RealityCheckResult with p-value and significance flag.
    """
    if returns_matrix.ndim != 2:
        raise ValueError("returns_matrix must be 2D (n_periods x n_strategies)")

    n_periods, n_strategies = returns_matrix.shape
    rng = np.random.RandomState(seed)

    # Observed test statistic: max mean return across strategies
    observed_means = np.mean(returns_matrix, axis=0)
    observed_max = np.max(observed_means)

    # Center returns under null (subtract each strategy's mean)
    centered = returns_matrix - observed_means

    # Bootstrap
    bootstrap_max_stats = np.empty(n_bootstraps)
    for b in range(n_bootstraps):
        # Resample rows (periods) with replacement
        indices = rng.randint(0, n_periods, size=n_periods)
        boot_sample = centered[indices]
        boot_means = np.mean(boot_sample, axis=0)
        bootstrap_max_stats[b] = np.max(boot_means)

    # p-value: fraction of bootstrap stats >= observed
    p_value = float(np.mean(bootstrap_max_stats >= observed_max))

    return RealityCheckResult(
        observed_max_return=float(observed_max),
        p_value=p_value,
        n_strategies=n_strategies,
        n_bootstraps=n_bootstraps,
        is_significant=bool(p_value < alpha),
    )


def min_backtest_length(
    target_sharpe: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> int:
    """Minimum number of observations for a backtest to detect a given Sharpe.

    Based on the power analysis for a one-sample t-test of mean return.

    n = ((z_alpha + z_beta) / SR)^2

    Args:
        target_sharpe: Per-period Sharpe ratio to detect.
        alpha: Significance level (two-sided).
        power: Statistical power (1 - beta).

    Returns:
        Minimum number of observations (periods).
    """
    if target_sharpe <= 0:
        raise ValueError("target_sharpe must be positive")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be between 0 and 1")
    if not (0 < power < 1):
        raise ValueError("power must be between 0 and 1")

    z_alpha = stats.norm.ppf(1.0 - alpha / 2.0)  # two-sided
    z_beta = stats.norm.ppf(power)

    n = ((z_alpha + z_beta) / target_sharpe) ** 2
    return int(np.ceil(n))
