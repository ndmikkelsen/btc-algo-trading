"""Parameter preset system for Mean Reversion BB strategy.

Loads, saves, validates, and lists YAML parameter presets.
"""

from pathlib import Path
from typing import Optional

import yaml

from strategies.mean_reversion_bb.param_registry import ParamRegistry


class PresetManager:
    """Manage YAML parameter presets for the MRBB strategy."""

    def __init__(self, presets_dir: Optional[Path] = None):
        if presets_dir is None:
            self._presets_dir = Path(__file__).parent / "presets"
        else:
            self._presets_dir = Path(presets_dir)

    def load(self, name: str, overrides: Optional[dict] = None) -> dict:
        """Load a named preset from YAML, optionally applying overrides.

        Args:
            name: Preset name (without .yaml extension).
            overrides: Dict of param values to override after loading.

        Returns:
            Flat dict with all preset params (+ metadata like name/description).

        Raises:
            FileNotFoundError: If no YAML file exists for the given name.
        """
        yaml_path = self._presets_dir / f"{name}.yaml"
        if not yaml_path.exists():
            yml_path = self._presets_dir / f"{name}.yml"
            if yml_path.exists():
                yaml_path = yml_path
            else:
                raise FileNotFoundError(
                    f"Preset '{name}' not found at {yaml_path}"
                )

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        if overrides:
            data.update(overrides)

        return data

    def save(self, name: str, params: dict) -> Path:
        """Save params as a YAML preset file.

        Args:
            name: Preset name (becomes filename).
            params: Dict of parameter values to persist.

        Returns:
            Path to the written YAML file.
        """
        self._presets_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = self._presets_dir / f"{name}.yaml"

        with open(yaml_path, "w") as f:
            yaml.dump(params, f, default_flow_style=False, sort_keys=False)

        return yaml_path

    def list(self) -> list:
        """Return names of all available presets (without extension)."""
        if not self._presets_dir.exists():
            return []
        names = []
        for p in sorted(self._presets_dir.iterdir()):
            if p.suffix in (".yaml", ".yml"):
                names.append(p.stem)
        return names

    def validate(self, params: dict) -> None:
        """Validate param values against the ParamRegistry.

        Checks types and ranges for any key present in both *params*
        and the registry.  Keys not in the registry are silently skipped.

        Raises:
            TypeError: If a value has the wrong Python type.
            ValueError: If a value is outside its allowed range.
        """
        registry = ParamRegistry()
        for key, value in params.items():
            if key not in registry.params:
                continue
            spec = registry.params[key]

            # Type gate
            if spec.param_type in ("int", "float"):
                if not isinstance(value, (int, float)):
                    raise TypeError(
                        f"Parameter '{key}' expects numeric type, "
                        f"got {type(value).__name__}"
                    )
            elif spec.param_type == "choice":
                pass  # choices validated below

            # Range / choice gate
            if not spec.validate(value):
                raise ValueError(
                    f"Parameter '{key}' value {value!r} is out of range "
                    f"[{spec.min_val}, {spec.max_val}]"
                )
