"""Unit tests for the order book data pipeline and kappa calibration."""

import numpy as np
import pytest

from strategies.avellaneda_stoikov.orderbook import (
    OrderBookSnapshot,
    OrderBookCollector,
    TradeRecord,
    KappaCalibrator,
)
from strategies.avellaneda_stoikov.kappa_provider import (
    KappaProvider,
    ConstantKappaProvider,
    LiveKappaProvider,
    HistoricalKappaProvider,
)


# =============================================================================
# OrderBookSnapshot
# =============================================================================


class TestOrderBookSnapshot:

    def test_mid_price_computed_from_bids_asks(self):
        snap = OrderBookSnapshot(
            bids=[(99990.0, 1.0)],
            asks=[(100010.0, 1.0)],
            timestamp=1000.0,
        )
        assert snap.mid_price == pytest.approx(100000.0)

    def test_mid_price_explicit_overrides(self):
        snap = OrderBookSnapshot(
            bids=[(99990.0, 1.0)],
            asks=[(100010.0, 1.0)],
            timestamp=1000.0,
            mid_price=99999.0,
        )
        assert snap.mid_price == 99999.0

    def test_empty_bids_asks_keeps_zero_mid(self):
        snap = OrderBookSnapshot(
            bids=[],
            asks=[],
            timestamp=1000.0,
        )
        assert snap.mid_price == 0.0

    def test_multiple_levels(self):
        snap = OrderBookSnapshot(
            bids=[(100.0, 1.0), (99.0, 2.0)],
            asks=[(101.0, 1.0), (102.0, 2.0)],
            timestamp=1000.0,
        )
        # Mid = (100 + 101) / 2 = 100.5
        assert snap.mid_price == pytest.approx(100.5)


# =============================================================================
# OrderBookCollector
# =============================================================================


class TestOrderBookCollector:

    def test_add_snapshot(self):
        collector = OrderBookCollector()
        snap = OrderBookSnapshot(
            bids=[(100.0, 1.0)],
            asks=[(101.0, 1.0)],
            timestamp=1000.0,
        )
        collector.add_snapshot(snap)
        assert collector.snapshot_count == 1

    def test_add_trade(self):
        collector = OrderBookCollector()
        trade = TradeRecord(price=100.0, qty=0.01, timestamp=1000.0, side="Buy")
        collector.add_trade(trade)
        assert collector.trade_count == 1

    def test_max_snapshots_enforced(self):
        collector = OrderBookCollector(max_snapshots=5)
        for i in range(10):
            collector.add_snapshot(OrderBookSnapshot(
                bids=[(100.0, 1.0)],
                asks=[(101.0, 1.0)],
                timestamp=float(i),
            ))
        assert collector.snapshot_count == 5

    def test_max_trades_enforced(self):
        collector = OrderBookCollector(max_trades=5)
        for i in range(10):
            collector.add_trade(TradeRecord(
                price=100.0 + i,
                qty=0.01,
                timestamp=float(i),
                side="Buy",
            ))
        assert collector.trade_count == 5

    def test_get_trades_in_window(self):
        collector = OrderBookCollector()
        for i in range(100):
            collector.add_trade(TradeRecord(
                price=100.0,
                qty=0.01,
                timestamp=1000.0 + i,
                side="Buy",
            ))
        # Window of 50 seconds: trades from t=50 to t=99
        trades = collector.get_trades_in_window(50.0)
        assert len(trades) == 51  # timestamps 49..99 inclusive

    def test_get_trades_in_window_empty(self):
        collector = OrderBookCollector()
        assert collector.get_trades_in_window() == []

    def test_get_latest_mid_price(self):
        collector = OrderBookCollector()
        collector.add_snapshot(OrderBookSnapshot(
            bids=[(99.0, 1.0)], asks=[(101.0, 1.0)], timestamp=1.0,
        ))
        collector.add_snapshot(OrderBookSnapshot(
            bids=[(199.0, 1.0)], asks=[(201.0, 1.0)], timestamp=2.0,
        ))
        assert collector.get_latest_mid_price() == pytest.approx(200.0)

    def test_get_latest_mid_price_none_when_empty(self):
        collector = OrderBookCollector()
        assert collector.get_latest_mid_price() is None


# =============================================================================
# KappaCalibrator
# =============================================================================


