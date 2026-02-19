"""Tests for Mean Reversion BB parameter preset system.

Tests the PresetManager class that loads, saves, validates, and lists
YAML parameter presets for the MRBB strategy.
"""

import pytest

from strategies.mean_reversion_bb.presets import PresetManager
from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.param_registry import ParamRegistry


# All 18 tunable params that a preset must contain (excludes ma_type)
REQUIRED_KEYS = {
    "bb_period",
    "bb_std_dev",
    "bb_inner_std_dev",
    "vwap_period",
    "vwap_confirmation_pct",
    "kc_period",
    "kc_atr_multiplier",
    "min_squeeze_duration",
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


class TestPresetLoading:
    """Tests for loading presets from YAML files."""

    def test_load_default_preset(self):
        """PresetManager().load('default') returns dict with all 18 params."""
        pm = PresetManager()
        preset = pm.load("default")
        assert isinstance(preset, dict)
        assert len(set(preset.keys()) & REQUIRED_KEYS) == len(REQUIRED_KEYS)

    def test_load_preset_has_all_required_keys(self):
        """Loaded preset contains every required parameter key."""
        pm = PresetManager()
        preset = pm.load("default")
        for key in REQUIRED_KEYS:
            assert key in preset, f"Missing required key: {key}"

    def test_load_nonexistent_preset_raises(self):
        """Loading a preset that doesn't exist raises an error."""
        pm = PresetManager()
        with pytest.raises((FileNotFoundError, ValueError)):
            pm.load("nonexistent_preset_that_does_not_exist")

    def test_load_preset_types_correct(self):
        """Loaded preset values have correct Python types."""
        pm = PresetManager()
        preset = pm.load("default")
        assert isinstance(preset["bb_period"], int)
        assert isinstance(preset["bb_std_dev"], float)
        assert isinstance(preset["use_regime_filter"], bool)
        assert isinstance(preset["rsi_period"], int)
        assert isinstance(preset["reversion_target"], float)


class TestPresetSaving:
    """Tests for saving presets to YAML files."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Save a preset, load it back, and verify params match."""
        pm = PresetManager(presets_dir=tmp_path)
        params = {
            "bb_period": 25,
            "bb_std_dev": 2.0,
            "bb_inner_std_dev": 1.0,
            "vwap_period": 40,
            "vwap_confirmation_pct": 0.03,
            "kc_period": 15,
            "kc_atr_multiplier": 1.5,
            "min_squeeze_duration": 5,
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "adx_period": 14,
            "adx_threshold": 25.0,
            "use_regime_filter": True,
            "reversion_target": 0.8,
            "max_holding_bars": 40,
            "risk_per_trade": 0.02,
            "max_position_pct": 0.25,
            "stop_atr_multiplier": 2.0,
        }
        pm.save("roundtrip_test", params)
        loaded = pm.load("roundtrip_test")

        for key in REQUIRED_KEYS:
            assert loaded[key] == params[key], f"Mismatch on {key}: {loaded[key]} != {params[key]}"

    def test_save_creates_yaml_file(self, tmp_path):
        """Saving a preset creates a .yaml file at the expected path."""
        pm = PresetManager(presets_dir=tmp_path)
        params = {"bb_period": 20, "bb_std_dev": 2.5}
        pm.save("file_check", params)

        yaml_file = tmp_path / "file_check.yaml"
        yml_file = tmp_path / "file_check.yml"
        assert yaml_file.exists() or yml_file.exists(), (
            f"Expected YAML file at {yaml_file} or {yml_file}"
        )


class TestPresetListing:
    """Tests for listing available presets."""

    def test_list_presets_returns_names(self):
        """list() returns a list of strings."""
        pm = PresetManager()
        presets = pm.list()
        assert isinstance(presets, list)
        assert all(isinstance(name, str) for name in presets)

    def test_list_includes_default(self):
        """The 'default' preset appears in the list."""
        pm = PresetManager()
        presets = pm.list()
        assert "default" in presets


class TestPresetValidation:
    """Tests for parameter validation within presets."""

    def test_validate_rejects_out_of_range(self):
        """Validation rejects bb_period=0 (below min range)."""
        pm = PresetManager()
        invalid_params = {"bb_period": 0}
        with pytest.raises((ValueError, KeyError)):
            pm.validate(invalid_params)

    def test_validate_rejects_wrong_type(self):
        """Validation rejects bb_period='twenty' (wrong type)."""
        pm = PresetManager()
        invalid_params = {"bb_period": "twenty"}
        with pytest.raises((ValueError, TypeError)):
            pm.validate(invalid_params)

    def test_validate_accepts_valid_params(self):
        """Default parameter values pass validation."""
        pm = PresetManager()
        registry = ParamRegistry()
        defaults = registry.to_dict()
        # Should not raise
        pm.validate(defaults)


class TestPresetMetadata:
    """Tests for preset metadata (name, description)."""

    def test_preset_has_metadata(self):
        """Loaded preset includes name and description metadata."""
        pm = PresetManager()
        preset = pm.load("default")
        assert "name" in preset or hasattr(preset, "name"), "Preset missing 'name' metadata"
        assert "description" in preset or hasattr(preset, "description"), (
            "Preset missing 'description' metadata"
        )

    def test_preset_metadata_is_string(self):
        """Preset name and description are strings."""
        pm = PresetManager()
        preset = pm.load("default")
        if isinstance(preset, dict):
            assert isinstance(preset.get("name", ""), str)
            assert isinstance(preset.get("description", ""), str)


class TestPresetModelIntegration:
    """Tests for constructing MeanReversionBB from preset params."""

    def test_preset_params_construct_model(self):
        """MeanReversionBB(**preset_params) succeeds with preset values."""
        pm = PresetManager()
        preset = pm.load("default")
        # Filter to only constructor-accepted params
        model_params = {
            k: v for k, v in preset.items()
            if k in REQUIRED_KEYS and k != "min_squeeze_duration"
        }
        model = MeanReversionBB(**model_params)
        assert isinstance(model, MeanReversionBB)
        assert model.bb_period == preset["bb_period"]

    def test_preset_overrides(self):
        """PresetManager().load() with overrides applies the override values."""
        pm = PresetManager()
        preset = pm.load("default", overrides={"bb_period": 30})
        assert preset["bb_period"] == 30

    def test_preset_overrides_preserve_other_params(self):
        """Overriding one param doesn't change the others."""
        pm = PresetManager()
        base = pm.load("default")
        overridden = pm.load("default", overrides={"bb_period": 30})
        for key in REQUIRED_KEYS:
            if key != "bb_period":
                assert overridden[key] == base[key], (
                    f"Override of bb_period changed {key}: {overridden[key]} != {base[key]}"
                )
