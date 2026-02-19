"""Tests for tuned MRBB parameter presets.

Validates that all 6 presets (default + 5 tuned) load, validate,
and construct MeanReversionBB models without error. Also checks
that each tuned preset has the expected parameter differences from
the default baseline.
"""

import pytest

from strategies.mean_reversion_bb.presets import PresetManager
from strategies.mean_reversion_bb.model import MeanReversionBB


# Keys accepted by MeanReversionBB constructor (excludes min_squeeze_duration)
MODEL_PARAMS = {
    "bb_period",
    "bb_std_dev",
    "bb_inner_std_dev",
    "vwap_period",
    "vwap_confirmation_pct",
    "kc_period",
    "kc_atr_multiplier",
    "rsi_period",
    "rsi_oversold",
    "rsi_overbought",
    "adx_period",
    "adx_threshold",
    "use_regime_filter",
    "reversion_target",
    "max_holding_bars",
    "risk_per_trade",
    "max_position_pct",
    "stop_atr_multiplier",
}

ALL_PRESET_NAMES = [
    "default",
    "conservative",
    "aggressive",
    "long_only",
    "ranging",
    "high_rr",
]


@pytest.fixture
def pm():
    return PresetManager()


@pytest.fixture
def default_preset(pm):
    return pm.load("default")


class TestAllPresetsLoad:
    """Every preset loads without error."""

    @pytest.mark.parametrize("name", ALL_PRESET_NAMES)
    def test_all_presets_load_successfully(self, pm, name):
        preset = pm.load(name)
        assert isinstance(preset, dict)
        assert "name" in preset
        assert preset["name"] == name


class TestAllPresetsValidate:
    """Every preset passes ParamRegistry validation."""

    @pytest.mark.parametrize("name", ALL_PRESET_NAMES)
    def test_all_presets_validate(self, pm, name):
        preset = pm.load(name)
        # Should not raise
        pm.validate(preset)


class TestAllPresetsConstructModel:
    """Every preset can construct a MeanReversionBB model."""

    @pytest.mark.parametrize("name", ALL_PRESET_NAMES)
    def test_all_presets_construct_model(self, pm, name):
        preset = pm.load(name)
        model_params = {k: v for k, v in preset.items() if k in MODEL_PARAMS}
        model = MeanReversionBB(**model_params)
        assert isinstance(model, MeanReversionBB)


class TestConservativePreset:
    """Conservative preset has wider bands and reduced risk."""

    def test_conservative_has_wider_bands(self, pm, default_preset):
        conservative = pm.load("conservative")
        assert conservative["bb_std_dev"] > default_preset["bb_std_dev"]

    def test_conservative_has_stricter_adx(self, pm, default_preset):
        conservative = pm.load("conservative")
        assert conservative["adx_threshold"] > default_preset["adx_threshold"]

    def test_conservative_has_lower_risk(self, pm, default_preset):
        conservative = pm.load("conservative")
        assert conservative["risk_per_trade"] < default_preset["risk_per_trade"]

    def test_conservative_has_smaller_position(self, pm, default_preset):
        conservative = pm.load("conservative")
        assert conservative["max_position_pct"] < default_preset["max_position_pct"]


class TestAggressivePreset:
    """Aggressive preset has tighter bands and higher risk."""

    def test_aggressive_has_tighter_bands(self, pm, default_preset):
        aggressive = pm.load("aggressive")
        assert aggressive["bb_std_dev"] < default_preset["bb_std_dev"]

    def test_aggressive_has_relaxed_adx(self, pm, default_preset):
        aggressive = pm.load("aggressive")
        assert aggressive["adx_threshold"] < default_preset["adx_threshold"]

    def test_aggressive_has_higher_risk(self, pm, default_preset):
        aggressive = pm.load("aggressive")
        assert aggressive["risk_per_trade"] > default_preset["risk_per_trade"]

    def test_aggressive_has_larger_position(self, pm, default_preset):
        aggressive = pm.load("aggressive")
        assert aggressive["max_position_pct"] > default_preset["max_position_pct"]


class TestLongOnlyPreset:
    """Long-only preset has side_filter metadata and stricter oversold."""

    def test_long_only_has_side_filter(self, pm):
        long_only = pm.load("long_only")
        assert long_only.get("side_filter") == "long_only"

    def test_long_only_has_stricter_oversold(self, pm, default_preset):
        long_only = pm.load("long_only")
        assert long_only["rsi_oversold"] < default_preset["rsi_oversold"]


class TestRangingPreset:
    """Ranging preset optimized for sideways markets."""

    def test_ranging_has_tighter_bands(self, pm, default_preset):
        ranging = pm.load("ranging")
        assert ranging["bb_std_dev"] < default_preset["bb_std_dev"]

    def test_ranging_has_strict_adx(self, pm, default_preset):
        ranging = pm.load("ranging")
        assert ranging["adx_threshold"] < default_preset["adx_threshold"]

    def test_ranging_has_shorter_hold(self, pm, default_preset):
        ranging = pm.load("ranging")
        assert ranging["max_holding_bars"] < default_preset["max_holding_bars"]

    def test_ranging_has_closer_target(self, pm, default_preset):
        ranging = pm.load("ranging")
        assert ranging["reversion_target"] < default_preset["reversion_target"]


class TestHighRRPreset:
    """High reward-to-risk preset targets 2:1+ payoff."""

    def test_high_rr_has_full_reversion(self, pm):
        high_rr = pm.load("high_rr")
        assert high_rr["reversion_target"] == 1.0

    def test_high_rr_has_tighter_stop(self, pm, default_preset):
        high_rr = pm.load("high_rr")
        assert high_rr["stop_atr_multiplier"] < default_preset["stop_atr_multiplier"]

    def test_high_rr_has_longer_hold(self, pm, default_preset):
        high_rr = pm.load("high_rr")
        assert high_rr["max_holding_bars"] > default_preset["max_holding_bars"]


class TestPresetCount:
    """Verify total number of available presets."""

    def test_preset_count(self, pm):
        presets = pm.list()
        assert len(presets) == 6, f"Expected 6 presets, got {len(presets)}: {presets}"
