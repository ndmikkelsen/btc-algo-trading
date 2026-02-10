"""Bybit fee model with tiered structure.

Models the real-world fee schedule for Bybit spot trading,
including VIP tiers and the Market Maker Program.

Reference: https://www.bybit.com/en/help-center/article/Fee-Structure
"""

from dataclasses import dataclass
from enum import Enum


class FeeTier(Enum):
    """Bybit spot fee tiers (as of 2025)."""

    REGULAR = "regular"
    VIP1 = "vip1"
    VIP2 = "vip2"
    MARKET_MAKER = "market_maker"


@dataclass(frozen=True)
class TierSchedule:
    """Fee rates for a given tier."""

    maker: float  # as decimal (e.g. 0.0002 = 0.02%)
    taker: float  # as decimal
    min_monthly_volume: float  # USD threshold to qualify


# Bybit spot fee schedule (2025)
FEE_SCHEDULE: dict[FeeTier, TierSchedule] = {
    FeeTier.REGULAR: TierSchedule(
        maker=0.0002, taker=0.00055, min_monthly_volume=0.0
    ),
    FeeTier.VIP1: TierSchedule(
        maker=0.00018, taker=0.0004, min_monthly_volume=1_000_000.0
    ),
    FeeTier.VIP2: TierSchedule(
        maker=0.00016, taker=0.000375, min_monthly_volume=5_000_000.0
    ),
    FeeTier.MARKET_MAKER: TierSchedule(
        maker=-0.00005, taker=0.00025, min_monthly_volume=10_000_000.0
    ),
}


class FeeModel:
    """Bybit fee calculator with tier-aware costs.

    Parameters
    ----------
    tier : FeeTier
        Fee tier to use. Defaults to REGULAR.
    """

    def __init__(self, tier: FeeTier = FeeTier.REGULAR) -> None:
        self.tier = tier
        self._schedule = FEE_SCHEDULE[tier]

    @property
    def schedule(self) -> TierSchedule:
        return self._schedule

    def maker_fee(self, notional: float) -> float:
        """Fee (or rebate) for a maker fill.

        Parameters
        ----------
        notional : float
            Trade notional in USD.

        Returns
        -------
        float
            Fee amount in USD. Negative means rebate.
        """
        return notional * self._schedule.maker

    def taker_fee(self, notional: float) -> float:
        """Fee for a taker fill.

        Parameters
        ----------
        notional : float
            Trade notional in USD.

        Returns
        -------
        float
            Fee amount in USD.
        """
        return notional * self._schedule.taker

    def round_trip_cost(self, notional: float, maker_both: bool = True) -> float:
        """Round-trip trading cost.

        Parameters
        ----------
        notional : float
            Trade notional in USD (one side).
        maker_both : bool
            If True, assume both entry and exit are maker fills.
            If False, assume entry is maker and exit is taker.

        Returns
        -------
        float
            Total fee in USD for the round trip.
        """
        entry_fee = self.maker_fee(notional)
        exit_fee = self.maker_fee(notional) if maker_both else self.taker_fee(notional)
        return entry_fee + exit_fee

    def round_trip_rate(self, maker_both: bool = True) -> float:
        """Round-trip fee as a decimal rate.

        Parameters
        ----------
        maker_both : bool
            If True, both sides are maker.

        Returns
        -------
        float
            Total fee rate (e.g. 0.0004 for 0.04%).
        """
        exit_rate = self._schedule.maker if maker_both else self._schedule.taker
        return self._schedule.maker + exit_rate

    @staticmethod
    def effective_tier(monthly_volume: float) -> FeeTier:
        """Determine which fee tier applies for a given monthly volume.

        Parameters
        ----------
        monthly_volume : float
            Trading volume in USD over the past 30 days.

        Returns
        -------
        FeeTier
            The highest tier the volume qualifies for.
        """
        best = FeeTier.REGULAR
        for tier, schedule in FEE_SCHEDULE.items():
            if tier == FeeTier.MARKET_MAKER:
                continue  # requires application, not just volume
            if monthly_volume >= schedule.min_monthly_volume:
                best = tier
        return best
