"""Tests for time-decay stop loss functionality."""

import pytest
import numpy as np
import pandas as pd

from strategies.mean_reversion_bb.model import MeanReversionBB


class TestComputeTimeDecayStop:
    """Tests for compute_time_decay_stop method."""

    def test_phase_0_uses_initial_multiplier(self):
        """Before first decay boundary, uses stop_atr_multiplier."""
        model = MeanReversionBB()
        # bars_held=5, max_bars=50 -> progress=0.10 < 0.33
        stop = model.compute_time_decay_stop(5, 50, 96.0, 2.0, "long")
        expected = 96.0 - 3.0 * 2.0  # 90.0
        assert stop == pytest.approx(expected)

    def test_phase_1_uses_decay_mult_1(self):
        """Between first and second boundary, uses stop_decay_mult_1."""
        model = MeanReversionBB()
        # bars_held=17, max_bars=50 -> progress=0.34 >= 0.33
        stop = model.compute_time_decay_stop(17, 50, 96.0, 2.0, "long")
        expected = 96.0 - 2.0 * 2.0  # 92.0
        assert stop == pytest.approx(expected)

    def test_phase_2_uses_decay_mult_2(self):
        """Beyond second boundary, uses stop_decay_mult_2."""
        model = MeanReversionBB()
        # bars_held=33, max_bars=50 -> progress=0.66 >= 0.66
        stop = model.compute_time_decay_stop(33, 50, 96.0, 2.0, "long")
        expected = 96.0 - 1.0 * 2.0  # 94.0
        assert stop == pytest.approx(expected)

    def test_long_stop_tightens_over_time(self):
        """Long stop moves UP (closer to entry) as trade ages."""
        model = MeanReversionBB()
        stop_0 = model.compute_time_decay_stop(0, 50, 96.0, 2.0, "long")
        stop_1 = model.compute_time_decay_stop(17, 50, 96.0, 2.0, "long")
        stop_2 = model.compute_time_decay_stop(33, 50, 96.0, 2.0, "long")
        assert stop_0 < stop_1 < stop_2  # tightening

    def test_short_stop_tightens_over_time(self):
        """Short stop moves DOWN (closer to entry) as trade ages."""
        model = MeanReversionBB()
        stop_0 = model.compute_time_decay_stop(0, 50, 104.0, 2.0, "short")
        stop_1 = model.compute_time_decay_stop(17, 50, 104.0, 2.0, "short")
        stop_2 = model.compute_time_decay_stop(33, 50, 104.0, 2.0, "short")
        assert stop_0 > stop_1 > stop_2  # tightening


class TestGenerateOrdersAlwaysStop:
    """Tests that stops are always enforced."""

    def test_long_order_always_has_stop(self):
        """Long orders always have non-zero stop_loss."""
        model = MeanReversionBB()
        signal = {
            "signal": "long", "middle": 100.0,
            "lower_outer": 96.0, "lower_inner": 98.0,
            "upper_outer": 104.0, "upper_inner": 102.0,
        }
        orders = model.generate_orders(signal, 96.0, 10000.0, 2.0)
        assert len(orders) == 1
        assert orders[0]["stop_loss"] != 0.0
        assert orders[0]["stop_loss"] < 96.0

    def test_short_order_always_has_stop(self):
        """Short orders always have non-zero stop_loss."""
        model = MeanReversionBB()
        signal = {
            "signal": "short", "middle": 100.0,
            "lower_outer": 96.0, "lower_inner": 98.0,
            "upper_outer": 104.0, "upper_inner": 102.0,
        }
        orders = model.generate_orders(signal, 104.0, 10000.0, 2.0)
        assert len(orders) == 1
        assert orders[0]["stop_loss"] != 0.0
        assert orders[0]["stop_loss"] > 104.0

    def test_order_includes_band_ref(self):
        """Order dict includes band_ref for simulator/trader sync."""
        model = MeanReversionBB()
        signal = {
            "signal": "long", "middle": 100.0,
            "lower_outer": 96.0, "lower_inner": 98.0,
            "upper_outer": 104.0, "upper_inner": 102.0,
        }
        orders = model.generate_orders(signal, 96.0, 10000.0, 2.0)
        assert "band_ref" in orders[0]
        assert orders[0]["band_ref"] == 96.0  # lower_outer for long


class TestManageRiskTimeDecay:
    """Tests for time-decay in manage_risk."""

    def test_returns_decayed_stop_when_band_level_set(self):
        """With entry_band_level, manage_risk returns tighten_stop with new_stop."""
        model = MeanReversionBB(use_band_walking_exit=False)
        model.position_side = "long"
        model.entry_price = 96.0
        model.entry_band_level = 96.0
        model.bars_held = 0

        np.random.seed(42)
        close = pd.Series(100 + np.random.randn(50).cumsum() * 2)
        volume = pd.Series([1000.0] * 50)

        result = model.manage_risk(100.0, close, volume, atr=2.0)
        assert result["action"] == "tighten_stop"
        assert "new_stop" in result
        assert result["new_stop"] == pytest.approx(90.0)  # 96 - 3.0*2

    def test_backward_compat_without_band_level(self):
        """Without entry_band_level, falls back to old behavior."""
        model = MeanReversionBB(use_band_walking_exit=False)
        model.position_side = "long"
        model.entry_price = 96.0
        # entry_band_level is None (not set)
        model.bars_held = 0

        close = pd.Series([100.0] * 50)
        volume = pd.Series([1000.0] * 50)

        result = model.manage_risk(100.0, close, volume)
        # Should not return tighten_stop with new_stop since no band level
        if result["action"] == "tighten_stop":
            assert "new_stop" not in result  # volume spike path, no new_stop
