"""Unit tests for performance metrics."""

import pytest
import numpy as np
from strategies.avellaneda_stoikov.metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    win_rate,
    profit_factor,
    calculate_all_metrics,
)


class TestSharpeRatio:
    """Tests for Sharpe ratio calculation."""

    def test_positive_returns_positive_sharpe(self):
        """Positive consistent returns give positive Sharpe."""
        # Steadily increasing equity
        equity_curve = [{'equity': 10000 + i * 10} for i in range(100)]
        sharpe = sharpe_ratio(equity_curve, periods_per_year=100)
        assert sharpe > 0

    def test_negative_returns_negative_sharpe(self):
        """Negative returns give negative Sharpe."""
        equity_curve = [{'equity': 10000 - i * 10} for i in range(100)]
        sharpe = sharpe_ratio(equity_curve, periods_per_year=100)
        assert sharpe < 0

    def test_flat_returns_zero_sharpe(self):
        """Flat equity curve gives zero Sharpe."""
        equity_curve = [{'equity': 10000} for _ in range(100)]
        sharpe = sharpe_ratio(equity_curve, periods_per_year=100)
        assert sharpe == 0.0

    def test_empty_curve_returns_zero(self):
        """Empty equity curve returns zero."""
        sharpe = sharpe_ratio([], periods_per_year=100)
        assert sharpe == 0.0


class TestSortinoRatio:
    """Tests for Sortino ratio calculation."""

    def test_no_downside_returns_infinity(self):
        """Only positive returns gives infinite Sortino."""
        equity_curve = [{'equity': 10000 + i * 10} for i in range(100)]
        sortino = sortino_ratio(equity_curve, periods_per_year=100)
        assert sortino == float('inf')

    def test_mixed_returns_finite_sortino(self):
        """Mixed returns give finite Sortino."""
        np.random.seed(42)
        equity = 10000
        curve = []
        for _ in range(100):
            equity += np.random.randn() * 50
            curve.append({'equity': equity})

        sortino = sortino_ratio(curve, periods_per_year=100)
        assert sortino != float('inf')
        assert not np.isnan(sortino)


class TestMaxDrawdown:
    """Tests for maximum drawdown calculation."""

    def test_no_drawdown_for_increasing_equity(self):
        """Steadily increasing equity has zero drawdown."""
        equity_curve = [{'equity': 10000 + i * 10} for i in range(100)]
        dd = max_drawdown(equity_curve)
        assert dd['max_drawdown_pct'] == 0.0

    def test_drawdown_calculated_correctly(self):
        """Drawdown percentage is calculated correctly."""
        # Peak at 10000, drops to 9000 (10% drawdown)
        equity_curve = [
            {'equity': 10000},
            {'equity': 9000},
            {'equity': 9500},
        ]
        dd = max_drawdown(equity_curve)
        assert dd['max_drawdown_pct'] == pytest.approx(-10.0)

    def test_drawdown_duration_tracked(self):
        """Drawdown duration is tracked."""
        equity_curve = [
            {'equity': 10000},
            {'equity': 9000},  # Start drawdown
            {'equity': 9200},  # Still in drawdown
            {'equity': 9800},  # Still in drawdown
            {'equity': 10100},  # Recovery
        ]
        dd = max_drawdown(equity_curve)
        assert dd['max_drawdown_duration'] >= 3


class TestWinRate:
    """Tests for win rate calculation."""

    def test_all_wins_100_percent(self):
        """All profitable trades gives 100% win rate."""
        trades = [
            {'side': 'buy', 'price': 100, 'quantity': 1},
            {'side': 'sell', 'price': 110, 'quantity': 1},
            {'side': 'buy', 'price': 100, 'quantity': 1},
            {'side': 'sell', 'price': 120, 'quantity': 1},
        ]
        wr = win_rate(trades)
        assert wr == 1.0

    def test_all_losses_0_percent(self):
        """All losing trades gives 0% win rate."""
        trades = [
            {'side': 'buy', 'price': 100, 'quantity': 1},
            {'side': 'sell', 'price': 90, 'quantity': 1},
        ]
        wr = win_rate(trades)
        assert wr == 0.0

    def test_mixed_results(self):
        """Mixed results give correct win rate."""
        trades = [
            {'side': 'buy', 'price': 100, 'quantity': 1},
            {'side': 'sell', 'price': 110, 'quantity': 1},  # Win
            {'side': 'buy', 'price': 100, 'quantity': 1},
            {'side': 'sell', 'price': 90, 'quantity': 1},   # Loss
        ]
        wr = win_rate(trades)
        assert wr == 0.5

    def test_empty_trades_returns_zero(self):
        """Empty trades list returns zero."""
        wr = win_rate([])
        assert wr == 0.0


class TestProfitFactor:
    """Tests for profit factor calculation."""

    def test_all_profits_returns_infinity(self):
        """All profits returns infinity."""
        trades = [
            {'side': 'buy', 'price': 100, 'quantity': 1},
            {'side': 'sell', 'price': 110, 'quantity': 1},
        ]
        pf = profit_factor(trades)
        assert pf == float('inf')

    def test_profit_factor_calculated_correctly(self):
        """Profit factor calculated as gross profit / gross loss."""
        trades = [
            {'side': 'buy', 'price': 100, 'quantity': 1},
            {'side': 'sell', 'price': 120, 'quantity': 1},  # +20 profit
            {'side': 'buy', 'price': 100, 'quantity': 1},
            {'side': 'sell', 'price': 90, 'quantity': 1},   # -10 loss
        ]
        pf = profit_factor(trades)
        assert pf == pytest.approx(2.0)  # 20 / 10


class TestCalculateAllMetrics:
    """Tests for combined metrics calculation."""

    def test_returns_all_expected_keys(self):
        """Function returns all expected metric keys."""
        np.random.seed(42)
        equity = 10000
        curve = []
        for _ in range(100):
            equity += np.random.randn() * 50
            curve.append({'equity': equity})

        trades = [
            {'side': 'buy', 'price': 100, 'quantity': 1},
            {'side': 'sell', 'price': 110, 'quantity': 1},
        ]

        metrics = calculate_all_metrics(curve, trades, 10000)

        assert 'total_return_pct' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'sortino_ratio' in metrics
        assert 'max_drawdown_pct' in metrics
        assert 'win_rate' in metrics
        assert 'profit_factor' in metrics

    def test_empty_curve_returns_empty_dict(self):
        """Empty equity curve returns empty dict."""
        metrics = calculate_all_metrics([], [], 10000)
        assert metrics == {}
