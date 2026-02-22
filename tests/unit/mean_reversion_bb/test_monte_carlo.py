"""Tests for Monte Carlo simulation module."""

import numpy as np
import pytest

from strategies.mean_reversion_bb.monte_carlo import (
    trade_shuffle,
    return_bootstrap,
    parameter_perturbation,
    _max_drawdown,
    _equity_from_pnls,
)


class TestHelpers:
    """Tests for helper functions."""

    def test_max_drawdown_known(self):
        # Equity: 100, 110, 90, 105 -> peak 110, dd at 90 = 20/110 = 0.1818
        equity = np.array([100.0, 110.0, 90.0, 105.0])
        dd = _max_drawdown(equity)
        assert abs(dd - 20.0 / 110.0) < 1e-10

    def test_max_drawdown_no_drawdown(self):
        equity = np.array([100.0, 110.0, 120.0, 130.0])
        dd = _max_drawdown(equity)
        assert dd == 0.0

    def test_max_drawdown_single_point(self):
        assert _max_drawdown(np.array([100.0])) == 0.0

    def test_equity_from_pnls(self):
        pnls = np.array([100.0, -50.0, 200.0])
        equity = _equity_from_pnls(pnls, initial=10000.0)
        np.testing.assert_array_equal(equity, [10100.0, 10050.0, 10250.0])


class TestTradeShuffle:
    """Tests for trade order shuffling Monte Carlo."""

    def test_basic_output_structure(self):
        rng = np.random.RandomState(42)
        pnls = rng.normal(10, 100, 50)
        result = trade_shuffle(pnls, n_simulations=100, seed=42)
        assert result.n_simulations == 100
        assert result.observed_max_dd >= 0.0
        assert result.mean_max_dd >= 0.0
        assert 0.0 <= result.p_value <= 1.0

    def test_deterministic_with_seed(self):
        pnls = np.array([100, -50, 200, -150, 80, -30, 120, -90])
        r1 = trade_shuffle(pnls, n_simulations=200, seed=123)
        r2 = trade_shuffle(pnls, n_simulations=200, seed=123)
        assert r1.observed_max_dd == r2.observed_max_dd
        assert r1.mean_max_dd == r2.mean_max_dd
        assert r1.p_value == r2.p_value

    def test_all_winning_trades_low_drawdown(self):
        pnls = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        result = trade_shuffle(pnls, n_simulations=200, seed=42)
        # All positive PnLs -> zero drawdown regardless of order
        assert result.observed_max_dd == 0.0
        assert result.mean_max_dd == 0.0

    def test_percentiles_ordered(self):
        rng = np.random.RandomState(42)
        pnls = rng.normal(5, 100, 100)
        result = trade_shuffle(pnls, n_simulations=500, seed=42)
        assert result.median_max_dd <= result.percentile_95
        assert result.percentile_95 <= result.percentile_99

    def test_too_few_trades(self):
        with pytest.raises(ValueError, match="at least 2"):
            trade_shuffle(np.array([100.0]))

    def test_observed_dd_preserved(self):
        """Observed drawdown matches direct calculation."""
        pnls = np.array([100, -200, 50, -100, 300])
        result = trade_shuffle(pnls, n_simulations=10, seed=42)
        equity = 10000.0 + np.cumsum(pnls)
        expected_dd = _max_drawdown(equity)
        assert abs(result.observed_max_dd - expected_dd) < 1e-10


