"""Tests for the MRBB preset comparison runner."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from scripts.compare_mrbb_presets import (
    backtest_preset,
    compute_trade_stats,
    format_table,
    run_comparison,
    save_results,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_equity_curve(n: int = 100, start: float = 10_000.0, delta: float = 1.0):
    """Build a simple equity curve for testing."""
    return [{"equity": start + i * delta} for i in range(n)]


def _make_trade_log(n_wins: int = 5, n_losses: int = 3):
    """Build a trade log with controlled wins/losses."""
    trades = []
    for _ in range(n_wins):
        trades.append({"side": "long", "entry_price": 100, "exit_price": 102, "size": 0.1, "pnl": 0.2, "reason": "target"})
    for _ in range(n_losses):
        trades.append({"side": "long", "entry_price": 100, "exit_price": 98, "size": 0.1, "pnl": -0.2, "reason": "stop_loss"})
    return trades


def _mock_sim_results(total_trades: int = 10):
    """Return a plausible simulator result dict."""
    ec = _make_equity_curve(100, 10_000.0, 0.5)
    tl = _make_trade_log(6, 4)
    return {
        "equity_curve": ec,
        "trade_log": tl,
        "total_trades": total_trades,
        "final_equity": ec[-1]["equity"],
        "total_return_pct": (ec[-1]["equity"] / 10_000.0 - 1) * 100,
    }


# ---------------------------------------------------------------------------
# Tests: compute_trade_stats
# ---------------------------------------------------------------------------

class TestComputeTradeStats:
    def test_empty_log(self):
        stats = compute_trade_stats([])
        assert stats["win_rate"] == 0.0
        assert stats["profit_factor"] == 0.0
        assert stats["avg_pnl"] == 0.0

    def test_all_winners(self):
        trades = [{"pnl": 10.0}, {"pnl": 5.0}]
        stats = compute_trade_stats(trades)
        assert stats["win_rate"] == 1.0
        assert stats["profit_factor"] == float("inf")
        assert stats["avg_pnl"] == 7.5

    def test_mixed(self):
        trades = [{"pnl": 10.0}, {"pnl": -5.0}]
        stats = compute_trade_stats(trades)
        assert stats["win_rate"] == 0.5
        assert stats["profit_factor"] == pytest.approx(2.0)
        assert stats["avg_pnl"] == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# Tests: backtest_preset
# ---------------------------------------------------------------------------

class TestBacktestPreset:
    @patch("scripts.compare_mrbb_presets.DirectionalSimulator")
    @patch("scripts.compare_mrbb_presets.MeanReversionBB")
    def test_returns_required_keys(self, mock_model_cls, mock_sim_cls):
        mock_sim = MagicMock()
        mock_sim.run_backtest_fast.return_value = _mock_sim_results()
        mock_sim_cls.return_value = mock_sim

        import pandas as pd
        df = pd.DataFrame({
            "open": [100.0] * 60,
            "high": [101.0] * 60,
            "low": [99.0] * 60,
            "close": [100.5] * 60,
            "volume": [1000.0] * 60,
        })

        result = backtest_preset("test_preset", {"bb_period": 20}, df, 10_000.0)

        expected_keys = {
            "preset", "return_pct", "sharpe", "sortino",
            "max_dd_pct", "calmar", "trades", "win_rate",
            "profit_factor", "avg_pnl", "final_equity",
        }
        assert set(result.keys()) == expected_keys
        assert result["preset"] == "test_preset"

    @patch("scripts.compare_mrbb_presets.DirectionalSimulator")
    @patch("scripts.compare_mrbb_presets.MeanReversionBB")
    def test_empty_equity_curve(self, mock_model_cls, mock_sim_cls):
        mock_sim = MagicMock()
        mock_sim.run_backtest_fast.return_value = {
            "equity_curve": [],
            "trade_log": [],
            "total_trades": 0,
            "final_equity": 10_000.0,
            "total_return_pct": 0.0,
        }
        mock_sim_cls.return_value = mock_sim

        import pandas as pd
        df = pd.DataFrame({
            "open": [100.0] * 5,
            "high": [101.0] * 5,
            "low": [99.0] * 5,
            "close": [100.5] * 5,
            "volume": [1000.0] * 5,
        })

        result = backtest_preset("empty", {}, df, 10_000.0)
        assert result["trades"] == 0
        assert result["return_pct"] == 0.0


# ---------------------------------------------------------------------------
# Tests: run_comparison
# ---------------------------------------------------------------------------

class TestRunComparison:
    @patch("scripts.compare_mrbb_presets.backtest_preset")
    @patch("scripts.compare_mrbb_presets.load_data")
    @patch("scripts.compare_mrbb_presets.PresetManager")
    def test_comparison_runs_all_presets(self, mock_pm_cls, mock_load, mock_bt):
        """Each available preset gets backtested."""
        pm = MagicMock()
        pm.list.return_value = ["default", "conservative", "aggressive"]
        pm.load.side_effect = lambda n: {"name": n, "bb_period": 20}
        mock_pm_cls.return_value = pm

        import pandas as pd
        mock_load.return_value = pd.DataFrame()

        mock_bt.side_effect = lambda name, params, df, eq: {
            "preset": name,
            "return_pct": 1.0,
            "sharpe": 0.5,
            "sortino": 0.8,
            "max_dd_pct": -3.0,
            "calmar": 0.3,
            "trades": 100,
            "win_rate": 0.4,
            "profit_factor": 1.1,
            "avg_pnl": 0.05,
            "final_equity": 10_100.0,
        }

        results = run_comparison(
            data_path="fake.csv",
            preset_names=None,
            initial_equity=10_000.0,
        )

        assert len(results) == 3
        preset_names = {r["preset"] for r in results}
        assert preset_names == {"default", "conservative", "aggressive"}

    @patch("scripts.compare_mrbb_presets.backtest_preset")
    @patch("scripts.compare_mrbb_presets.load_data")
    @patch("scripts.compare_mrbb_presets.PresetManager")
    def test_comparison_specific_presets(self, mock_pm_cls, mock_load, mock_bt):
        """Only specified presets are backtested."""
        pm = MagicMock()
        pm.load.side_effect = lambda n: {"name": n}
        mock_pm_cls.return_value = pm

        import pandas as pd
        mock_load.return_value = pd.DataFrame()

        mock_bt.side_effect = lambda name, params, df, eq: {
            "preset": name,
            "return_pct": 2.0,
            "sharpe": 1.0,
            "sortino": 1.5,
            "max_dd_pct": -2.0,
            "calmar": 0.5,
            "trades": 50,
            "win_rate": 0.5,
            "profit_factor": 1.2,
            "avg_pnl": 0.10,
            "final_equity": 10_200.0,
        }

        results = run_comparison(
            data_path="fake.csv",
            preset_names=["default", "aggressive"],
        )

        assert len(results) == 2


# ---------------------------------------------------------------------------
# Tests: format_table
# ---------------------------------------------------------------------------

class TestFormatTable:
    def test_comparison_output_has_required_columns(self):
        """Table output contains all required metric columns."""
        results = [
            {
                "preset": "default",
                "return_pct": 2.28,
                "sharpe": 0.45,
                "sortino": 0.60,
                "max_dd_pct": -5.1,
                "calmar": 0.3,
                "trades": 1120,
                "win_rate": 0.362,
                "profit_factor": 0.72,
                "avg_pnl": -0.11,
                "final_equity": 10_228.0,
            }
        ]
        table = format_table(results)

        assert "Preset" in table
        assert "Return" in table
        assert "Sharpe" in table
        assert "Max DD" in table
        assert "Trades" in table
        assert "Win Rate" in table
        assert "PF" in table
        assert "Avg P&L" in table
        assert "default" in table

    def test_empty_results(self):
        assert "No results" in format_table([])


# ---------------------------------------------------------------------------
# Tests: save_results
# ---------------------------------------------------------------------------

class TestSaveResults:
    def test_comparison_saves_json(self, tmp_path):
        """Results are saved as valid JSON to the output directory."""
        results = [
            {
                "preset": "default",
                "return_pct": 2.28,
                "sharpe": 0.45,
                "sortino": 0.60,
                "max_dd_pct": -5.1,
                "calmar": 0.3,
                "trades": 1120,
                "win_rate": 0.362,
                "profit_factor": 0.72,
                "avg_pnl": -0.11,
                "final_equity": 10_228.0,
            }
        ]

        out_path = save_results(results, tmp_path)
        assert out_path.exists()
        assert out_path.name == "comparison.json"

        with open(out_path) as f:
            loaded = json.load(f)

        assert len(loaded) == 1
        assert loaded[0]["preset"] == "default"
        assert loaded[0]["return_pct"] == pytest.approx(2.28)

    def test_saves_inf_values(self, tmp_path):
        """Infinity values are serialized as strings."""
        results = [
            {
                "preset": "perfect",
                "return_pct": 5.0,
                "sharpe": float("inf"),
                "sortino": float("inf"),
                "max_dd_pct": 0.0,
                "calmar": float("inf"),
                "trades": 10,
                "win_rate": 1.0,
                "profit_factor": float("inf"),
                "avg_pnl": 1.0,
                "final_equity": 10_500.0,
            }
        ]

        out_path = save_results(results, tmp_path)
        with open(out_path) as f:
            loaded = json.load(f)

        assert loaded[0]["sharpe"] == "inf"
        assert loaded[0]["profit_factor"] == "inf"
