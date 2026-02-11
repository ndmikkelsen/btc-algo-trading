"""Trading economics and break-even analysis.

Calculates profitability thresholds, expected P&L, and daily projections
for the Avellaneda-Stoikov market making strategy on MEXC.
"""

from dataclasses import dataclass

from strategies.avellaneda_stoikov.fee_model import FeeModel, FeeTier


@dataclass(frozen=True)
class EconomicsReport:
    """Summary of trading economics for a given configuration."""

    fee_tier: FeeTier
    maker_rate: float
    taker_rate: float
    round_trip_rate: float  # both sides maker
    min_profitable_spread_pct: float  # as decimal
    min_profitable_spread_dollar: float  # at reference price
    reference_price: float
    typical_bbo_dollar: float
    spread_gap_dollar: float  # min_profitable - typical_bbo (positive = unprofitable)
    viable: bool  # True if min_profitable_spread <= typical_bbo


class BreakEvenCalculator:
    """Calculates profitability thresholds for market making.

    Parameters
    ----------
    fee_model : FeeModel
        Fee model to use for calculations.
    reference_price : float
        Reference BTC price for dollar conversions. Default 100_000.
    """

    def __init__(
        self,
        fee_model: FeeModel | None = None,
        reference_price: float = 100_000.0,
    ) -> None:
        self.fee_model = fee_model or FeeModel()
        self.reference_price = reference_price

    def min_profitable_spread(self, maker_both: bool = True) -> float:
        """Minimum spread (as decimal rate) to break even after fees.

        For market makers quoting both sides, the spread must exceed
        the round-trip fee cost for each completed round trip.

        Parameters
        ----------
        maker_both : bool
            If True, assume both fills are maker.

        Returns
        -------
        float
            Minimum spread as a decimal (e.g. 0.0004 = 0.04%).
        """
        return self.fee_model.round_trip_rate(maker_both=maker_both)

    def min_profitable_spread_dollar(self, maker_both: bool = True) -> float:
        """Minimum spread in dollar terms at the reference price.

        Parameters
        ----------
        maker_both : bool
            If True, assume both fills are maker.

        Returns
        -------
        float
            Minimum spread in USD.
        """
        return self.min_profitable_spread(maker_both) * self.reference_price

    def expected_pnl(
        self,
        spread_dollar: float,
        fill_rate: float,
        notional: float,
        maker_both: bool = True,
    ) -> float:
        """Expected P&L per quote cycle.

        Parameters
        ----------
        spread_dollar : float
            Quoted spread in USD.
        fill_rate : float
            Probability of both sides filling (0 to 1).
        notional : float
            Notional per side in USD.
        maker_both : bool
            If True, both fills are maker.

        Returns
        -------
        float
            Expected profit per cycle in USD.
        """
        gross_profit = spread_dollar * fill_rate
        fee_cost = self.fee_model.round_trip_cost(notional, maker_both) * fill_rate
        return gross_profit - fee_cost

    def daily_pnl_estimate(
        self,
        spread_dollar: float,
        fills_per_day: int,
        avg_notional: float,
        maker_both: bool = True,
    ) -> float:
        """Projected daily P&L.

        Parameters
        ----------
        spread_dollar : float
            Quoted spread in USD.
        fills_per_day : int
            Number of completed round-trips per day.
        avg_notional : float
            Average notional per side in USD.
        maker_both : bool
            If True, both fills are maker.

        Returns
        -------
        float
            Estimated daily P&L in USD.
        """
        gross_per_trade = spread_dollar
        fee_per_trade = self.fee_model.round_trip_cost(avg_notional, maker_both)
        net_per_trade = gross_per_trade - fee_per_trade
        return net_per_trade * fills_per_day

    def generate_report(
        self, typical_bbo_dollar: float = 0.20
    ) -> EconomicsReport:
        """Generate a full economics report.

        Parameters
        ----------
        typical_bbo_dollar : float
            Typical best bid-offer spread on BTCUSDT.

        Returns
        -------
        EconomicsReport
            Complete economics summary.
        """
        schedule = self.fee_model.schedule
        rt_rate = self.fee_model.round_trip_rate(maker_both=True)
        min_spread_pct = self.min_profitable_spread()
        min_spread_dollar = self.min_profitable_spread_dollar()
        gap = min_spread_dollar - typical_bbo_dollar

        return EconomicsReport(
            fee_tier=self.fee_model.tier,
            maker_rate=schedule.maker,
            taker_rate=schedule.taker,
            round_trip_rate=rt_rate,
            min_profitable_spread_pct=min_spread_pct,
            min_profitable_spread_dollar=min_spread_dollar,
            reference_price=self.reference_price,
            typical_bbo_dollar=typical_bbo_dollar,
            spread_gap_dollar=gap,
            viable=gap <= 0,
        )
