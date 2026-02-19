"""Tests for Mean Reversion BB parameter registry."""

import math
import pytest

from strategies.mean_reversion_bb.param_registry import ParamRegistry, ParamSpec
from strategies.mean_reversion_bb import config


class TestParamSpec:
    """Tests for individual ParamSpec behavior."""

    def test_validate_float_in_range(self):
        spec = ParamSpec("test", 2.0, 1.0, 3.0, 0.5, "float")
        assert spec.validate(1.0) is True
        assert spec.validate(2.5) is True
        assert spec.validate(3.0) is True

    def test_validate_float_out_of_range(self):
        spec = ParamSpec("test", 2.0, 1.0, 3.0, 0.5, "float")
        assert spec.validate(0.5) is False
        assert spec.validate(3.5) is False

    def test_validate_choice(self):
        spec = ParamSpec("test", "a", param_type="choice", choices=["a", "b", "c"])
        assert spec.validate("a") is True
        assert spec.validate("d") is False

    def test_random_value_in_bounds(self):
        spec = ParamSpec("test", 5.0, 1.0, 10.0, 1.0, "float")
        import random
        rng = random.Random(42)
        for _ in range(100):
            val = spec.random_value(rng)
            assert 1.0 <= val <= 10.0

    def test_random_value_int(self):
        spec = ParamSpec("test", 5, 1, 10, 1, "int")
        import random
        rng = random.Random(42)
        for _ in range(100):
            val = spec.random_value(rng)
            assert isinstance(val, int)
            assert 1 <= val <= 10

    def test_random_value_choice(self):
        spec = ParamSpec("test", "a", param_type="choice", choices=["a", "b", "c"])
        import random
        rng = random.Random(42)
        for _ in range(100):
            val = spec.random_value(rng)
            assert val in ["a", "b", "c"]

    def test_grid_values_int(self):
        spec = ParamSpec("bb_period", 20, 10, 50, 5, "int")
        grid = spec.grid_values()
        assert grid == [10, 15, 20, 25, 30, 35, 40, 45, 50]

    def test_grid_values_float(self):
        spec = ParamSpec("bb_std_dev", 2.0, 1.5, 3.0, 0.25, "float")
        grid = spec.grid_values()
        assert grid == [1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0]

    def test_grid_values_choice(self):
        spec = ParamSpec("ma_type", "sma", param_type="choice", choices=["sma", "ema", "wma"])
        grid = spec.grid_values()
        assert grid == ["sma", "ema", "wma"]

    def test_grid_values_no_step_returns_default(self):
        spec = ParamSpec("test", 5.0, 1.0, 10.0, param_type="float")
        grid = spec.grid_values()
        assert grid == [5.0]


