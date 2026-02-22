"""Tests for Mean Reversion BB optimizer."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

from strategies.mean_reversion_bb.optimizer import (
    BacktestResult,
    OptimizationResult,
    _compute_metrics,
    _apply_params_to_model,
    evaluate_params,
    grid_search,
    random_search,
    bayesian_search,
    save_results,
    DEFAULT_MAX_DRAWDOWN,
)
from strategies.mean_reversion_bb.param_registry import ParamRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_df():
    """Small OHLCV DataFrame for testing."""
    np.random.seed(42)
    n = 100
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        "open": close + np.random.randn(n) * 0.1,
        "high": close + abs(np.random.randn(n) * 0.5),
        "low": close - abs(np.random.randn(n) * 0.5),
        "close": close,
        "volume": np.random.uniform(100, 1000, n),
    }, index=pd.date_range("2025-01-01", periods=n, freq="5min"))


@pytest.fixture
def mock_backtest_result():
    """A mock BacktestResult for testing."""
    return BacktestResult(
        params={"bb_period": 20, "bb_std_dev": 2.0},
        sharpe=0.15,
        max_drawdown=0.08,
        total_return_pct=12.5,
        total_trades=25,
        final_equity=11250.0,
        feasible=True,
    )


def _make_equity_curve(equities):
    """Helper to create equity curve dicts."""
    return [{"timestamp": i, "equity": e} for i, e in enumerate(equities)]


# ---------------------------------------------------------------------------
# _compute_metrics tests
# ---------------------------------------------------------------------------

class TestComputeMetrics:

    def test_monotonic_up_zero_drawdown(self):
        curve = _make_equity_curve([10000, 10100, 10200, 10300])
        sharpe, dd = _compute_metrics(curve, 10000)
        assert dd == 0.0
        assert sharpe > 0

    def test_drawdown_calculated_correctly(self):
        # Peak at 11000, trough at 9500 -> dd = 1500/11000 = 0.1364
        curve = _make_equity_curve([10000, 11000, 9500, 10500])
        sharpe, dd = _compute_metrics(curve, 10000)
        assert abs(dd - 1500 / 11000) < 1e-6

    def test_empty_curve(self):
        sharpe, dd = _compute_metrics([], 10000)
        assert sharpe == 0.0
        assert dd == 0.0

    def test_single_point(self):
        curve = _make_equity_curve([10000])
        sharpe, dd = _compute_metrics(curve, 10000)
        assert sharpe == 0.0
        assert dd == 0.0

    def test_negative_returns_negative_sharpe(self):
        curve = _make_equity_curve([10000, 9800, 9600, 9400])
        sharpe, dd = _compute_metrics(curve, 10000)
        assert sharpe < 0
        assert dd > 0


# ---------------------------------------------------------------------------
# _apply_params_to_model tests
# ---------------------------------------------------------------------------

class TestApplyParamsToModel:

    def test_creates_model_with_params(self):
        params = {"bb_period": 30, "bb_std_dev": 2.5, "vwap_period": 60}
        model = _apply_params_to_model(params)
        assert model.bb_period == 30
        assert model.bb_std_dev == 2.5
        assert model.vwap_period == 60

    def test_uses_defaults_for_missing(self):
        model = _apply_params_to_model({})
        # Should use config defaults
        assert model.bb_period == 20
        assert model.bb_std_dev == 2.5

    def test_ignores_non_constructor_params(self):
        # These are valid registry params but not in MeanReversionBB constructor
        params = {"rsi_oversold": 25, "bb_period": 15}
        model = _apply_params_to_model(params)
        assert model.bb_period == 15


# ---------------------------------------------------------------------------
# evaluate_params tests (mocked simulator)
# ---------------------------------------------------------------------------

class TestEvaluateParams:

    @patch("strategies.mean_reversion_bb.optimizer.DirectionalSimulator")
    def test_returns_backtest_result(self, MockSim, sample_df):
        mock_instance = MockSim.return_value
        mock_instance.run_backtest.return_value = {
            "equity_curve": _make_equity_curve([10000, 10200, 10400]),
            "trade_log": [{"pnl": 200}, {"pnl": 200}],
            "total_trades": 2,
            "final_equity": 10400,
            "total_return_pct": 4.0,
        }
        params = ParamRegistry().to_dict()
        result = evaluate_params(params, sample_df)
        assert isinstance(result, BacktestResult)
        assert result.total_trades == 2
        assert result.total_return_pct == 4.0
        assert result.sharpe > 0

    @patch("strategies.mean_reversion_bb.optimizer.DirectionalSimulator")
    def test_feasibility_flag(self, MockSim, sample_df):
        mock_instance = MockSim.return_value
        # Big drawdown: 10000 -> 8000 -> 9000 = 20% dd
        mock_instance.run_backtest.return_value = {
            "equity_curve": _make_equity_curve([10000, 8000, 9000]),
            "trade_log": [],
            "total_trades": 0,
            "final_equity": 9000,
            "total_return_pct": -10.0,
        }
        params = ParamRegistry().to_dict()
        result = evaluate_params(params, sample_df, max_drawdown=0.15)
        assert result.feasible is False
        assert result.max_drawdown > 0.15

    @patch("strategies.mean_reversion_bb.optimizer.DirectionalSimulator")
    def test_feasible_when_below_constraint(self, MockSim, sample_df):
        mock_instance = MockSim.return_value
        # Small drawdown
        mock_instance.run_backtest.return_value = {
            "equity_curve": _make_equity_curve([10000, 10100, 10050, 10200]),
            "trade_log": [],
            "total_trades": 0,
            "final_equity": 10200,
            "total_return_pct": 2.0,
        }
        params = ParamRegistry().to_dict()
        result = evaluate_params(params, sample_df, max_drawdown=0.15)
        assert result.feasible is True


# ---------------------------------------------------------------------------
# grid_search tests (mocked evaluate_params)
# ---------------------------------------------------------------------------

class TestGridSearch:

    @patch("strategies.mean_reversion_bb.optimizer.evaluate_params")
    def test_grid_search_subset(self, mock_eval, sample_df):
        mock_eval.return_value = BacktestResult(
            params={}, sharpe=0.1, max_drawdown=0.05,
            total_return_pct=5.0, total_trades=10,
            final_equity=10500, feasible=True,
        )
        result = grid_search(sample_df, param_names=["ma_type"], n_workers=1)
        assert isinstance(result, OptimizationResult)
        assert result.method == "grid"
        # ma_type has 3 choices: sma, ema, wma
        assert result.total_evaluated == 3
        assert result.feasible_count == 3

    @patch("strategies.mean_reversion_bb.optimizer.evaluate_params")
    def test_grid_two_params(self, mock_eval, sample_df):
        mock_eval.return_value = BacktestResult(
            params={}, sharpe=0.1, max_drawdown=0.05,
            total_return_pct=5.0, total_trades=10,
            final_equity=10500, feasible=True,
        )
        result = grid_search(sample_df, param_names=["ma_type", "rsi_oversold"], n_workers=1)
        # ma_type: 3, rsi_oversold: 5 (20,25,30,35,40)
        assert result.total_evaluated == 3 * 5

    @patch("strategies.mean_reversion_bb.optimizer.evaluate_params")
    def test_best_selected_from_feasible(self, mock_eval, sample_df):
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            sharpe = 0.2 if call_count[0] == 2 else 0.1
            feasible = call_count[0] != 3  # 3rd is infeasible
            return BacktestResult(
                params={"idx": call_count[0]}, sharpe=sharpe,
                max_drawdown=0.20 if not feasible else 0.05,
                total_return_pct=5.0, total_trades=10,
                final_equity=10500, feasible=feasible,
            )
        mock_eval.side_effect = side_effect
        result = grid_search(sample_df, param_names=["ma_type"], n_workers=1)
        assert result.best_sharpe == 0.2
        assert result.feasible_count == 2


# ---------------------------------------------------------------------------
# random_search tests
# ---------------------------------------------------------------------------

class TestRandomSearch:

    @patch("strategies.mean_reversion_bb.optimizer.evaluate_params")
    def test_random_search_count(self, mock_eval, sample_df):
        mock_eval.return_value = BacktestResult(
            params={}, sharpe=0.1, max_drawdown=0.05,
            total_return_pct=5.0, total_trades=10,
            final_equity=10500, feasible=True,
        )
        result = random_search(sample_df, n_iterations=20, n_workers=1)
        assert result.method == "random"
        assert result.total_evaluated == 20

    @patch("strategies.mean_reversion_bb.optimizer.evaluate_params")
    def test_random_search_deterministic(self, mock_eval, sample_df):
        mock_eval.return_value = BacktestResult(
            params={}, sharpe=0.1, max_drawdown=0.05,
            total_return_pct=5.0, total_trades=10,
            final_equity=10500, feasible=True,
        )
        r1 = random_search(sample_df, n_iterations=5, random_seed=42)
        r2 = random_search(sample_df, n_iterations=5, random_seed=42)
        # Same seed -> same param combos -> same number of calls
        assert r1.total_evaluated == r2.total_evaluated

    @patch("strategies.mean_reversion_bb.optimizer.evaluate_params")
    def test_no_feasible_results(self, mock_eval, sample_df):
        mock_eval.return_value = BacktestResult(
            params={}, sharpe=0.1, max_drawdown=0.30,
            total_return_pct=-5.0, total_trades=10,
            final_equity=9500, feasible=False,
        )
        result = random_search(sample_df, n_iterations=5)
        assert result.best_params is None
        assert result.best_sharpe == 0.0
        assert result.feasible_count == 0


# ---------------------------------------------------------------------------
# bayesian_search tests
# ---------------------------------------------------------------------------

class TestBayesianSearch:

    @patch("strategies.mean_reversion_bb.optimizer.evaluate_params")
    def test_falls_back_to_random_without_optuna(self, mock_eval, sample_df):
        """Without optuna installed, should fall back to random search."""
        mock_eval.return_value = BacktestResult(
            params={}, sharpe=0.1, max_drawdown=0.05,
            total_return_pct=5.0, total_trades=10,
            final_equity=10500, feasible=True,
        )
        result = bayesian_search(sample_df, n_trials=10)
        # Since optuna is not installed, it falls back to random
        assert result.method == "random"
        assert result.total_evaluated == 10


# ---------------------------------------------------------------------------
# save_results tests
# ---------------------------------------------------------------------------

class TestSaveResults:

    def test_creates_file(self):
        result = OptimizationResult(
            method="test",
            best_params={"bb_period": 20},
            best_sharpe=0.15,
            best_drawdown=0.08,
            total_evaluated=5,
            feasible_count=3,
            elapsed_seconds=1.5,
            all_results=[],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = save_results(result, output_dir=tmpdir)
            assert os.path.exists(filepath)
            assert filepath.endswith(".json")

            with open(filepath) as f:
                data = json.load(f)
            assert data["method"] == "test"
            assert data["best_sharpe"] == 0.15
            assert data["best_params"]["bb_period"] == 20

    def test_saves_all_results(self):
        results_list = [
            BacktestResult(
                params={"bb_period": i},
                sharpe=0.1 * i,
                max_drawdown=0.01 * i,
                total_return_pct=i,
                total_trades=i,
                final_equity=10000 + i * 100,
                feasible=True,
            )
            for i in range(3)
        ]
        result = OptimizationResult(
            method="grid",
            best_params={"bb_period": 2},
            best_sharpe=0.2,
            best_drawdown=0.02,
            total_evaluated=3,
            feasible_count=3,
            elapsed_seconds=0.5,
            all_results=results_list,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = save_results(result, output_dir=tmpdir)
            with open(filepath) as f:
                data = json.load(f)
            assert len(data["results"]) == 3
            assert data["results"][2]["sharpe"] == 0.2

    def test_creates_output_dir(self):
        result = OptimizationResult(
            method="test", best_params=None, best_sharpe=0.0,
            best_drawdown=0.0, total_evaluated=0, feasible_count=0,
            elapsed_seconds=0.0, all_results=[],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "a", "b", "c")
            filepath = save_results(result, output_dir=nested)
            assert os.path.exists(filepath)
