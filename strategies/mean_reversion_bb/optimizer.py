"""Optimizer for Mean Reversion BB strategy parameter tuning.

Supports grid search (subset), random search, and optional Bayesian
optimization via optuna. Runs backtests in parallel and saves results.
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from multiprocessing import Pool
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.param_registry import ParamRegistry
from strategies.mean_reversion_bb.simulator import DirectionalSimulator


# Default constraint: reject runs with drawdown > 15%
DEFAULT_MAX_DRAWDOWN = 0.15

# Default output directory
DEFAULT_OUTPUT_DIR = "backtests/mrbb/optimization"


@dataclass
class BacktestResult:
    """Result of a single backtest run."""
    params: Dict[str, Any]
    sharpe: float
    max_drawdown: float
    total_return_pct: float
    total_trades: int
    final_equity: float
    feasible: bool  # True if max_drawdown <= constraint


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    method: str
    best_params: Optional[Dict[str, Any]]
    best_sharpe: float
    best_drawdown: float
    total_evaluated: int
    feasible_count: int
    elapsed_seconds: float
    all_results: List[BacktestResult] = field(default_factory=list)


def _compute_metrics(equity_curve: List[Dict], initial_equity: float) -> Tuple[float, float]:
    """Compute Sharpe ratio and max drawdown from an equity curve.

    Args:
        equity_curve: List of {timestamp, equity} dicts from simulator.
        initial_equity: Starting equity value.

    Returns:
        (sharpe_ratio, max_drawdown) tuple.
    """
    if len(equity_curve) < 2:
        return 0.0, 0.0

    equities = np.array([e["equity"] for e in equity_curve], dtype=float)
    returns = np.diff(equities) / equities[:-1]

    # Sharpe (per-bar, not annualized)
    std = np.std(returns, ddof=1)
    sharpe = float(np.mean(returns) / std) if std > 0 else 0.0

    # Max drawdown
    peak = np.maximum.accumulate(equities)
    drawdowns = (peak - equities) / np.where(peak > 0, peak, 1.0)
    max_dd = float(np.max(drawdowns))

    return sharpe, max_dd


def _apply_params_to_model(params: dict) -> MeanReversionBB:
    """Create a MeanReversionBB model with given parameters."""
    # Map registry param names to model constructor args
    constructor_args = {
        "bb_period": params.get("bb_period"),
        "bb_std_dev": params.get("bb_std_dev"),
        "bb_inner_std_dev": params.get("bb_inner_std_dev"),
        "vwap_period": params.get("vwap_period"),
        "kc_period": params.get("kc_period"),
        "kc_atr_multiplier": params.get("kc_atr_multiplier"),
        "rsi_period": params.get("rsi_period"),
    }
    # Filter out None values so defaults are used
    constructor_args = {k: v for k, v in constructor_args.items() if v is not None}
    return MeanReversionBB(**constructor_args)


def evaluate_params(
    params: dict,
    df: pd.DataFrame,
    initial_equity: float = 10_000.0,
    max_drawdown: float = DEFAULT_MAX_DRAWDOWN,
    random_seed: Optional[int] = None,
) -> BacktestResult:
    """Evaluate a single parameter combination.

    Args:
        params: Parameter dict from the registry.
        df: OHLCV DataFrame for backtesting.
        initial_equity: Starting equity.
        max_drawdown: Maximum allowed drawdown (feasibility constraint).
        random_seed: Random seed for simulator reproducibility.

    Returns:
        BacktestResult with metrics.
    """
    model = _apply_params_to_model(params)
    sim = DirectionalSimulator(
        model=model,
        initial_equity=initial_equity,
        random_seed=random_seed,
    )
    result = sim.run_backtest(df)

    sharpe, max_dd = _compute_metrics(result["equity_curve"], initial_equity)

    return BacktestResult(
        params=params,
        sharpe=sharpe,
        max_drawdown=max_dd,
        total_return_pct=result["total_return_pct"],
        total_trades=result["total_trades"],
        final_equity=result["final_equity"],
        feasible=max_dd <= max_drawdown,
    )


def _evaluate_params_wrapper(args: tuple) -> BacktestResult:
    """Picklable wrapper for multiprocessing."""
    params, df, initial_equity, max_drawdown, seed = args
    return evaluate_params(params, df, initial_equity, max_drawdown, seed)


def grid_search(
    df: pd.DataFrame,
    param_names: Optional[List[str]] = None,
    n_workers: int = 1,
    initial_equity: float = 10_000.0,
    max_drawdown: float = DEFAULT_MAX_DRAWDOWN,
    random_seed: Optional[int] = None,
) -> OptimizationResult:
    """Grid search over a subset of parameters.

    Args:
        df: OHLCV DataFrame for backtesting.
        param_names: Which parameters to grid over (others stay at defaults).
            If None, uses all parameters (WARNING: combinatorial explosion).
        n_workers: Number of parallel workers.
        initial_equity: Starting equity.
        max_drawdown: Maximum allowed drawdown constraint.
        random_seed: Random seed for simulator.

    Returns:
        OptimizationResult with best params and all results.
    """
    registry = ParamRegistry()
    defaults = registry.to_dict()

    if param_names is None:
        param_names = list(registry.params.keys())

    # Build grid for selected params only, defaults for the rest
    import itertools
    grid_params = {name: registry.params[name].grid_values() for name in param_names}
    keys = list(grid_params.keys())
    values = list(grid_params.values())

    combos = []
    for combo_vals in itertools.product(*values):
        params = dict(defaults)
        params.update(dict(zip(keys, combo_vals)))
        combos.append(params)

    return _run_optimization("grid", combos, df, n_workers, initial_equity, max_drawdown, random_seed)


def random_search(
    df: pd.DataFrame,
    n_iterations: int = 100,
    n_workers: int = 1,
    initial_equity: float = 10_000.0,
    max_drawdown: float = DEFAULT_MAX_DRAWDOWN,
    random_seed: Optional[int] = None,
) -> OptimizationResult:
    """Random search over the parameter space.

    Args:
        df: OHLCV DataFrame for backtesting.
        n_iterations: Number of random parameter combinations to try.
        n_workers: Number of parallel workers.
        initial_equity: Starting equity.
        max_drawdown: Maximum allowed drawdown constraint.
        random_seed: Random seed for parameter generation and simulator.

    Returns:
        OptimizationResult with best params and all results.
    """
    registry = ParamRegistry()
    combos = registry.generate_random(n_iterations, seed=random_seed)

    return _run_optimization("random", combos, df, n_workers, initial_equity, max_drawdown, random_seed)


def bayesian_search(
    df: pd.DataFrame,
    n_trials: int = 100,
    initial_equity: float = 10_000.0,
    max_drawdown: float = DEFAULT_MAX_DRAWDOWN,
    random_seed: Optional[int] = None,
) -> OptimizationResult:
    """Bayesian optimization using optuna TPE sampler.

    Falls back to random search if optuna is not installed.

    Args:
        df: OHLCV DataFrame for backtesting.
        n_trials: Number of optimization trials.
        initial_equity: Starting equity.
        max_drawdown: Maximum allowed drawdown constraint.
        random_seed: Random seed for reproducibility.

    Returns:
        OptimizationResult with best params and all results.
    """
    try:
        import optuna
    except ImportError:
        # Graceful fallback to random search
        return random_search(
            df,
            n_iterations=n_trials,
            n_workers=1,
            initial_equity=initial_equity,
            max_drawdown=max_drawdown,
            random_seed=random_seed,
        )

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    registry = ParamRegistry()
    all_results: List[BacktestResult] = []

    def objective(trial: "optuna.Trial") -> float:
        params = {}
        for name, spec in registry.params.items():
            if spec.param_type == "choice":
                params[name] = trial.suggest_categorical(name, spec.choices)
            elif spec.param_type == "int":
                params[name] = trial.suggest_int(name, int(spec.min_val), int(spec.max_val))
            else:
                params[name] = trial.suggest_float(name, spec.min_val, spec.max_val)

        result = evaluate_params(params, df, initial_equity, max_drawdown, random_seed)
        all_results.append(result)

        # Penalize infeasible solutions
        if not result.feasible:
            return -10.0

        return result.sharpe

    sampler = optuna.samplers.TPESampler(seed=random_seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    start = time.time()
    study.optimize(objective, n_trials=n_trials)
    elapsed = time.time() - start

    feasible = [r for r in all_results if r.feasible]
    if feasible:
        best = max(feasible, key=lambda r: r.sharpe)
        best_params = best.params
        best_sharpe = best.sharpe
        best_dd = best.max_drawdown
    else:
        best_params = None
        best_sharpe = 0.0
        best_dd = 0.0

    return OptimizationResult(
        method="bayesian",
        best_params=best_params,
        best_sharpe=best_sharpe,
        best_drawdown=best_dd,
        total_evaluated=len(all_results),
        feasible_count=len(feasible),
        elapsed_seconds=elapsed,
        all_results=all_results,
    )


def _run_optimization(
    method: str,
    combos: List[dict],
    df: pd.DataFrame,
    n_workers: int,
    initial_equity: float,
    max_drawdown: float,
    random_seed: Optional[int],
) -> OptimizationResult:
    """Run optimization over a list of parameter combinations.

    Args:
        method: Name of the optimization method.
        combos: List of parameter dicts to evaluate.
        df: OHLCV DataFrame.
        n_workers: Number of parallel workers.
        initial_equity: Starting equity.
        max_drawdown: Drawdown constraint.
        random_seed: Random seed for simulator.

    Returns:
        OptimizationResult.
    """
    start = time.time()

    args_list = [(params, df, initial_equity, max_drawdown, random_seed) for params in combos]

    if n_workers > 1:
        with Pool(n_workers) as pool:
            results = pool.map(_evaluate_params_wrapper, args_list)
    else:
        results = [_evaluate_params_wrapper(args) for args in args_list]

    elapsed = time.time() - start

    feasible = [r for r in results if r.feasible]
    if feasible:
        best = max(feasible, key=lambda r: r.sharpe)
        best_params = best.params
        best_sharpe = best.sharpe
        best_dd = best.max_drawdown
    else:
        best_params = None
        best_sharpe = 0.0
        best_dd = 0.0

    return OptimizationResult(
        method=method,
        best_params=best_params,
        best_sharpe=best_sharpe,
        best_drawdown=best_dd,
        total_evaluated=len(results),
        feasible_count=len(feasible),
        elapsed_seconds=elapsed,
        all_results=results,
    )


def save_results(result: OptimizationResult, output_dir: str = DEFAULT_OUTPUT_DIR) -> str:
    """Save optimization results to JSON.

    Args:
        result: OptimizationResult to save.
        output_dir: Directory to save to.

    Returns:
        Path to saved file.
    """
    os.makedirs(output_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{result.method}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    # Convert to serializable format
    data = {
        "method": result.method,
        "best_params": result.best_params,
        "best_sharpe": result.best_sharpe,
        "best_drawdown": result.best_drawdown,
        "total_evaluated": result.total_evaluated,
        "feasible_count": result.feasible_count,
        "elapsed_seconds": result.elapsed_seconds,
        "results": [
            {
                "params": r.params,
                "sharpe": r.sharpe,
                "max_drawdown": r.max_drawdown,
                "total_return_pct": r.total_return_pct,
                "total_trades": r.total_trades,
                "final_equity": r.final_equity,
                "feasible": r.feasible,
            }
            for r in result.all_results
        ],
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    return filepath
