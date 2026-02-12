"""Kappa provider abstraction for the A-S model.

Provides different strategies for obtaining the kappa (order book intensity)
parameter:

- ConstantKappaProvider: Fixed values for tests and backtests.
- LiveKappaProvider: Real-time calibration from trade data.
- HistoricalKappaProvider: Reads from stored calibration data.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, List

from strategies.avellaneda_stoikov.orderbook import (
    KappaCalibrator,
    KappaEstimate,
    OrderBookCollector,
)


class KappaProvider(ABC):
    """Abstract base class for kappa providers.

    Subclasses must implement get_kappa() which returns the current
    (kappa, A) pair for use in the A-S model.
    """

    @abstractmethod
    def get_kappa(self) -> Tuple[float, float]:
        """Return the current (kappa, A) estimate.

        Returns:
            Tuple of (kappa, A) where:
                kappa: Fill rate decay in 1/dollar (typical 0.005-0.1).
                A: Arrival rate at best price in trades/second.
        """
        ...


class ConstantKappaProvider(KappaProvider):
    """Returns fixed kappa and A values.

    Useful for backtesting, unit tests, and as a fallback when
    live calibration data is insufficient.

    Args:
        kappa: Fixed kappa value in 1/dollar.
        A: Fixed arrival rate in trades/second.
    """

    def __init__(self, kappa: float = 0.5, A: float = 20.0):
        self._kappa = kappa
        self._A = A

    def get_kappa(self) -> Tuple[float, float]:
        return self._kappa, self._A


class LiveKappaProvider(KappaProvider):
    """Real-time kappa calibration from WebSocket trade data.

    Wraps a KappaCalibrator and OrderBookCollector to provide
    live-updating kappa estimates. Falls back to default values
    when calibration data is insufficient.

    Args:
        collector: OrderBookCollector accumulating live data.
        calibrator: KappaCalibrator for fitting the model.
        default_kappa: Fallback kappa when calibration fails.
        default_A: Fallback A when calibration fails.
    """

    def __init__(
        self,
        collector: OrderBookCollector,
        calibrator: Optional[KappaCalibrator] = None,
        default_kappa: float = 0.5,
        default_A: float = 20.0,
    ):
        self._collector = collector
        self._calibrator = calibrator or KappaCalibrator()
        self._default_kappa = default_kappa
        self._default_A = default_A
        self._last_estimate: Optional[KappaEstimate] = None

    def get_kappa(self) -> Tuple[float, float]:
        """Return calibrated (kappa, A) or fallback defaults.

        Attempts calibration from the collector's rolling window.
        If calibration fails, returns the last successful estimate
        or the default values.
        """
        estimate = self._calibrator.calibrate_from_collector(self._collector)

        if estimate is not None:
            self._last_estimate = estimate
            return estimate.kappa, estimate.A

        if self._last_estimate is not None:
            return self._last_estimate.kappa, self._last_estimate.A

        return self._default_kappa, self._default_A

    @property
    def last_estimate(self) -> Optional[KappaEstimate]:
        """The most recent successful KappaEstimate, if any."""
        return self._last_estimate


class HistoricalKappaProvider(KappaProvider):
    """Reads kappa from stored calibration data.

    Accepts a list of (timestamp, kappa, A) tuples and returns
    the most recent entry. Useful for backtesting with pre-computed
    calibration data.

    Args:
        data: List of (timestamp, kappa, A) tuples, sorted by timestamp.
        default_kappa: Fallback kappa when no data is available.
        default_A: Fallback A when no data is available.
    """

    def __init__(
        self,
        data: Optional[List[Tuple[float, float, float]]] = None,
        default_kappa: float = 0.5,
        default_A: float = 20.0,
    ):
        self._data = data or []
        self._default_kappa = default_kappa
        self._default_A = default_A
        self._index = len(self._data) - 1

    def get_kappa(self) -> Tuple[float, float]:
        """Return the most recent (kappa, A) from historical data."""
        if self._data and self._index >= 0:
            _, kappa, A = self._data[self._index]
            return kappa, A
        return self._default_kappa, self._default_A

    def advance_to(self, timestamp: float) -> None:
        """Advance the index to the latest entry at or before timestamp.

        Args:
            timestamp: Target timestamp to seek to.
        """
        self._index = -1
        for i, (ts, _, _) in enumerate(self._data):
            if ts <= timestamp:
                self._index = i
            else:
                break
