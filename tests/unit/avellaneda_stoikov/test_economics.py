"""Unit tests for the break-even calculator and economics report."""

import pytest

from strategies.avellaneda_stoikov.fee_model import FeeModel, FeeTier
from strategies.avellaneda_stoikov.economics import BreakEvenCalculator


class TestMinProfitableSpread:
    """Tests for break-even spread calculations."""

    def test_regular_tier_min_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        # 2 × 0.02% = 0.04%
        assert calc.min_profitable_spread() == pytest.approx(0.0004)

    def test_regular_tier_min_spread_dollar(self):
        calc = BreakEvenCalculator(
            FeeModel(FeeTier.REGULAR), reference_price=100_000
        )
        # 0.04% of $100k = $40
        assert calc.min_profitable_spread_dollar() == pytest.approx(40.0)

    def test_market_maker_min_spread_negative(self):
        calc = BreakEvenCalculator(
            FeeModel(FeeTier.MARKET_MAKER), reference_price=100_000
        )
        # 2 × (-0.005%) = -0.01% → -$10
        spread = calc.min_profitable_spread_dollar()
        assert spread < 0
        assert spread == pytest.approx(-10.0)

    def test_vip1_min_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.VIP1))
        # 2 × 0.018% = 0.036%
        assert calc.min_profitable_spread() == pytest.approx(0.00036)

    def test_vip2_min_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.VIP2))
        # 2 × 0.016% = 0.032%
        assert calc.min_profitable_spread() == pytest.approx(0.00032)

    def test_maker_taker_mixed_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        # 0.02% + 0.055% = 0.075%
        assert calc.min_profitable_spread(maker_both=False) == pytest.approx(
            0.00075
        )

    def test_default_fee_model(self):
        calc = BreakEvenCalculator()
        assert calc.fee_model.tier == FeeTier.REGULAR


class TestExpectedPnl:
    """Tests for per-cycle P&L calculation."""

    def test_positive_pnl_wide_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        # Spread of $100, 100% fill rate, $100k notional
        pnl = calc.expected_pnl(
            spread_dollar=100.0, fill_rate=1.0, notional=100_000
        )
        # gross = $100, fees = $40, net = $60
        assert pnl == pytest.approx(60.0)

    def test_negative_pnl_tight_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        # Spread of $10, 100% fill rate, $100k notional
        pnl = calc.expected_pnl(
            spread_dollar=10.0, fill_rate=1.0, notional=100_000
        )
        # gross = $10, fees = $40, net = -$30
        assert pnl == pytest.approx(-30.0)

    def test_zero_fill_rate_zero_pnl(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        pnl = calc.expected_pnl(
            spread_dollar=100.0, fill_rate=0.0, notional=100_000
        )
        assert pnl == 0.0

    def test_partial_fill_rate(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        pnl = calc.expected_pnl(
            spread_dollar=100.0, fill_rate=0.5, notional=100_000
        )
        # gross = $50, fees = $20, net = $30
        assert pnl == pytest.approx(30.0)

    def test_market_maker_earns_on_tight_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.MARKET_MAKER))
        # Spread of $0.20 (typical BBO), 100% fill rate, $100k notional
        pnl = calc.expected_pnl(
            spread_dollar=0.20, fill_rate=1.0, notional=100_000
        )
        # gross = $0.20, fees = -$10 (rebate), net = $10.20
        assert pnl == pytest.approx(10.20)


class TestDailyPnlEstimate:
    """Tests for daily P&L projections."""

    def test_daily_pnl_profitable(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        # $100 spread, 50 fills/day, $100k notional
        daily = calc.daily_pnl_estimate(
            spread_dollar=100.0, fills_per_day=50, avg_notional=100_000
        )
        # per trade: $100 - $40 = $60; daily: $60 × 50 = $3000
        assert daily == pytest.approx(3000.0)

    def test_daily_pnl_unprofitable(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        daily = calc.daily_pnl_estimate(
            spread_dollar=10.0, fills_per_day=100, avg_notional=100_000
        )
        # per trade: $10 - $40 = -$30; daily: -$30 × 100 = -$3000
        assert daily == pytest.approx(-3000.0)

    def test_daily_pnl_market_maker_tight_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.MARKET_MAKER))
        daily = calc.daily_pnl_estimate(
            spread_dollar=0.20, fills_per_day=500, avg_notional=100_000
        )
        # per trade: $0.20 - (-$10) = $10.20; daily: $10.20 × 500 = $5100
        assert daily == pytest.approx(5100.0)

    def test_zero_fills_zero_pnl(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        daily = calc.daily_pnl_estimate(
            spread_dollar=100.0, fills_per_day=0, avg_notional=100_000
        )
        assert daily == 0.0


class TestEconomicsReport:
    """Tests for the economics report generator."""

    def test_regular_tier_report(self):
        calc = BreakEvenCalculator(
            FeeModel(FeeTier.REGULAR), reference_price=100_000
        )
        report = calc.generate_report(typical_bbo_dollar=0.20)

        assert report.fee_tier == FeeTier.REGULAR
        assert report.maker_rate == 0.0002
        assert report.taker_rate == 0.00055
        assert report.round_trip_rate == pytest.approx(0.0004)
        assert report.min_profitable_spread_dollar == pytest.approx(40.0)
        assert report.typical_bbo_dollar == 0.20
        assert report.spread_gap_dollar == pytest.approx(39.80)
        assert report.viable is False

    def test_market_maker_report_viable(self):
        calc = BreakEvenCalculator(
            FeeModel(FeeTier.MARKET_MAKER), reference_price=100_000
        )
        report = calc.generate_report(typical_bbo_dollar=0.20)

        assert report.viable is True
        assert report.min_profitable_spread_dollar < 0
        assert report.spread_gap_dollar < 0

    def test_report_reference_price(self):
        calc = BreakEvenCalculator(
            FeeModel(FeeTier.REGULAR), reference_price=50_000
        )
        report = calc.generate_report()
        assert report.reference_price == 50_000
        # $50k × 0.04% = $20
        assert report.min_profitable_spread_dollar == pytest.approx(20.0)

    def test_report_is_frozen_dataclass(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        report = calc.generate_report()
        with pytest.raises(AttributeError):
            report.viable = True
