"""Unit tests for Combinatorial Purged Cross-Validation."""

import pytest
import numpy as np
import pandas as pd

from strategies.mean_reversion_bb.cpcv import (
    _split_into_groups,
    _apply_purge,
    _sharpe_from_returns,
    _deflated_sharpe,
    run_cpcv,
    CPCVResult,
    DEFAULT_N_GROUPS,
    DEFAULT_PURGE_GAP,
)
from tests.unit.mean_reversion_bb.conftest import make_ohlcv_df


def dummy_evaluate(train_df, test_df):
    """Dummy evaluation: compute Sharpe from close returns."""
    train_ret = train_df["close"].pct_change().dropna().values
    test_ret = test_df["close"].pct_change().dropna().values
    is_sharpe = _sharpe_from_returns(train_ret) if len(train_ret) > 1 else 0.0
    oos_sharpe = _sharpe_from_returns(test_ret) if len(test_ret) > 1 else 0.0
    return is_sharpe, oos_sharpe


# ===========================================================================
# Group splitting
# ===========================================================================


class TestSplitIntoGroups:

    def test_correct_number_of_groups(self):
        groups = _split_into_groups(600, 6)
        assert len(groups) == 6

    def test_groups_cover_all_indices(self):
        n = 600
        groups = _split_into_groups(n, 6)
        covered = set()
        for start, end in groups:
            covered.update(range(start, end))
        assert covered == set(range(n))

    def test_groups_non_overlapping(self):
        groups = _split_into_groups(600, 6)
        all_indices = []
        for start, end in groups:
            all_indices.extend(range(start, end))
        assert len(all_indices) == len(set(all_indices))


# ===========================================================================
# Purge
# ===========================================================================


class TestApplyPurge:

    def test_purge_removes_boundary_indices(self):
        train = np.arange(0, 50)
        test = np.arange(50, 100)
        purged = _apply_purge(train, test, purge_gap=10)
        # Indices 40-49 should be removed (within 10 of test start at 50)
        assert 49 not in purged
        assert 45 not in purged
        assert 0 in purged

    def test_zero_purge_gap_no_removal(self):
        train = np.arange(0, 50)
        test = np.arange(50, 100)
        purged = _apply_purge(train, test, purge_gap=0)
        np.testing.assert_array_equal(purged, train)

    def test_purge_result_smaller_than_original(self):
        train = np.arange(0, 100)
        test = np.arange(100, 200)
        purged = _apply_purge(train, test, purge_gap=20)
        assert len(purged) < len(train)


# ===========================================================================
# Sharpe helper
# ===========================================================================


class TestSharpeFromReturns:

    def test_positive_returns_positive_sharpe(self):
        returns = np.array([0.01, 0.02, 0.015, 0.01, 0.02])
        assert _sharpe_from_returns(returns) > 0

    def test_zero_std_returns_zero(self):
        returns = np.array([0.01, 0.01, 0.01])
        assert _sharpe_from_returns(returns) == 0.0

    def test_single_return_zero(self):
        returns = np.array([0.01])
        assert _sharpe_from_returns(returns) == 0.0


# ===========================================================================
# CPCV integration
# ===========================================================================


class TestRunCPCV:

    def test_returns_cpcv_result(self):
        df = make_ohlcv_df(600)
        result = run_cpcv(df, dummy_evaluate, n_groups=6, purge_gap=10)
        assert isinstance(result, CPCVResult)

    def test_correct_number_of_splits(self):
        """C(6,3) = 20 splits."""
        df = make_ohlcv_df(600)
        result = run_cpcv(df, dummy_evaluate, n_groups=6, purge_gap=10)
        assert result.n_splits == 20

    def test_pbo_bounded(self):
        """PBO should be between 0 and 1."""
        df = make_ohlcv_df(600)
        result = run_cpcv(df, dummy_evaluate, n_groups=6, purge_gap=10)
        assert 0.0 <= result.pbo <= 1.0

    def test_sharpe_lists_populated(self):
        df = make_ohlcv_df(600)
        result = run_cpcv(df, dummy_evaluate, n_groups=6, purge_gap=10)
        assert len(result.is_sharpes) == result.n_splits
        assert len(result.oos_sharpes) == result.n_splits

    def test_pbo_increases_with_randomness(self):
        """With a purely random evaluate_fn, PBO should be high."""
        df = make_ohlcv_df(600)
        rng = np.random.RandomState(42)

        def noisy_evaluate(train_df, test_df):
            # IS: random positive Sharpe, OOS: random (can be negative)
            is_s = abs(rng.randn()) * 0.5
            oos_s = rng.randn() * 0.3
            return is_s, oos_s

        result = run_cpcv(df, noisy_evaluate, n_groups=6, purge_gap=10)
        # With random OOS Sharpes, some should be negative → PBO > 0
        assert result.pbo > 0

    def test_different_n_groups(self):
        """Should work with different group counts."""
        df = make_ohlcv_df(400)
        result = run_cpcv(df, dummy_evaluate, n_groups=4, purge_gap=10)
        assert result.n_groups == 4
        # C(4,2) = 6
        assert result.n_splits == 6


# ===========================================================================
# Deflated Sharpe
# ===========================================================================


class TestDeflatedSharpe:

    def test_more_trials_lower_deflated(self):
        """More trials should produce lower (more deflated) Sharpe."""
        oos = [0.5, 0.3, 0.1, -0.1, 0.4, 0.2]
        d_few = _deflated_sharpe(oos[:3], oos[:3], n_trials=3)
        d_many = _deflated_sharpe(oos, oos, n_trials=20)
        # With more trials, expected max is higher, so deflated is lower
        assert d_many < d_few

    def test_single_trial_returns_zero(self):
        d = _deflated_sharpe([0.5], [0.5], n_trials=1)
        assert d == 0.0
