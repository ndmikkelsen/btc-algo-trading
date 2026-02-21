"""Parameter registry for Mean Reversion BB strategy optimization.

Defines tunable parameters with their ranges, types, and constraints
for grid search, random search, and Bayesian optimization.
"""

from dataclasses import dataclass
from typing import Any, List, Optional
import random
import itertools


@dataclass
class ParamSpec:
    """Specification for a single tunable parameter."""
    name: str
    default: Any
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    step: Optional[float] = None
    param_type: str = "float"  # "float", "int", "choice"
    choices: Optional[List[Any]] = None
    description: str = ""

    def validate(self, value: Any) -> bool:
        """Check if a value is valid for this parameter."""
        if self.param_type == "choice":
            return value in (self.choices or [])
        if self.min_val is not None and value < self.min_val:
            return False
        if self.max_val is not None and value > self.max_val:
            return False
        return True

    def random_value(self, rng: random.Random = None) -> Any:
        """Generate a random valid value."""
        r = rng or random
        if self.param_type == "choice":
            return r.choice(self.choices)
        if self.param_type == "int":
            return r.randint(int(self.min_val), int(self.max_val))
        # float
        return r.uniform(self.min_val, self.max_val)

    def grid_values(self) -> List[Any]:
        """Generate grid of values for this parameter."""
        if self.param_type == "choice":
            return list(self.choices)
        if self.step is None:
            return [self.default]
        values = []
        v = self.min_val
        while v <= self.max_val + 1e-10:  # floating point tolerance
            if self.param_type == "int":
                values.append(int(round(v)))
            else:
                values.append(round(v, 6))
            v += self.step
        return values


class ParamRegistry:
    """Registry of all tunable parameters for the MRBB strategy."""

    def __init__(self):
        self.params: dict[str, ParamSpec] = {}
        self._register_all()

    def _register_all(self):
        """Register all tunable parameters."""
        # Bollinger Band parameters
        self._register(ParamSpec("bb_period", 20, 10, 50, 5, "int", description="BB moving average period"))
        self._register(ParamSpec("bb_std_dev", 2.5, 1.5, 3.0, 0.25, "float", description="BB outer band std dev multiplier"))
        self._register(ParamSpec("bb_inner_std_dev", 1.0, 0.5, 1.5, 0.25, "float", description="BB inner band std dev multiplier"))
        self._register(ParamSpec("ma_type", "sma", param_type="choice", choices=["sma", "ema", "wma"], description="Moving average type"))

        # VWAP parameters
        self._register(ParamSpec("vwap_period", 50, 20, 100, 10, "int", description="VWAP rolling period"))
        self._register(ParamSpec("vwap_confirmation_pct", 0.02, 0.01, 1.0, 0.005, "float", description="VWAP proximity threshold (1.0 = effectively disabled)"))

        # Keltner Channel / Squeeze parameters
        self._register(ParamSpec("kc_period", 20, 10, 40, 5, "int", description="Keltner Channel period"))
        self._register(ParamSpec("kc_atr_multiplier", 1.5, 1.0, 3.0, 0.25, "float", description="KC ATR multiplier"))
        self._register(ParamSpec("min_squeeze_duration", 6, 3, 12, 1, "int", description="Min squeeze candles before fire"))

        # Regime filter parameters
        self._register(ParamSpec("adx_period", 14, 7, 21, 1, "int", description="ADX calculation period"))
        self._register(ParamSpec("adx_threshold", 22.0, 15.0, 35.0, 1.0, "float", description="ADX threshold for ranging regime"))

        # Signal parameters
        self._register(ParamSpec("rsi_period", 14, 7, 21, 1, "int", description="RSI calculation period"))
        self._register(ParamSpec("rsi_oversold", 30, 20, 40, 5, "int", description="RSI oversold threshold"))
        self._register(ParamSpec("rsi_overbought", 70, 60, 80, 5, "int", description="RSI overbought threshold"))
        self._register(ParamSpec("reversion_target", 0.9, 0.5, 1.0, 0.1, "float", description="Mean reversion target (fraction of distance)"))
        self._register(ParamSpec("max_holding_bars", 50, 20, 300, 10, "int", description="Max bars to hold position (288 = 24h at 5m)"))

        # Risk parameters
        self._register(ParamSpec("risk_per_trade", 0.02, 0.01, 0.05, 0.005, "float", description="Risk per trade as fraction of equity"))
        self._register(ParamSpec("max_position_pct", 0.25, 0.10, 0.50, 0.05, "float", description="Max position as fraction of equity"))
        self._register(ParamSpec("stop_atr_multiplier", 2.5, 0.0, 3.0, 0.25, "float", description="Stop loss ATR multiplier (0 = no stop)"))

        # Asymmetric short parameters
        self._register(ParamSpec("short_bb_std_dev", 2.5, 2.0, 4.0, 0.25, "float", description="BB std dev for short entry band (wider = stricter)"))
        self._register(ParamSpec("short_rsi_threshold", 70, 65, 90, 5, "int", description="RSI threshold for short entry (higher = stricter)"))
        self._register(ParamSpec("short_max_holding_bars", 50, 12, 288, 12, "int", description="Max bars to hold short position"))
        self._register(ParamSpec("short_position_pct", 0.25, 0.05, 0.50, 0.05, "float", description="Max short position as fraction of equity"))

        # Trend filter parameters
        self._register(ParamSpec("use_trend_filter", False, param_type="choice", choices=[True, False], description="Enable trend direction gating for entries"))
        self._register(ParamSpec("trend_ema_period", 50, 20, 200, 10, "int", description="EMA period for trend direction detection"))

        # Configurable toggles
        self._register(ParamSpec("side_filter", "both", param_type="choice", choices=["both", "long_only", "short_only"], description="Side filter: both, long_only, or short_only"))
        self._register(ParamSpec("use_squeeze_filter", True, param_type="choice", choices=[True, False], description="Enable/disable squeeze filter"))
        self._register(ParamSpec("use_band_walking_exit", True, param_type="choice", choices=[True, False], description="Enable/disable band walking exit"))

    def _register(self, spec: ParamSpec):
        self.params[spec.name] = spec

    def to_dict(self) -> dict:
        """Get all default parameter values as a dict."""
        return {name: spec.default for name, spec in self.params.items()}

    def from_dict(self, values: dict) -> dict:
        """Validate and return parameter values from a dict."""
        result = self.to_dict()  # start with defaults
        for name, value in values.items():
            if name in self.params:
                if self.params[name].validate(value):
                    result[name] = value
                else:
                    raise ValueError(f"Invalid value {value} for param {name}")
        return result

    def generate_grid(self) -> List[dict]:
        """Generate full parameter grid (all combinations)."""
        param_grids = {name: spec.grid_values() for name, spec in self.params.items()}
        keys = list(param_grids.keys())
        values = list(param_grids.values())
        grid = []
        for combo in itertools.product(*values):
            grid.append(dict(zip(keys, combo)))
        return grid

    def generate_random(self, n: int, seed: int = None) -> List[dict]:
        """Generate n random parameter combinations."""
        rng = random.Random(seed)
        results = []
        for _ in range(n):
            combo = {}
            for name, spec in self.params.items():
                combo[name] = spec.random_value(rng)
            results.append(combo)
        return results

    def apply_to_model(self, model, params: dict):
        """Apply parameter values to a model instance."""
        for name, value in params.items():
            if hasattr(model, name):
                setattr(model, name, value)
