"""Unit tests for the MEXC fee model."""

import pytest

from strategies.avellaneda_stoikov.fee_model import (
    FeeModel,
    FeeTier,
    FEE_SCHEDULE,
    TierSchedule,
)


class TestFeeSchedule:
    """Verify the fee schedule constants match MEXC rates."""

    def test_regular_tier_rates(self):
        s = FEE_SCHEDULE[FeeTier.REGULAR]
        assert s.maker == 0.0
        assert s.taker == 0.0005

    def test_mx_deduction_tier_rates(self):
        s = FEE_SCHEDULE[FeeTier.MX_DEDUCTION]
        assert s.maker == 0.0
        assert s.taker == 0.0004

    def test_all_tiers_present(self):
        assert set(FEE_SCHEDULE.keys()) == set(FeeTier)


class TestFeeModel:
    """Tests for FeeModel calculations."""

    def test_default_is_regular(self):
        model = FeeModel()
        assert model.tier == FeeTier.REGULAR

    def test_maker_fee_regular_is_zero(self):
        model = FeeModel(FeeTier.REGULAR)
        # $100k notional × 0% = $0
        assert model.maker_fee(100_000) == pytest.approx(0.0)

    def test_taker_fee_regular(self):
        model = FeeModel(FeeTier.REGULAR)
        # $100k × 0.05% = $50
        assert model.taker_fee(100_000) == pytest.approx(50.0)

    def test_maker_fee_mx_deduction_is_zero(self):
        model = FeeModel(FeeTier.MX_DEDUCTION)
        assert model.maker_fee(100_000) == pytest.approx(0.0)

    def test_taker_fee_mx_deduction(self):
        model = FeeModel(FeeTier.MX_DEDUCTION)
        # $100k × 0.04% = $40
        assert model.taker_fee(100_000) == pytest.approx(40.0)

    def test_round_trip_cost_maker_both_is_zero(self):
        model = FeeModel(FeeTier.REGULAR)
        # 2 × $0 = $0
        cost = model.round_trip_cost(100_000, maker_both=True)
        assert cost == pytest.approx(0.0)

    def test_round_trip_cost_maker_taker(self):
        model = FeeModel(FeeTier.REGULAR)
        # $0 (maker) + $50 (taker) = $50
        cost = model.round_trip_cost(100_000, maker_both=False)
        assert cost == pytest.approx(50.0)

    def test_round_trip_rate_maker_both_is_zero(self):
        model = FeeModel(FeeTier.REGULAR)
        assert model.round_trip_rate(maker_both=True) == pytest.approx(0.0)

    def test_round_trip_rate_maker_taker(self):
        model = FeeModel(FeeTier.REGULAR)
        # 0.0 + 0.0005 = 0.0005
        assert model.round_trip_rate(maker_both=False) == pytest.approx(0.0005)

    def test_zero_notional(self):
        model = FeeModel()
        assert model.maker_fee(0) == 0.0
        assert model.taker_fee(0) == 0.0
        assert model.round_trip_cost(0) == 0.0

    def test_schedule_property(self):
        model = FeeModel(FeeTier.MX_DEDUCTION)
        assert isinstance(model.schedule, TierSchedule)
        assert model.schedule.maker == 0.0
        assert model.schedule.taker == 0.0004