class TestReturnBootstrap:
    """Tests for return bootstrap Sharpe CI."""

    def test_ci_contains_observed(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.001, 0.01, 500)
        result = return_bootstrap(returns, n_bootstraps=1000, seed=42)
        # With 95% CI and enough data, observed should usually be inside
        assert result.ci_lower <= result.observed_sharpe <= result.ci_upper

    def test_ci_width_decreases_with_data(self):
        rng = np.random.RandomState(42)
        small = rng.normal(0.001, 0.01, 50)
        large = rng.normal(0.001, 0.01, 500)
        r_small = return_bootstrap(small, n_bootstraps=500, seed=42)
        r_large = return_bootstrap(large, n_bootstraps=500, seed=42)
        width_small = r_small.ci_upper - r_small.ci_lower
        width_large = r_large.ci_upper - r_large.ci_lower
        assert width_large < width_small

    def test_deterministic_with_seed(self):
        returns = np.random.RandomState(42).normal(0.001, 0.01, 200)
        r1 = return_bootstrap(returns, n_bootstraps=500, seed=123)
        r2 = return_bootstrap(returns, n_bootstraps=500, seed=123)
        assert r1.ci_lower == r2.ci_lower
        assert r1.ci_upper == r2.ci_upper

    def test_confidence_level_stored(self):
        returns = np.random.RandomState(42).normal(0, 0.01, 100)
        result = return_bootstrap(returns, confidence_level=0.99, seed=42)
        assert result.confidence_level == 0.99

    def test_wider_ci_at_higher_confidence(self):
        returns = np.random.RandomState(42).normal(0.001, 0.01, 200)
        r_95 = return_bootstrap(returns, confidence_level=0.95, seed=42)
        r_99 = return_bootstrap(returns, confidence_level=0.99, seed=42)
        w_95 = r_95.ci_upper - r_95.ci_lower
        w_99 = r_99.ci_upper - r_99.ci_lower
        assert w_99 > w_95

    def test_too_few_observations(self):
        with pytest.raises(ValueError, match="at least 2"):
            return_bootstrap(np.array([0.01]))

    def test_invalid_confidence_level(self):
        with pytest.raises(ValueError, match="confidence_level"):
            return_bootstrap(np.array([0.01, 0.02]), confidence_level=1.5)

    def test_zero_mean_ci_straddles_zero(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.0, 0.01, 1000)
        result = return_bootstrap(returns, n_bootstraps=1000, seed=42)
        # CI should contain zero for zero-mean returns
        assert result.ci_lower < 0 < result.ci_upper


class TestParameterPerturbation:
    """Tests for parameter perturbation sensitivity analysis."""

    def test_without_evaluate_fn(self):
        params = {"bb_period": 20, "bb_std_dev": 2.0}
        result = parameter_perturbation(params, "bb_period", n_perturbations=50)
        assert result.param_name == "bb_period"
        assert result.n_perturbations == 50
        assert result.base_metric is None
        assert result.mean_metric is None
        assert result.pct_degraded is None

    def test_with_evaluate_fn(self):
        params = {"x": 10.0, "y": 5.0}
        # Simple metric: closer to x=10 is better
        def evaluate(p):
            return -abs(p["x"] - 10.0)
        result = parameter_perturbation(
            params, "x", noise_pct=0.1, n_perturbations=200,
            evaluate_fn=evaluate, seed=42,
        )
        assert result.base_metric == 0.0  # x=10 is optimal
        assert result.mean_metric < 0.0   # perturbations move away from optimum
        assert result.pct_degraded > 0.5  # most perturbations degrade

    def test_insensitive_param(self):
        params = {"x": 10.0, "y": 5.0}
        # Metric only depends on y, not x
        def evaluate(p):
            return p["y"]
        result = parameter_perturbation(
            params, "x", noise_pct=0.1, n_perturbations=100,
            evaluate_fn=evaluate, seed=42,
        )
        assert result.std_metric == 0.0  # no variance since metric ignores x
        assert result.pct_degraded == 0.0

    def test_deterministic_with_seed(self):
        params = {"x": 10.0}
        def evaluate(p):
            return p["x"] ** 2
        r1 = parameter_perturbation(params, "x", evaluate_fn=evaluate, seed=42)
        r2 = parameter_perturbation(params, "x", evaluate_fn=evaluate, seed=42)
        assert r1.mean_metric == r2.mean_metric
        assert r1.std_metric == r2.std_metric

    def test_unknown_param(self):
        with pytest.raises(ValueError, match="not in base_params"):
            parameter_perturbation({"x": 1.0}, "unknown")

    def test_non_numeric_param(self):
        with pytest.raises(ValueError, match="numeric"):
            parameter_perturbation({"ma_type": "sma"}, "ma_type")

    def test_noise_scales_with_value(self):
        # Larger base value -> larger perturbation noise
        params_small = {"x": 1.0}
        params_large = {"x": 100.0}
        def evaluate(p):
            return p["x"]
        r_small = parameter_perturbation(
            params_small, "x", noise_pct=0.1, n_perturbations=500,
            evaluate_fn=evaluate, seed=42,
        )
        r_large = parameter_perturbation(
            params_large, "x", noise_pct=0.1, n_perturbations=500,
            evaluate_fn=evaluate, seed=42,
        )
        assert r_large.std_metric > r_small.std_metric