class TestParamRegistry:
    """Tests for the ParamRegistry class."""

    @pytest.fixture
    def registry(self):
        return ParamRegistry()

    def test_all_params_registered(self, registry):
        """All 22 tunable parameters from config.py are registered."""
        assert len(registry.params) == 22

    def test_expected_param_names(self, registry):
        expected = {
            "bb_period", "bb_std_dev", "bb_inner_std_dev", "ma_type",
            "vwap_period", "vwap_confirmation_pct",
            "kc_period", "kc_atr_multiplier", "min_squeeze_duration",
            "adx_period", "adx_threshold",
            "rsi_period", "rsi_oversold", "rsi_overbought",
            "reversion_target", "max_holding_bars",
            "risk_per_trade", "max_position_pct", "stop_atr_multiplier",
            "side_filter", "use_squeeze_filter", "use_band_walking_exit",
        }
        assert set(registry.params.keys()) == expected

    def test_defaults_match_config(self, registry):
        """Default values in registry match config.py constants."""
        defaults = registry.to_dict()
        assert defaults["bb_period"] == config.BB_PERIOD
        assert defaults["bb_std_dev"] == config.BB_STD_DEV
        assert defaults["bb_inner_std_dev"] == config.BB_INNER_STD_DEV
        assert defaults["ma_type"] == config.MA_TYPE
        assert defaults["vwap_period"] == config.VWAP_PERIOD
        assert defaults["vwap_confirmation_pct"] == config.VWAP_CONFIRMATION_PCT
        assert defaults["kc_period"] == config.KC_PERIOD
        assert defaults["kc_atr_multiplier"] == config.KC_ATR_MULTIPLIER
        assert defaults["min_squeeze_duration"] == config.MIN_SQUEEZE_DURATION
        assert defaults["adx_period"] == config.ADX_PERIOD
        assert defaults["adx_threshold"] == config.ADX_THRESHOLD
        assert defaults["rsi_period"] == config.RSI_PERIOD
        assert defaults["rsi_oversold"] == config.RSI_OVERSOLD
        assert defaults["rsi_overbought"] == config.RSI_OVERBOUGHT
        assert defaults["reversion_target"] == config.REVERSION_TARGET
        assert defaults["max_holding_bars"] == config.MAX_HOLDING_BARS
        assert defaults["risk_per_trade"] == config.RISK_PER_TRADE
        assert defaults["max_position_pct"] == config.MAX_POSITION_PCT
        assert defaults["stop_atr_multiplier"] == config.STOP_ATR_MULTIPLIER
        assert defaults["side_filter"] == config.SIDE_FILTER
        assert defaults["use_squeeze_filter"] == config.USE_SQUEEZE_FILTER
        assert defaults["use_band_walking_exit"] == config.USE_BAND_WALKING_EXIT

    def test_validation_rejects_out_of_range(self, registry):
        """Validation rejects values outside defined ranges."""
        assert registry.params["bb_period"].validate(5) is False   # below min 10
        assert registry.params["bb_period"].validate(55) is False  # above max 50
        assert registry.params["bb_std_dev"].validate(0.5) is False
        assert registry.params["ma_type"].validate("hull") is False

    def test_validation_accepts_in_range(self, registry):
        assert registry.params["bb_period"].validate(20) is True
        assert registry.params["bb_std_dev"].validate(2.0) is True
        assert registry.params["ma_type"].validate("ema") is True

    def test_grid_values_bb_period(self, registry):
        grid = registry.params["bb_period"].grid_values()
        assert grid == [10, 15, 20, 25, 30, 35, 40, 45, 50]

    def test_generate_random_count(self, registry):
        results = registry.generate_random(10, seed=42)
        assert len(results) == 10

    def test_generate_random_within_bounds(self, registry):
        results = registry.generate_random(50, seed=42)
        for combo in results:
            for name, value in combo.items():
                spec = registry.params[name]
                assert spec.validate(value), f"{name}={value} failed validation"

    def test_generate_random_deterministic(self, registry):
        r1 = registry.generate_random(5, seed=123)
        r2 = registry.generate_random(5, seed=123)
        assert r1 == r2

    def test_generate_grid_size_calculation(self, registry):
        """Grid size is the product of all individual grid sizes."""
        expected_size = 1
        for spec in registry.params.values():
            expected_size *= len(spec.grid_values())
        # Full grid is too large to materialize; verify the math
        assert expected_size > 1_000_000  # combinatorial explosion expected

    def test_generate_grid_subset(self):
        """generate_grid works correctly with a small subset of params."""
        reg = ParamRegistry()
        # Keep only 2 params for a tractable grid
        reg.params = {
            "bb_period": reg.params["bb_period"],
            "ma_type": reg.params["ma_type"],
        }
        grid = reg.generate_grid()
        # bb_period: 9 values * ma_type: 3 values = 27
        assert len(grid) == 9 * 3
        assert all("bb_period" in combo and "ma_type" in combo for combo in grid)

    def test_from_dict_fills_defaults(self, registry):
        """from_dict fills missing params with defaults."""
        partial = {"bb_period": 30, "bb_std_dev": 2.5}
        result = registry.from_dict(partial)
        assert result["bb_period"] == 30
        assert result["bb_std_dev"] == 2.5
        # Everything else should be default
        assert result["rsi_period"] == config.RSI_PERIOD
        assert result["ma_type"] == config.MA_TYPE

    def test_from_dict_rejects_invalid(self, registry):
        with pytest.raises(ValueError, match="Invalid value"):
            registry.from_dict({"bb_period": 999})

    def test_from_dict_ignores_unknown_keys(self, registry):
        result = registry.from_dict({"unknown_param": 42})
        assert "unknown_param" not in result

    def test_apply_to_model(self, registry):
        """apply_to_model sets attributes on the model object."""
        class MockModel:
            bb_period = 0
            bb_std_dev = 0.0
            ma_type = ""
            not_a_param = "original"

        model = MockModel()
        registry.apply_to_model(model, {"bb_period": 30, "bb_std_dev": 2.5, "ma_type": "ema"})
        assert model.bb_period == 30
        assert model.bb_std_dev == 2.5
        assert model.ma_type == "ema"

    def test_apply_to_model_skips_missing_attrs(self, registry):
        """apply_to_model only sets attributes that exist on the model."""
        class MinimalModel:
            bb_period = 0

        model = MinimalModel()
        registry.apply_to_model(model, {"bb_period": 30, "rsi_period": 10})
        assert model.bb_period == 30
        assert not hasattr(model, "rsi_period")

    def test_to_dict_returns_copy(self, registry):
        """to_dict returns a new dict each time."""
        d1 = registry.to_dict()
        d2 = registry.to_dict()
        assert d1 == d2
        assert d1 is not d2
