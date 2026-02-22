"""Combinatorial Purged Cross-Validation (CPCV).

Implements the de Prado (2018) method for detecting backtest overfitting:
- Split data into N groups, form C(N, N//2) train/test combinations
- Purge gap between train and test to avoid lookahead bias
- Compute PBO (Probability of Backtest Overfitting)
- Compute deflated Sharpe ratio

References:
- de Prado (2018) "Advances in Financial Machine Learning", Ch. 12
- Bailey & de Prado (2014) "The Deflated Sharpe Ratio"
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable, List, Optional, Tuple

from strategies.mean_reversion_bb.config import BB_PERIOD, MAX_HOLDING_BARS


# Purge gap: BB lookback + max hold period (~70 candles at 5m = ~6 hours)
DEFAULT_PURGE_GAP = BB_PERIOD + MAX_HOLDING_BARS

# Default number of groups
DEFAULT_N_GROUPS = 6


@dataclass
class CPCVResult:
    """Result of CPCV analysis."""
    pbo: float  # Probability of Backtest Overfitting
    deflated_sharpe: float
    n_splits: int
    is_sharpes: List[float]  # In-sample Sharpes per split
    oos_sharpes: List[float]  # Out-of-sample Sharpes per split
    n_groups: int
    purge_gap: int


def _split_into_groups(
    n_samples: int, n_groups: int
) -> List[Tuple[int, int]]:
    """Split data indices into n_groups contiguous blocks.

    Returns:
        List of (start, end) index tuples.
    """
    group_size = n_samples // n_groups
    groups = []
    for i in range(n_groups):
        start = i * group_size
        end = start + group_size if i < n_groups - 1 else n_samples
        groups.append((start, end))
    return groups


def _apply_purge(
    train_indices: np.ndarray,
    test_indices: np.ndarray,
    purge_gap: int,
) -> np.ndarray:
    """Remove training samples within purge_gap of any test sample.

    This prevents lookahead bias from overlapping indicator windows.
    """
    if purge_gap <= 0 or len(test_indices) == 0:
        return train_indices

    test_min = test_indices.min()
    test_max = test_indices.max()

    # Remove train indices that are within purge_gap of test boundaries
    mask = np.ones(len(train_indices), dtype=bool)
    for i, idx in enumerate(train_indices):
        if abs(idx - test_min) < purge_gap or abs(idx - test_max) < purge_gap:
            mask[i] = False

    return train_indices[mask]


def _sharpe_from_returns(returns: np.ndarray) -> float:
    """Compute Sharpe ratio from returns array."""
    if len(returns) < 2:
        return 0.0
    std = np.std(returns, ddof=1)
    if std == 0:
        return 0.0
    return float(np.mean(returns) / std)


def run_cpcv(
    df: pd.DataFrame,
    evaluate_fn: Callable[[pd.DataFrame, pd.DataFrame], Tuple[float, float]],
    n_groups: int = DEFAULT_N_GROUPS,
    purge_gap: int = DEFAULT_PURGE_GAP,
) -> CPCVResult:
    """Run Combinatorial Purged Cross-Validation.

    Args:
        df: Full OHLCV DataFrame.
        evaluate_fn: Callable(train_df, test_df) -> (is_sharpe, oos_sharpe).
            Should train strategy on train_df and evaluate on test_df.
        n_groups: Number of groups to split data into.
        purge_gap: Number of candles to purge between train/test.

    Returns:
        CPCVResult with PBO and deflated Sharpe.
    """
    n_samples = len(df)
    groups = _split_into_groups(n_samples, n_groups)

    # Generate all C(N, N//2) test group combinations
    test_size = n_groups // 2
    group_indices = list(range(n_groups))
    all_combos = list(combinations(group_indices, test_size))
    n_splits = len(all_combos)

    is_sharpes = []
    oos_sharpes = []

    all_indices = np.arange(n_samples)

    for combo in all_combos:
        test_group_set = set(combo)
        train_group_set = set(group_indices) - test_group_set

        # Build index arrays
        test_idx = np.concatenate(
            [np.arange(groups[g][0], groups[g][1]) for g in test_group_set]
        )
        train_idx = np.concatenate(
            [np.arange(groups[g][0], groups[g][1]) for g in train_group_set]
        )

        # Apply purge
        train_idx = _apply_purge(train_idx, test_idx, purge_gap)

        if len(train_idx) == 0 or len(test_idx) == 0:
            continue

        train_df = df.iloc[train_idx].copy()
        test_df = df.iloc[test_idx].copy()

        is_sharpe, oos_sharpe = evaluate_fn(train_df, test_df)
        is_sharpes.append(is_sharpe)
        oos_sharpes.append(oos_sharpe)

    # PBO: fraction of OOS Sharpes that are negative
    # when using IS-optimal parameters
    if oos_sharpes:
        pbo = float(np.mean(np.array(oos_sharpes) < 0))
    else:
        pbo = 1.0

    # Deflated Sharpe: adjust observed Sharpe for multiple testing
    deflated_sharpe = _deflated_sharpe(
        is_sharpes, oos_sharpes, n_splits
    )

    return CPCVResult(
        pbo=pbo,
        deflated_sharpe=deflated_sharpe,
        n_splits=n_splits,
        is_sharpes=is_sharpes,
        oos_sharpes=oos_sharpes,
        n_groups=n_groups,
        purge_gap=purge_gap,
    )


def _deflated_sharpe(
    is_sharpes: List[float],
    oos_sharpes: List[float],
    n_trials: int,
) -> float:
    """Compute the Deflated Sharpe Ratio (Bailey & de Prado 2014).

    Adjusts the best observed Sharpe for the number of trials conducted.
    """
    if not oos_sharpes or n_trials <= 1:
        return 0.0

    oos_arr = np.array(oos_sharpes)
    best_sharpe = np.max(oos_arr)
    mean_sharpe = np.mean(oos_arr)
    std_sharpe = np.std(oos_arr, ddof=1)

    if std_sharpe == 0:
        return best_sharpe

    # Expected maximum Sharpe under null (Euler-Mascheroni correction)
    euler_mascheroni = 0.5772156649
    expected_max = mean_sharpe + std_sharpe * (
        (1 - euler_mascheroni) * np.sqrt(2 * np.log(n_trials))
        + euler_mascheroni * np.sqrt(2 * np.log(n_trials))
    )
    # Simplified: E[max] ≈ mean + std * sqrt(2 * ln(N))
    expected_max = mean_sharpe + std_sharpe * np.sqrt(2 * np.log(n_trials))

    # Deflated = observed - expected maximum under null
    deflated = best_sharpe - expected_max

    return float(deflated)
