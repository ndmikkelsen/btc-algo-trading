"""Exchange fee models with tiered structure.

Models real-world fee schedules for:
- MEXC spot trading
- Bybit futures trading

References:
- MEXC: https://www.mexc.com/fee
- Bybit: https://www.bybit.com/en/help-center/article/Trading-Fee-Structure
"""

from dataclasses import dataclass
from enum import Enum


class FeeTier(Enum):
    """Exchange fee tiers."""

    # MEXC spot tiers
    REGULAR = "regular"
    MX_DEDUCTION = "mx_deduction"

    # Bybit futures tiers
    BYBIT_VIP0 = "bybit_vip0"
    BYBIT_VIP1 = "bybit_vip1"


@dataclass(frozen=True)
class TierSchedule:
    """Fee rates for a given tier."""

    maker: float  # as decimal (e.g. 0.0 = 0%)
    taker: float  # as decimal


# Exchange fee schedules
FEE_SCHEDULE: dict[FeeTier, TierSchedule] = {
    # MEXC spot
    FeeTier.REGULAR: TierSchedule(
        maker=0.0, taker=0.0005,
    ),
    FeeTier.MX_DEDUCTION: TierSchedule(
        maker=0.0, taker=0.0004,
    ),
    # Bybit futures
    FeeTier.BYBIT_VIP0: TierSchedule(
        maker=0.0001, taker=0.0006,  # 0.01% / 0.06%
    ),
    FeeTier.BYBIT_VIP1: TierSchedule(
        maker=0.0001, taker=0.0005,  # 0.01% / 0.05%
    ),
}


class FeeModel:
    """MEXC fee calculator with tier-aware costs.

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
        """Fee for a maker fill.

        Parameters
        ----------
        notional : float
            Trade notional in USD.

        Returns
        -------
        float
            Fee amount in USD. Always 0 on MEXC.
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
            Total fee rate.
        """
        exit_rate = self._schedule.maker if maker_both else self._schedule.taker
        return self._schedule.maker + exit_rate
