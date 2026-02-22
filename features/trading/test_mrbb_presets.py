"""BDD step implementations for mrbb-presets.feature.

Tests the PresetManager YAML preset system using pytest-bdd
with Gherkin scenarios defined in mrbb-presets.feature.
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from strategies.mean_reversion_bb.presets import PresetManager
from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.param_registry import ParamRegistry

# Load all scenarios
scenarios("trading/mrbb-presets.feature")

# All 18 tunable params that a preset must contain
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


class PresetContext:
    """Mutable container for passing data between BDD steps."""

    def __init__(self):
        self.pm: PresetManager | None = None
        self.preset: dict | None = None
        self.default_preset: dict | None = None
        self.preset_list: list | None = None
        self.error: Exception | None = None
        self.model: MeanReversionBB | None = None
        self.tmp_path: str | None = None


@pytest.fixture
def ctx(tmp_path):
    c = PresetContext()
    c.tmp_path = tmp_path
    return c


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------

@given("a PresetManager instance", target_fixture="ctx")
def given_preset_manager(ctx):
    ctx.pm = PresetManager()
    return ctx


@given(parsers.parse('the "{name}" preset is available'))
def given_preset_available(ctx, name):
    # Just verify the preset manager can reference it
    if ctx.pm is None:
        ctx.pm = PresetManager()


@given("at least one preset YAML file exists")
def given_preset_files_exist(ctx):
    if ctx.pm is None:
        ctx.pm = PresetManager()


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when(parsers.parse('I load the "{name}" preset'))
def when_load_preset(ctx, name):
    ctx.preset = ctx.pm.load(name)


@when(parsers.parse('I try to load the "{name}" preset'))
def when_try_load_preset(ctx, name):
    try:
        ctx.preset = ctx.pm.load(name)
    except (FileNotFoundError, ValueError) as e:
        ctx.error = e


@when("I construct a MeanReversionBB model from the preset")
def when_construct_model(ctx):
    model_params = {
        k: v for k, v in ctx.preset.items()
        if k in REQUIRED_KEYS and k != "min_squeeze_duration"
    }
    # Remove metadata keys that aren't constructor params
    model_params.pop("name", None)
    model_params.pop("description", None)
    ctx.model = MeanReversionBB(**model_params)


@when(parsers.parse('I load the "{name}" preset with overrides bb_period={value:d}'))
def when_load_with_overrides(ctx, name, value):
    ctx.default_preset = ctx.pm.load(name)
    ctx.preset = ctx.pm.load(name, overrides={"bb_period": value})


@when("I list available presets")
def when_list_presets(ctx):
    ctx.preset_list = ctx.pm.list()


@when(parsers.parse('I save a preset named "{name}" with default parameters'))
def when_save_default(ctx, name):
    # Use tmp_path-based PresetManager for save tests
    ctx.pm = PresetManager(presets_dir=ctx.tmp_path)
    registry = ParamRegistry()
    defaults = registry.to_dict()
    ctx.pm.save(name, defaults)
    ctx.preset = defaults


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------

@then("the preset should contain all 18 tunable parameters")
def then_has_all_params(ctx):
    assert ctx.preset is not None
    for key in REQUIRED_KEYS:
        assert key in ctx.preset, f"Missing key: {key}"


@then("it should raise a preset not found error")
def then_raises_error(ctx):
    assert ctx.error is not None, "Expected an error but none was raised"
    assert isinstance(ctx.error, (FileNotFoundError, ValueError))


@then("the model should be valid")
def then_model_valid(ctx):
    assert ctx.model is not None
    assert isinstance(ctx.model, MeanReversionBB)


@then(parsers.parse("the preset bb_period should be {value:d}"))
def then_bb_period_is(ctx, value):
    assert ctx.preset["bb_period"] == value


@then("all other parameters should match the default preset")
def then_other_params_match(ctx):
    for key in REQUIRED_KEYS:
        if key != "bb_period":
            assert ctx.preset[key] == ctx.default_preset[key], (
                f"Param {key} differs: {ctx.preset[key]} != {ctx.default_preset[key]}"
            )


@then("the result should be a non-empty list of strings")
def then_non_empty_string_list(ctx):
    assert isinstance(ctx.preset_list, list)
    assert len(ctx.preset_list) > 0
    assert all(isinstance(name, str) for name in ctx.preset_list)


@then(parsers.parse('"{name}" should be in the list'))
def then_name_in_list(ctx, name):
    assert name in ctx.preset_list


@then(parsers.parse('a YAML file for "{name}" should exist'))
def then_yaml_exists(ctx, name):
    yaml_file = ctx.tmp_path / f"{name}.yaml"
    yml_file = ctx.tmp_path / f"{name}.yml"
    assert yaml_file.exists() or yml_file.exists()


@then(parsers.parse('loading "{name}" should return the saved parameters'))
def then_load_matches_saved(ctx, name):
    loaded = ctx.pm.load(name)
    for key in REQUIRED_KEYS:
        if key in ctx.preset:
            assert loaded[key] == ctx.preset[key], (
                f"Roundtrip mismatch on {key}: {loaded[key]} != {ctx.preset[key]}"
            )
