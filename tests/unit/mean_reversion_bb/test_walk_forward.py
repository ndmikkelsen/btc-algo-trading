"""Tests for walk-forward optimization.

Verifies window generation, single-window optimization, and aggregate
reporting with synthetic OHLCV data.
"""

import numpy as np
import pandas as pd
import pytest

from strategies.mean_reversion_bb.walk_forward import (
    WalkForwardOptimizer,
    WalkForwardReport,
    WindowResult,
)
from strategies.mean_reversion_bb.param_registry import ParamRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(months: int = 12, freq: str = "1h", base_price: float = 100_000.0) -> pd.DataFrame:
    """Generate synthetic OHLCV data spanning *months* months.

    Uses 1h frequency by default to keep tests fast.
    Window-generation tests only need the index; backtest tests run through
    the model so larger freq avoids tens of thousands of candles.
    """
    rng = np.random.RandomState(42)
    start = pd.Timestamp("2024-01-01")
    end = start + pd.DateOffset(months=months)
    idx = pd.date_range(start, end, freq=freq)

    n = len(idx)
    returns = rng.normal(0, 0.001, n)
    close = base_price * np.exp(np.cumsum(returns))
    noise = rng.uniform(0.5, 1.5, n)

    df = pd.DataFrame({
        "open": close * (1 - 0.001 * noise),
        "high": close * (1 + 0.002 * noise),
        "low": close * (1 - 0.002 * noise),
        "close": close,
        "volume": rng.uniform(50, 200, n),
    }, index=idx)
    return df


# ===========================================================================
# Window generation
# ===========================================================================


class TestWindowGeneration:
    """Test that walk-forward windows are generated correctly."""

    def test_basic_window_count(self):
        """12 months data, 6m train, 1m test => ~6 windows."""
        df = _make_ohlcv(months=12)
        wfo = WalkForwardOptimizer(df, train_months=6, test_months=1)
        windows = wfo._generate_windows()
        assert len(windows) >= 5
        assert len(windows) <= 7

    def test_windows_cover_data(self):
        """Test windows collectively cover the OOS portion."""
        df = _make_ohlcv(months=12)
        wfo = WalkForwardOptimizer(df, train_months=6, test_months=1)
        windows = wfo._generate_windows()

        # First test window starts after first train period
        first_test = windows[0]["test_start"]
        expected_start = df.index.min() + pd.DateOffset(months=6)
        assert abs((first_test - expected_start).total_seconds()) < 86400 * 2  # within 2 days

    def test_train_windows_are_anchored(self):
        """Anchored: all train windows start at same date."""
        df = _make_ohlcv(months=12)
        wfo = WalkForwardOptimizer(df, train_months=6, test_months=1)
        windows = wfo._generate_windows()

        starts = [w["train_start"] for w in windows]
        assert all(s == starts[0] for s in starts)

    def test_train_end_increases(self):
        """Each window's train_end should increase monotonically."""
        df = _make_ohlcv(months=12)
        wfo = WalkForwardOptimizer(df, train_months=6, test_months=1)
        windows = wfo._generate_windows()

        train_ends = [w["train_end"] for w in windows]
        for i in range(1, len(train_ends)):
            assert train_ends[i] > train_ends[i - 1]

    def test_insufficient_data_raises(self):
        """Not enough data should raise ValueError."""
        df = _make_ohlcv(months=3)
        wfo = WalkForwardOptimizer(df, train_months=6, test_months=1)
        with pytest.raises(ValueError, match="Not enough data"):
            wfo.run(verbose=False)

    def test_window_ids_sequential(self):
        df = _make_ohlcv(months=12)
        wfo = WalkForwardOptimizer(df, train_months=6, test_months=1)
        windows = wfo._generate_windows()
        ids = [w["window_id"] for w in windows]
        assert ids == list(range(len(ids)))


# ===========================================================================
# Model building
# ===========================================================================


class TestModelBuilding:
    """Test parameter application to model."""

    def test_build_model_with_defaults(self):
        df = _make_ohlcv(months=12)
        wfo = WalkForwardOptimizer(df)
        params = wfo.registry.to_dict()
        model = wfo._build_model(params)
        assert model.bb_period == 20
        assert model.bb_std_dev == 2.5

    def test_build_model_with_custom_params(self):
        df = _make_ohlcv(months=12)
        wfo = WalkForwardOptimizer(df)
        params = wfo.registry.to_dict()
        params["bb_period"] = 30
        params["rsi_period"] = 21
        model = wfo._build_model(params)
        assert model.bb_period == 30
        assert model.rsi_period == 21


# ===========================================================================
# Single backtest
# ===========================================================================


class TestSingleBacktest:
    """Test running a single backtest via walk-forward."""

    def test_backtest_returns_dict(self):
        df = _make_ohlcv(months=8)
        wfo = WalkForwardOptimizer(df)
        params = wfo.registry.to_dict()
        result = wfo._run_backtest(df, params)
        assert "total_return_pct" in result
        assert "total_trades" in result
        assert "final_equity" in result
        assert "equity_curve" in result


# ===========================================================================
# Walk-forward report
# ===========================================================================


class TestWalkForwardReport:
    """Test the aggregate report dataclass."""

    def test_report_fields(self):
        wr = WindowResult(
            window_id=0,
            train_start=pd.Timestamp("2024-01-01"),
            train_end=pd.Timestamp("2024-07-01"),
            test_start=pd.Timestamp("2024-07-01"),
            test_end=pd.Timestamp("2024-08-01"),
            best_params={},
            is_return_pct=10.0,
            oos_return_pct=6.0,
            is_trades=50,
            oos_trades=8,
            wf_efficiency=0.6,
        )
        assert wr.wf_efficiency == 0.6
        assert wr.oos_return_pct == 6.0

    def test_report_aggregate(self):
        report = WalkForwardReport(
            windows=[],
            mean_wf_efficiency=0.65,
            median_wf_efficiency=0.60,
            total_oos_return_pct=12.0,
            total_oos_trades=40,
            num_profitable_windows=4,
            num_windows=6,
        )
        assert report.mean_wf_efficiency == 0.65
        assert report.num_profitable_windows == 4


# ===========================================================================
# WF efficiency calculation
# ===========================================================================


class TestWFEfficiency:
    """Test walk-forward efficiency edge cases."""

    def test_positive_is_return(self):
        """WFE = OOS/IS when IS > 0."""
        wr = WindowResult(
            window_id=0,
            train_start=pd.Timestamp("2024-01-01"),
            train_end=pd.Timestamp("2024-07-01"),
            test_start=pd.Timestamp("2024-07-01"),
            test_end=pd.Timestamp("2024-08-01"),
            best_params={},
            is_return_pct=10.0,
            oos_return_pct=7.0,
            is_trades=50,
            oos_trades=8,
            wf_efficiency=7.0 / 10.0,
        )
        assert abs(wr.wf_efficiency - 0.7) < 1e-10

    def test_zero_is_return_gives_nan(self):
        """WFE should be NaN when IS return is zero or negative."""
        import math
        wr = WindowResult(
            window_id=0,
            train_start=pd.Timestamp("2024-01-01"),
            train_end=pd.Timestamp("2024-07-01"),
            test_start=pd.Timestamp("2024-07-01"),
            test_end=pd.Timestamp("2024-08-01"),
            best_params={},
            is_return_pct=0.0,
            oos_return_pct=5.0,
            is_trades=0,
            oos_trades=3,
            wf_efficiency=float("nan"),
        )
        assert math.isnan(wr.wf_efficiency)
