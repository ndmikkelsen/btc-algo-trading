"""Tick-level data types and OHLCV-to-tick conversion.

Provides:
- TickEvent: immutable record for a single trade tick
- OHLCVToTickConverter: synthetic tick generation from candle data
  using constrained Brownian bridge interpolation
- TradeReplayProvider: iterator over captured tick data
"""

from dataclasses import dataclass
from typing import List, Optional, Iterator

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TickEvent:
    """A single trade tick.

    Attributes:
        timestamp: Seconds since epoch (or relative to session start)
        price: Trade price in dollars
        volume: Trade volume in base currency (e.g., BTC)
        side: Trade aggressor side ("buy" or "sell")
    """

    timestamp: float
    price: float
    volume: float
    side: str  # "buy" or "sell"


class OHLCVToTickConverter:
    """Convert OHLCV candles to synthetic ticks using Brownian bridge.

    Given a candle's O, H, L, C, generates N synthetic trade events that:
    1. Start at open, end at close
    2. Touch high and low at appropriate points
    3. Stay within [low, high] at all times
    4. Distribute volume across ticks

    Algorithm:
    - Determine extreme order: if close >= open (bullish), low is hit first
    - Generate 3-segment path: open -> extreme1 -> extreme2 -> close
    - Each segment uses Brownian bridge constrained to [low, high]

    Args:
        ticks_per_candle: Number of synthetic ticks per candle
        random_seed: Seed for reproducibility
    """

    def __init__(
        self,
        ticks_per_candle: int = 100,
        random_seed: Optional[int] = None,
    ):
        self.ticks_per_candle = ticks_per_candle
        self.rng = np.random.RandomState(random_seed)

    def convert_candle(
        self,
        timestamp: float,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        duration_seconds: float,
    ) -> List[TickEvent]:
        """Convert a single OHLCV candle to synthetic ticks.

        Args:
            timestamp: Candle start timestamp (seconds)
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Total volume for the candle
            duration_seconds: Candle duration in seconds

        Returns:
            List of TickEvent objects
        """
        n = self.ticks_per_candle
        if n < 2:
            side = "buy" if close >= open_price else "sell"
            return [TickEvent(timestamp, close, volume, side)]

        prices = self._generate_path(open_price, high, low, close, n)
        times = np.linspace(
            timestamp, timestamp + duration_seconds, n, endpoint=False,
        )
        volumes = self._distribute_volume(prices, volume)

        ticks = []
        for i in range(n):
            side = "buy" if (i == 0 or prices[i] >= prices[i - 1]) else "sell"
            ticks.append(TickEvent(
                timestamp=float(times[i]),
                price=float(prices[i]),
                volume=float(volumes[i]),
                side=side,
            ))

        return ticks

    def convert_dataframe(
        self,
        df: pd.DataFrame,
        duration_seconds: float = 60.0,
    ) -> List[TickEvent]:
        """Convert an OHLCV DataFrame to synthetic ticks.

        Args:
            df: DataFrame with columns: open, high, low, close, volume
                Index should be DatetimeIndex or numeric timestamps
            duration_seconds: Duration of each candle in seconds

        Returns:
            List of TickEvent objects for all candles
        """
        all_ticks: List[TickEvent] = []

        for i, (idx, row) in enumerate(df.iterrows()):
            if hasattr(idx, 'timestamp'):
                ts = idx.timestamp()
            else:
                ts = float(i * duration_seconds)

            candle_ticks = self.convert_candle(
                timestamp=ts,
                open_price=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row.get('volume', 1.0),
                duration_seconds=duration_seconds,
            )
            all_ticks.extend(candle_ticks)

        return all_ticks

    def _generate_path(
        self,
        open_price: float,
        high: float,
        low: float,
        close: float,
        n: int,
    ) -> np.ndarray:
        """Generate a constrained price path from open to close.

        Uses a 3-segment Brownian bridge:
        1. Open -> first extreme
        2. First extreme -> second extreme
        3. Second extreme -> close
        """
        # Bullish: hit low first then high; Bearish: hit high first then low
        if close >= open_price:
            extreme1, extreme2 = low, high
        else:
            extreme1, extreme2 = high, low

        # Random split points for extreme touches
        t1 = self.rng.uniform(0.1, 0.4)
        t2 = self.rng.uniform(0.6, 0.9)

        n1 = max(2, int(n * t1))
        n2 = max(2, int(n * (t2 - t1)))
        n3 = max(2, n - n1 - n2)

        seg1 = self._brownian_bridge(open_price, extreme1, n1)
        seg2 = self._brownian_bridge(extreme1, extreme2, n2)
        seg3 = self._brownian_bridge(extreme2, close, n3)

        path = np.concatenate([seg1, seg2[1:], seg3[1:]])

        # Pad or trim to exactly n points
        if len(path) < n:
            path = np.append(path, np.full(n - len(path), close))
        elif len(path) > n:
            path = path[:n]

        path = np.clip(path, low, high)
        path[0] = open_price
        path[-1] = close

        return path

    def _brownian_bridge(
        self,
        start: float,
        end: float,
        n: int,
    ) -> np.ndarray:
        """Generate a Brownian bridge from start to end with n points."""
        if n <= 1:
            return np.array([start])
        if n == 2:
            return np.array([start, end])

        t = np.linspace(0, 1, n)
        dt = 1.0 / (n - 1)

        sigma = abs(end - start) * 0.3 + 1e-10

        increments = self.rng.normal(0, sigma * np.sqrt(dt), n - 1)
        W = np.zeros(n)
        W[1:] = np.cumsum(increments)

        bridge = start + (end - start) * t + (W - t * W[-1])
        return bridge

    def _distribute_volume(
        self,
        prices: np.ndarray,
        total_volume: float,
    ) -> np.ndarray:
        """Distribute volume across ticks proportionally to price movement."""
        if len(prices) < 2:
            return np.array([total_volume])

        changes = np.abs(np.diff(prices))
        changes = np.append(changes[0] if changes[0] > 0 else 1e-10, changes)

        total_change = changes.sum()
        if total_change > 0:
            volumes = changes / total_change * total_volume
        else:
            volumes = np.full(len(prices), total_volume / len(prices))

        return volumes


class TradeReplayProvider:
    """Iterator over captured tick data.

    Wraps a list of TickEvents for use with TickSimulator.
    Supports iteration, length queries, and indexing.

    Args:
        ticks: Pre-loaded list of TickEvent objects
    """

    def __init__(self, ticks: List[TickEvent]):
        self._ticks = list(ticks)

    def __iter__(self) -> Iterator[TickEvent]:
        return iter(self._ticks)

    def __len__(self) -> int:
        return len(self._ticks)

    def __getitem__(self, index):
        return self._ticks[index]

    @property
    def start_time(self) -> float:
        """Timestamp of the first tick."""
        return self._ticks[0].timestamp if self._ticks else 0.0

    @property
    def end_time(self) -> float:
        """Timestamp of the last tick."""
        return self._ticks[-1].timestamp if self._ticks else 0.0

    @property
    def duration(self) -> float:
        """Total duration in seconds."""
        return self.end_time - self.start_time
