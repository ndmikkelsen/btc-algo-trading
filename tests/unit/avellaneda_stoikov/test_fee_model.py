"""Unit tests for the Bybit fee model."""

import pytest

from strategies.avellaneda_stoikov.fee_model import (
    FeeModel,
    FeeTier,
    FEE_SCHEDULE,
    TierSchedule,
)


class TestFeeSchedule:
    """Verify the fee schedule constants match Bybit 2025 rates."""

    def test_regular_tier_rates(self):
        s = FEE_SCHEDULE[FeeTier.REGULAR]
        assert s.maker == 0.0002
        assert s.taker == 0.00055

    def test_vip1_tier_rates(self):
        s = FEE_SCHEDULE[FeeTier.VIP1]
        assert s.maker == 0.00018
        assert s.taker == 0.0004

    def test_vip2_tier_rates(self):
        s = FEE_SCHEDULE[FeeTier.VIP2]
        assert s.maker == 0.00016
        assert s.taker == 0.000375

    def test_market_maker_has_rebate(self):
        s = FEE_SCHEDULE[FeeTier.MARKET_MAKER]
        assert s.maker < 0  # rebate
        assert s.maker == -0.00005
        assert s.taker == 0.00025

    def test_all_tiers_present(self):
        assert set(FEE_SCHEDULE.keys()) == set(FeeTier)


class TestFeeModel:
    """Tests for FeeModel calculations."""

    def test_default_is_regular(self):
        model = FeeModel()
        assert model.tier == FeeTier.REGULAR

    def test_maker_fee_regular(self):
        model = FeeModel(FeeTier.REGULAR)
        # $100k notional × 0.02% = $20
        assert model.maker_fee(100_000) == pytest.approx(20.0)

    def test_taker_fee_regular(self):
        model = FeeModel(FeeTier.REGULAR)
        # $100k × 0.055% = $55
        assert model.taker_fee(100_000) == pytest.approx(55.0)

    def test_maker_fee_market_maker_is_rebate(self):
        model = FeeModel(FeeTier.MARKET_MAKER)
        fee = model.maker_fee(100_000)
        assert fee < 0  # rebate
        assert fee == pytest.approx(-5.0)

    def test_round_trip_cost_maker_both(self):
        model = FeeModel(FeeTier.REGULAR)
        # 2 × $20 = $40
        cost = model.round_trip_cost(100_000, maker_both=True)
        assert cost == pytest.approx(40.0)

    def test_round_trip_cost_maker_taker(self):
        model = FeeModel(FeeTier.REGULAR)
        # $20 (maker) + $55 (taker) = $75
        cost = model.round_trip_cost(100_000, maker_both=False)
        assert cost == pytest.approx(75.0)

    def test_round_trip_rate_maker_both(self):
        model = FeeModel(FeeTier.REGULAR)
        assert model.round_trip_rate(maker_both=True) == pytest.approx(0.0004)

    def test_round_trip_rate_maker_taker(self):
        model = FeeModel(FeeTier.REGULAR)
        # 0.0002 + 0.00055 = 0.00075
        assert model.round_trip_rate(maker_both=False) == pytest.approx(0.00075)

    def test_round_trip_market_maker_negative(self):
        model = FeeModel(FeeTier.MARKET_MAKER)
        # 2 × (-0.00005) = -0.0001 → net rebate
        cost = model.round_trip_cost(100_000, maker_both=True)
        assert cost < 0  # net rebate
        assert cost == pytest.approx(-10.0)

    def test_zero_notional(self):
        model = FeeModel()
        assert model.maker_fee(0) == 0.0
        assert model.taker_fee(0) == 0.0
        assert model.round_trip_cost(0) == 0.0

    def test_schedule_property(self):
        model = FeeModel(FeeTier.VIP2)
        assert isinstance(model.schedule, TierSchedule)
        assert model.schedule.maker == 0.00016


class TestEffectiveTier:
    """Tests for volume-based tier determination."""

    def test_zero_volume_is_regular(self):
        assert FeeModel.effective_tier(0) == FeeTier.REGULAR

    def test_small_volume_is_regular(self):
        assert FeeModel.effective_tier(500_000) == FeeTier.REGULAR

    def test_1m_volume_is_vip1(self):
        assert FeeModel.effective_tier(1_000_000) == FeeTier.VIP1

    def test_5m_volume_is_vip2(self):
        assert FeeModel.effective_tier(5_000_000) == FeeTier.VIP2

    def test_large_volume_is_vip2_not_market_maker(self):
        # Market Maker requires application, not just volume
        assert FeeModel.effective_tier(100_000_000) == FeeTier.VIP2

    def test_boundary_vip1(self):
        assert FeeModel.effective_tier(999_999) == FeeTier.REGULAR
        assert FeeModel.effective_tier(1_000_000) == FeeTier.VIP1
