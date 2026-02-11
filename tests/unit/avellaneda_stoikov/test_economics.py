"""Unit tests for the break-even calculator and economics report."""

import pytest

from strategies.avellaneda_stoikov.fee_model import FeeModel, FeeTier
from strategies.avellaneda_stoikov.economics import BreakEvenCalculator


class TestMinProfitableSpread:
    """Tests for break-even spread calculations."""

    def test_regular_tier_min_spread_is_zero(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        # 2 × 0% = 0%
        assert calc.min_profitable_spread() == pytest.approx(0.0)

    def test_regular_tier_min_spread_dollar_is_zero(self):
        calc = BreakEvenCalculator(
            FeeModel(FeeTier.REGULAR), reference_price=100_000
        )
        # 0% of $100k = $0
        assert calc.min_profitable_spread_dollar() == pytest.approx(0.0)

    def test_mx_deduction_min_spread_is_zero(self):
        calc = BreakEvenCalculator(
            FeeModel(FeeTier.MX_DEDUCTION), reference_price=100_000
        )
        assert calc.min_profitable_spread_dollar() == pytest.approx(0.0)

    def test_maker_taker_mixed_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        # 0% + 0.05% = 0.05%
        assert calc.min_profitable_spread(maker_both=False) == pytest.approx(
            0.0005
        )

    def test_default_fee_model(self):
        calc = BreakEvenCalculator()
        assert calc.fee_model.tier == FeeTier.REGULAR


class TestExpectedPnl:
    """Tests for per-cycle P&L calculation."""

    def test_positive_pnl_any_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        # Spread of $100, 100% fill rate, $100k notional
        pnl = calc.expected_pnl(
            spread_dollar=100.0, fill_rate=1.0, notional=100_000
        )
        # gross = $100, fees = $0, net = $100
        assert pnl == pytest.approx(100.0)

    def test_positive_pnl_tight_spread(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        # Spread of $0.20 (typical BBO) — still profitable with 0% maker!
        pnl = calc.expected_pnl(
            spread_dollar=0.20, fill_rate=1.0, notional=100_000
        )
        # gross = $0.20, fees = $0, net = $0.20
        assert pnl == pytest.approx(0.20)

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
        # gross = $50, fees = $0, net = $50
        assert pnl == pytest.approx(50.0)


class TestDailyPnlEstimate:
    """Tests for daily P&L projections."""

    def test_daily_pnl_profitable(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        # $100 spread, 50 fills/day, $100k notional
        daily = calc.daily_pnl_estimate(
            spread_dollar=100.0, fills_per_day=50, avg_notional=100_000
        )
        # per trade: $100 - $0 = $100; daily: $100 × 50 = $5000
        assert daily == pytest.approx(5000.0)

    def test_daily_pnl_tight_spread_still_profitable(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        daily = calc.daily_pnl_estimate(
            spread_dollar=0.20, fills_per_day=500, avg_notional=100_000
        )
        # per trade: $0.20 - $0 = $0.20; daily: $0.20 × 500 = $100
        assert daily == pytest.approx(100.0)

    def test_zero_fills_zero_pnl(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        daily = calc.daily_pnl_estimate(
            spread_dollar=100.0, fills_per_day=0, avg_notional=100_000
        )
        assert daily == 0.0


class TestEconomicsReport:
    """Tests for the economics report generator."""

    def test_regular_tier_report_viable(self):
        calc = BreakEvenCalculator(
            FeeModel(FeeTier.REGULAR), reference_price=100_000
        )
        report = calc.generate_report(typical_bbo_dollar=0.20)

        assert report.fee_tier == FeeTier.REGULAR
        assert report.maker_rate == 0.0
        assert report.taker_rate == 0.0005
        assert report.round_trip_rate == pytest.approx(0.0)
        assert report.min_profitable_spread_dollar == pytest.approx(0.0)
        assert report.typical_bbo_dollar == 0.20
        assert report.spread_gap_dollar == pytest.approx(-0.20)
        assert report.viable is True

    def test_mx_deduction_report_viable(self):
        calc = BreakEvenCalculator(
            FeeModel(FeeTier.MX_DEDUCTION), reference_price=100_000
        )
        report = calc.generate_report(typical_bbo_dollar=0.20)
        assert report.viable is True
        assert report.min_profitable_spread_dollar == pytest.approx(0.0)

    def test_report_reference_price(self):
        calc = BreakEvenCalculator(
            FeeModel(FeeTier.REGULAR), reference_price=50_000
        )
        report = calc.generate_report()
        assert report.reference_price == 50_000
        # $50k × 0% = $0
        assert report.min_profitable_spread_dollar == pytest.approx(0.0)

    def test_report_is_frozen_dataclass(self):
        calc = BreakEvenCalculator(FeeModel(FeeTier.REGULAR))
        report = calc.generate_report()
        with pytest.raises(AttributeError):
            report.viable = True