def _generate_exponential_trades(
    mid: float,
    kappa: float,
    A: float,
    n: int,
    time_span: float = 600.0,
    seed: int = 42,
) -> list:
    """Generate synthetic trades from lambda = A * exp(-kappa * delta)."""
    np.random.seed(seed)
    trades = []
    base_time = 1000000.0
    for i in range(n):
        delta = np.random.exponential(1.0 / kappa)
        side = np.random.choice(["Buy", "Sell"])
        sign = 1.0 if side == "Sell" else -1.0
        price = mid + sign * delta
        ts = base_time + (i / n) * time_span
        trades.append(TradeRecord(
            price=price,
            qty=0.001,
            timestamp=ts,
            side=side,
        ))
    return trades


class TestKappaCalibrator:

    def test_calibrate_known_kappa(self):
        """Fit should recover known kappa from synthetic data."""
        mid = 100000.0
        true_kappa = 0.05
        trades = _generate_exponential_trades(mid, true_kappa, 2.0, 1000)

        calibrator = KappaCalibrator(bin_width=2.0, min_trades=20)
        est = calibrator.calibrate(trades, mid)

        assert est is not None
        assert abs(est.kappa - true_kappa) < 0.03

    def test_calibrate_returns_none_with_few_trades(self):
        """Should return None when too few trades."""
        mid = 100000.0
        trades = _generate_exponential_trades(mid, 0.05, 2.0, 5)
        calibrator = KappaCalibrator(min_trades=30)
        assert calibrator.calibrate(trades, mid) is None

    def test_calibrate_returns_none_with_zero_time_span(self):
        """All trades at same timestamp should return None."""
        mid = 100000.0
        trades = [
            TradeRecord(price=mid + i, qty=0.001, timestamp=1000.0, side="Buy")
            for i in range(50)
        ]
        calibrator = KappaCalibrator(min_trades=10)
        assert calibrator.calibrate(trades, mid) is None

    def test_calibrate_kappa_range(self):
        """Calibrated kappa should be in a reasonable range."""
        mid = 100000.0
        trades = _generate_exponential_trades(mid, 0.02, 1.5, 500)
        calibrator = KappaCalibrator(bin_width=5.0, min_trades=20)
        est = calibrator.calibrate(trades, mid)

        assert est is not None
        assert 0.001 < est.kappa < 1.0

    def test_calibrate_A_positive(self):
        """Arrival rate A should always be positive."""
        mid = 100000.0
        trades = _generate_exponential_trades(mid, 0.05, 3.0, 500)
        calibrator = KappaCalibrator(bin_width=2.0, min_trades=20)
        est = calibrator.calibrate(trades, mid)

        assert est is not None
        assert est.A > 0

    def test_calibrate_r_squared(self):
        """R^2 should be reasonable for well-behaved synthetic data."""
        mid = 100000.0
        trades = _generate_exponential_trades(mid, 0.05, 2.0, 2000)
        calibrator = KappaCalibrator(bin_width=1.0, min_trades=20)
        est = calibrator.calibrate(trades, mid)

        assert est is not None
        assert est.r_squared > 0.3

    def test_calibrate_from_collector(self):
        """Should work through the collector convenience method."""
        mid = 100000.0
        collector = OrderBookCollector()
        collector.add_snapshot(OrderBookSnapshot(
            bids=[(mid - 5, 1.0)],
            asks=[(mid + 5, 1.0)],
            timestamp=1000000.0,
        ))

        trades = _generate_exponential_trades(mid, 0.05, 2.0, 500)
        for t in trades:
            collector.add_trade(t)

        calibrator = KappaCalibrator(bin_width=2.0, min_trades=20)
        est = calibrator.calibrate_from_collector(collector)

        assert est is not None
        assert est.kappa > 0

    def test_calibrate_from_collector_no_snapshot(self):
        """Should return None when no snapshot available for mid price."""
        collector = OrderBookCollector()
        mid = 100000.0
        trades = _generate_exponential_trades(mid, 0.05, 2.0, 500)
        for t in trades:
            collector.add_trade(t)

        calibrator = KappaCalibrator()
        assert calibrator.calibrate_from_collector(collector) is None

    def test_fit_log_linear_basic(self):
        """Test the internal log-linear fit."""
        # y = 2 - 0.5x => kappa=0.5, log_A=2
        x = np.array([0, 1, 2, 3, 4], dtype=float)
        y = 2.0 - 0.5 * x

        kappa, log_A, r_sq = KappaCalibrator._fit_log_linear(x, y)
        assert kappa == pytest.approx(0.5, abs=1e-10)
        assert log_A == pytest.approx(2.0, abs=1e-10)
        assert r_sq == pytest.approx(1.0, abs=1e-10)

    def test_fit_log_linear_single_point(self):
        """Single point should return zeros."""
        kappa, log_A, r_sq = KappaCalibrator._fit_log_linear(
            np.array([1.0]), np.array([1.0])
        )
        assert kappa == 0.0
        assert r_sq == 0.0


