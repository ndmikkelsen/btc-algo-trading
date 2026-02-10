"""Order book data pipeline for kappa calibration.

Collects L2 order book snapshots and public trade data from Bybit,
then calibrates the exponential fill rate model:

    lambda(delta) = A * exp(-kappa * delta)

where:
    - delta: distance from mid price in dollars
    - A: arrival rate at the best price (trades/second)
    - kappa: fill rate decay per dollar of depth (1/dollar)

The calibration uses rolling windows (default 10 minutes) of trade data,
binning trades by their distance from mid price and fitting log-linear
regression: log(lambda) = log(A) - kappa * delta.
"""

import math
from collections import deque
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np


@dataclass
class OrderBookSnapshot:
    """A point-in-time snapshot of L2 order book data.

    Attributes:
        bids: List of (price, qty) tuples, sorted best-to-worst (descending price).
        asks: List of (price, qty) tuples, sorted best-to-worst (ascending price).
        timestamp: Unix timestamp in seconds (float).
        mid_price: Computed mid price = (best_bid + best_ask) / 2.
    """

    bids: List[Tuple[float, float]]
    asks: List[Tuple[float, float]]
    timestamp: float
    mid_price: float = 0.0

    def __post_init__(self):
        if self.mid_price == 0.0 and self.bids and self.asks:
            self.mid_price = (self.bids[0][0] + self.asks[0][0]) / 2.0


@dataclass
class TradeRecord:
    """A single public trade for arrival rate estimation.

    Attributes:
        price: Trade execution price in dollars.
        qty: Trade quantity in base currency.
        timestamp: Unix timestamp in seconds (float).
        side: "Buy" or "Sell".
    """

    price: float
    qty: float
    timestamp: float
    side: str


@dataclass
class KappaEstimate:
    """Result of kappa calibration.

    Attributes:
        kappa: Fill rate decay parameter (1/dollar).
        A: Arrival rate at best price (trades/second).
        n_trades: Number of trades used in calibration.
        r_squared: Goodness of fit (0 to 1).
        window_seconds: Length of the calibration window.
    """

    kappa: float
    A: float
    n_trades: int
    r_squared: float = 0.0
    window_seconds: float = 600.0


class OrderBookCollector:
    """Accumulates order book snapshots and trades for calibration.

    Maintains a rolling window of snapshots and trades, providing
    the raw data needed by KappaCalibrator.

    Args:
        max_snapshots: Maximum number of snapshots to retain.
        max_trades: Maximum number of trades to retain.
    """

    def __init__(
        self,
        max_snapshots: int = 1000,
        max_trades: int = 50000,
    ):
        self.max_snapshots = max_snapshots
        self.max_trades = max_trades
        self.snapshots: deque[OrderBookSnapshot] = deque(maxlen=max_snapshots)
        self.trades: deque[TradeRecord] = deque(maxlen=max_trades)

    def add_snapshot(self, snapshot: OrderBookSnapshot) -> None:
        """Add an order book snapshot."""
        self.snapshots.append(snapshot)

    def add_trade(self, trade: TradeRecord) -> None:
        """Add a public trade record."""
        self.trades.append(trade)

    def get_trades_in_window(self, window_seconds: float = 600.0) -> List[TradeRecord]:
        """Return trades within the last `window_seconds` seconds.

        Args:
            window_seconds: Lookback window in seconds (default 600 = 10 min).

        Returns:
            List of TradeRecord within the window.
        """
        if not self.trades:
            return []
        cutoff = self.trades[-1].timestamp - window_seconds
        return [t for t in self.trades if t.timestamp >= cutoff]

    def get_latest_mid_price(self) -> Optional[float]:
        """Return the mid price from the most recent snapshot, or None."""
        if self.snapshots:
            return self.snapshots[-1].mid_price
        return None

    @property
    def trade_count(self) -> int:
        return len(self.trades)

    @property
    def snapshot_count(self) -> int:
        return len(self.snapshots)


