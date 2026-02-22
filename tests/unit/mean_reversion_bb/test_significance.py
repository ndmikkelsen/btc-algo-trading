"""Tests for statistical significance module."""

import numpy as np
import pytest
from scipy import stats

from strategies.mean_reversion_bb.significance import (
    sharpe_t_stat,
    deflated_sharpe_ratio,
    whites_reality_check,
    min_backtest_length,
)


class TestSharpeTStat:
    """Tests for Sharpe ratio t-statistic."""

    def test_positive_sharpe(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.001, 0.01, 1000)
        result = sharpe_t_stat(returns)
        assert result.sharpe > 0
        assert result.t_stat > 0
        assert result.n_obs == 1000

    def test_zero_mean_not_significant(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.0, 0.01, 100)
        result = sharpe_t_stat(returns)
        # With zero true mean and 100 obs, should usually not be significant
        # (but random; just check structure)
        assert 0.0 <= result.p_value <= 1.0

    def test_strong_signal_significant(self):
        rng = np.random.RandomState(42)
        # Very strong signal: mean = 0.01, std = 0.005
        returns = rng.normal(0.01, 0.005, 500)
        result = sharpe_t_stat(returns)
        assert result.p_value < 0.01
        assert result.t_stat > 2.0

    def test_matches_scipy_ttest(self):
        rng = np.random.RandomState(123)
        returns = rng.normal(0.002, 0.01, 200)
        result = sharpe_t_stat(returns)
        scipy_t, scipy_p = stats.ttest_1samp(returns, 0.0)
        assert abs(result.t_stat - scipy_t) < 1e-10
        assert abs(result.p_value - scipy_p) < 1e-10

    def test_too_few_observations(self):
        with pytest.raises(ValueError, match="at least 2"):
            sharpe_t_stat(np.array([0.01]))

    def test_zero_std(self):
        with pytest.raises(ValueError, match="Zero standard deviation"):
            sharpe_t_stat(np.array([0.01, 0.01, 0.01]))


class TestDeflatedSharpeRatio:
    """Tests for Deflated Sharpe Ratio."""

    def test_single_trial_easier_to_pass(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.002, 0.01, 500)
        observed_sr = np.mean(returns) / np.std(returns, ddof=1)

        dsr_1 = deflated_sharpe_ratio(observed_sr, n_trials=1, returns=returns)
        dsr_100 = deflated_sharpe_ratio(observed_sr, n_trials=100, returns=returns)

        # More trials -> higher bar -> higher p-value (less significant)
        assert dsr_1.p_value < dsr_100.p_value

    def test_high_sharpe_survives_deflation(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.005, 0.01, 1000)
        observed_sr = np.mean(returns) / np.std(returns, ddof=1)

        result = deflated_sharpe_ratio(observed_sr, n_trials=10, returns=returns)
        assert result.is_significant is True
        assert result.p_value < 0.05

    def test_weak_sharpe_fails_with_many_trials(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.0005, 0.01, 200)
        observed_sr = np.mean(returns) / np.std(returns, ddof=1)

        result = deflated_sharpe_ratio(observed_sr, n_trials=1000, returns=returns)
        assert result.is_significant is False

    def test_too_few_observations(self):
        with pytest.raises(ValueError, match="at least 3"):
            deflated_sharpe_ratio(1.0, 10, np.array([0.01, 0.02]))

    def test_invalid_n_trials(self):
        with pytest.raises(ValueError, match="n_trials"):
            deflated_sharpe_ratio(1.0, 0, np.random.randn(100))

    def test_result_fields(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.001, 0.01, 300)
        sr = np.mean(returns) / np.std(returns, ddof=1)

        result = deflated_sharpe_ratio(sr, 5, returns)
        assert result.observed_sharpe == sr
        assert result.n_trials == 5
        assert 0.0 <= result.p_value <= 1.0


class TestWhitesRealityCheck:
    """Tests for White's Reality Check bootstrap."""

    def test_null_strategies_not_significant(self):
        rng = np.random.RandomState(42)
        # All strategies have zero true mean
        returns = rng.normal(0.0, 0.01, (500, 10))
        result = whites_reality_check(returns, n_bootstraps=500, seed=42)
        assert result.p_value > 0.05
        assert result.is_significant is False

    def test_strong_strategy_significant(self):
        rng = np.random.RandomState(42)
        # 9 null strategies + 1 strong strategy
        null_returns = rng.normal(0.0, 0.01, (500, 9))
        strong_returns = rng.normal(0.005, 0.01, (500, 1))
        returns = np.hstack([null_returns, strong_returns])
        result = whites_reality_check(returns, n_bootstraps=1000, seed=42)
        assert result.p_value < 0.05
        assert result.is_significant is True

    def test_deterministic_with_seed(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.001, 0.01, (200, 5))
        r1 = whites_reality_check(returns, n_bootstraps=500, seed=123)
        r2 = whites_reality_check(returns, n_bootstraps=500, seed=123)
        assert r1.p_value == r2.p_value

    def test_result_fields(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.0, 0.01, (100, 3))
        result = whites_reality_check(returns, n_bootstraps=200, seed=42)
        assert result.n_strategies == 3
        assert result.n_bootstraps == 200
        assert 0.0 <= result.p_value <= 1.0

    def test_invalid_input_shape(self):
        with pytest.raises(ValueError, match="2D"):
            whites_reality_check(np.array([1.0, 2.0, 3.0]))

    def test_p_value_bounded(self):
        rng = np.random.RandomState(42)
        returns = rng.normal(0.0, 0.01, (100, 5))
        result = whites_reality_check(returns, n_bootstraps=100, seed=42)
        assert 0.0 <= result.p_value <= 1.0


class TestMinBacktestLength:
    """Tests for minimum backtest length calculation."""

    def test_known_values(self):
        # SR=0.5, alpha=0.05, power=0.80 -> n ~= 31.4 -> 32
        # z_alpha/2 = 1.96, z_beta = 0.8416
        # n = ((1.96 + 0.8416) / 0.5)^2 = (2.8016/0.5)^2 = 5.6032^2 = 31.4
        n = min_backtest_length(0.5, alpha=0.05, power=0.80)
        assert n == 32

    def test_higher_sharpe_needs_fewer_obs(self):
        n_low = min_backtest_length(0.2)
        n_high = min_backtest_length(1.0)
        assert n_high < n_low

    def test_higher_power_needs_more_obs(self):
        n_80 = min_backtest_length(0.5, power=0.80)
        n_95 = min_backtest_length(0.5, power=0.95)
        assert n_95 > n_80

    def test_stricter_alpha_needs_more_obs(self):
        n_05 = min_backtest_length(0.5, alpha=0.05)
        n_01 = min_backtest_length(0.5, alpha=0.01)
        assert n_01 > n_05

    def test_returns_int(self):
        n = min_backtest_length(0.5)
        assert isinstance(n, int)

    def test_invalid_sharpe(self):
        with pytest.raises(ValueError, match="positive"):
            min_backtest_length(0.0)
        with pytest.raises(ValueError, match="positive"):
            min_backtest_length(-1.0)

    def test_invalid_alpha(self):
        with pytest.raises(ValueError, match="alpha"):
            min_backtest_length(0.5, alpha=0.0)
        with pytest.raises(ValueError, match="alpha"):
            min_backtest_length(0.5, alpha=1.0)

    def test_invalid_power(self):
        with pytest.raises(ValueError, match="power"):
            min_backtest_length(0.5, power=0.0)