# =============================================================================
# KappaProvider implementations
# =============================================================================


class TestConstantKappaProvider:

    def test_returns_fixed_values(self):
        provider = ConstantKappaProvider(kappa=0.05, A=2.0)
        kappa, A = provider.get_kappa()
        assert kappa == 0.05
        assert A == 2.0

    def test_default_values(self):
        provider = ConstantKappaProvider()
        kappa, A = provider.get_kappa()
        assert kappa == 0.5
        assert A == 20.0

    def test_is_kappa_provider(self):
        provider = ConstantKappaProvider()
        assert isinstance(provider, KappaProvider)


class TestLiveKappaProvider:

    def test_returns_defaults_when_no_data(self):
        collector = OrderBookCollector()
        provider = LiveKappaProvider(
            collector=collector,
            default_kappa=0.03,
            default_A=1.5,
        )
        kappa, A = provider.get_kappa()
        assert kappa == 0.03
        assert A == 1.5

    def test_returns_calibrated_values(self):
        mid = 100000.0
        collector = OrderBookCollector()
        collector.add_snapshot(OrderBookSnapshot(
            bids=[(mid - 5, 1.0)],
            asks=[(mid + 5, 1.0)],
            timestamp=1000000.0,
        ))

        trades = _generate_exponential_trades(mid, 0.05, 2.0, 500)
        for t in trades:
            collector.add_trade(t)

        provider = LiveKappaProvider(
            collector=collector,
            calibrator=KappaCalibrator(bin_width=2.0, min_trades=20),
        )
        kappa, A = provider.get_kappa()

        assert kappa > 0
        assert A > 0
        assert provider.last_estimate is not None

    def test_falls_back_to_last_estimate(self):
        mid = 100000.0
        collector = OrderBookCollector()
        collector.add_snapshot(OrderBookSnapshot(
            bids=[(mid - 5, 1.0)],
            asks=[(mid + 5, 1.0)],
            timestamp=1000000.0,
        ))

        trades = _generate_exponential_trades(mid, 0.05, 2.0, 500)
        for t in trades:
            collector.add_trade(t)

        provider = LiveKappaProvider(
            collector=collector,
            calibrator=KappaCalibrator(bin_width=2.0, min_trades=20),
        )

        # First call succeeds
        k1, a1 = provider.get_kappa()
        assert provider.last_estimate is not None

        # Clear trades so calibration fails
        collector.trades.clear()
        collector.snapshots.clear()

        # Should fall back to last estimate
        k2, a2 = provider.get_kappa()
        assert k2 == k1
        assert a2 == a1

    def test_is_kappa_provider(self):
        provider = LiveKappaProvider(collector=OrderBookCollector())
        assert isinstance(provider, KappaProvider)


class TestHistoricalKappaProvider:

    def test_returns_latest_entry(self):
        data = [
            (1000.0, 0.02, 1.0),
            (2000.0, 0.05, 2.0),
            (3000.0, 0.03, 1.5),
        ]
        provider = HistoricalKappaProvider(data=data)
        kappa, A = provider.get_kappa()
        assert kappa == 0.03
        assert A == 1.5

    def test_returns_defaults_when_empty(self):
        provider = HistoricalKappaProvider(default_kappa=0.01, default_A=0.5)
        kappa, A = provider.get_kappa()
        assert kappa == 0.01
        assert A == 0.5

    def test_advance_to_timestamp(self):
        data = [
            (1000.0, 0.02, 1.0),
            (2000.0, 0.05, 2.0),
            (3000.0, 0.03, 1.5),
        ]
        provider = HistoricalKappaProvider(data=data)
        provider.advance_to(1500.0)
        kappa, A = provider.get_kappa()
        assert kappa == 0.02
        assert A == 1.0

    def test_advance_to_exact_timestamp(self):
        data = [
            (1000.0, 0.02, 1.0),
            (2000.0, 0.05, 2.0),
        ]
        provider = HistoricalKappaProvider(data=data)
        provider.advance_to(2000.0)
        kappa, A = provider.get_kappa()
        assert kappa == 0.05
        assert A == 2.0

    def test_advance_before_any_data(self):
        data = [
            (1000.0, 0.02, 1.0),
        ]
        provider = HistoricalKappaProvider(
            data=data,
            default_kappa=0.01,
            default_A=0.5,
        )
        provider.advance_to(500.0)
        kappa, A = provider.get_kappa()
        assert kappa == 0.01
        assert A == 0.5

    def test_is_kappa_provider(self):
        provider = HistoricalKappaProvider()
        assert isinstance(provider, KappaProvider)