class KappaCalibrator:
    """Calibrates kappa from trade arrival rates vs distance from mid.

    Fits the exponential model lambda(delta) = A * exp(-kappa * delta)
    using log-linear least squares on binned trade data.

    Args:
        bin_width: Width of distance bins in dollars (default $1.0).
        min_trades: Minimum trades required to attempt calibration.
        window_seconds: Rolling window length in seconds (default 600 = 10 min).
        max_delta: Maximum distance from mid to consider, in dollars.
    """

    def __init__(
        self,
        bin_width: float = 1.0,
        min_trades: int = 30,
        window_seconds: float = 600.0,
        max_delta: float = 500.0,
    ):
        self.bin_width = bin_width
        self.min_trades = min_trades
        self.window_seconds = window_seconds
        self.max_delta = max_delta

    def calibrate(
        self,
        trades: List[TradeRecord],
        mid_price: float,
    ) -> Optional[KappaEstimate]:
        """Calibrate kappa from a list of trades.

        Bins trades by their distance from mid_price, computes arrival rate
        per bin, then fits log(lambda) = log(A) - kappa * delta.

        Args:
            trades: List of recent trades.
            mid_price: Current mid price for computing distances.

        Returns:
            KappaEstimate if calibration succeeds, None if insufficient data.
        """
        if len(trades) < self.min_trades:
            return None

        # Compute delta for each trade
        deltas = [abs(t.price - mid_price) for t in trades]

        # Determine time span
        timestamps = [t.timestamp for t in trades]
        time_span = max(timestamps) - min(timestamps)
        if time_span <= 0:
            return None

        # Bin trades by distance
        n_bins = max(1, int(self.max_delta / self.bin_width))
        bin_counts = np.zeros(n_bins)
        for d in deltas:
            bin_idx = int(d / self.bin_width)
            if 0 <= bin_idx < n_bins:
                bin_counts[bin_idx] += 1

        # Convert to arrival rate (trades per second)
        arrival_rates = bin_counts / time_span

        # Filter bins with nonzero arrivals for log-linear fit
        bin_centers = np.array([
            (i + 0.5) * self.bin_width for i in range(n_bins)
        ])
        mask = arrival_rates > 0
        if mask.sum() < 2:
            return None

        x = bin_centers[mask]
        y = np.log(arrival_rates[mask])

        # Log-linear least squares: y = log(A) - kappa * x
        kappa, log_A, r_squared = self._fit_log_linear(x, y)

        if kappa <= 0:
            return None

        A = math.exp(log_A)

        return KappaEstimate(
            kappa=kappa,
            A=A,
            n_trades=len(trades),
            r_squared=r_squared,
            window_seconds=time_span,
        )

    def calibrate_from_collector(
        self,
        collector: OrderBookCollector,
    ) -> Optional[KappaEstimate]:
        """Convenience method: calibrate from an OrderBookCollector.

        Args:
            collector: OrderBookCollector with accumulated trade data.

        Returns:
            KappaEstimate or None.
        """
        mid_price = collector.get_latest_mid_price()
        if mid_price is None:
            return None

        trades = collector.get_trades_in_window(self.window_seconds)
        return self.calibrate(trades, mid_price)

    @staticmethod
    def _fit_log_linear(
        x: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[float, float, float]:
        """Fit y = a + b*x via least squares, return (-b, a, R^2).

        Since our model is log(lambda) = log(A) - kappa*delta,
        the slope b = -kappa, intercept a = log(A).

        Returns:
            Tuple of (kappa, log_A, r_squared).
        """
        n = len(x)
        if n < 2:
            return 0.0, 0.0, 0.0

        x_mean = np.mean(x)
        y_mean = np.mean(y)

        ss_xx = np.sum((x - x_mean) ** 2)
        ss_xy = np.sum((x - x_mean) * (y - y_mean))
        ss_yy = np.sum((y - y_mean) ** 2)

        if ss_xx == 0:
            return 0.0, float(y_mean), 0.0

        slope = ss_xy / ss_xx  # b (negative for decaying function)
        intercept = y_mean - slope * x_mean  # a = log(A)

        # R^2
        if ss_yy == 0:
            r_squared = 1.0 if ss_xy == 0 else 0.0
        else:
            r_squared = (ss_xy ** 2) / (ss_xx * ss_yy)

        kappa = -slope  # kappa = -b (positive for decay)
        return float(kappa), float(intercept), float(r_squared)
