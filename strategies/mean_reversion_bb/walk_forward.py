"""Anchored walk-forward optimization for Mean Reversion BB strategy.

Splits historical data into rolling train/test windows, optimizes model
parameters on the training window, then validates on the out-of-sample
test window.

Walk-forward efficiency = OOS_return / IS_return (target > 0.5).

Usage:
    from strategies.mean_reversion_bb.walk_forward import WalkForwardOptimizer

    wfo = WalkForwardOptimizer(
        df=ohlcv_data,
        train_months=6,
        test_months=1,
    )
    report = wfo.run()
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable

import pandas as pd

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.simulator import DirectionalSimulator
from strategies.mean_reversion_bb.param_registry import ParamRegistry


@dataclass
class WindowResult:
    """Results for a single train/test window pair."""
    window_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    best_params: dict
    is_return_pct: float         # in-sample return %
    oos_return_pct: float        # out-of-sample return %
    is_trades: int
    oos_trades: int
    wf_efficiency: float         # OOS / IS (NaN if IS <= 0)
    oos_equity_curve: List[dict] = field(default_factory=list)
    oos_trade_log: List[dict] = field(default_factory=list)


@dataclass
class WalkForwardReport:
    """Aggregate report from walk-forward optimization."""
    windows: List[WindowResult]
    mean_wf_efficiency: float
    median_wf_efficiency: float
    total_oos_return_pct: float
    total_oos_trades: int
    num_profitable_windows: int
    num_windows: int


class WalkForwardOptimizer:
    """Anchored walk-forward optimizer.

    Splits data into overlapping train/test windows:
        Window 0: [0..train_end] train, [train_end..train_end+test] test
        Window 1: [0..train_end+step] train, [+step..+step+test] test
        ...

    For each window:
    1. Generate parameter candidates (random search by default)
    2. Run backtest on training data for each candidate
    3. Select best by objective (default: total_return_pct)
    4. Run backtest on test data with best params
    5. Calculate WF efficiency

    Args:
        df: OHLCV DataFrame with DatetimeIndex.
            Columns: open, high, low, close, volume
        train_months: Training window length in months
        test_months: Test window length in months
        n_candidates: Number of random param combos per window
        objective: Function(backtest_result) -> float to maximize
        initial_equity: Starting equity for each backtest
        seed: Random seed for reproducibility
    """

    def __init__(
        self,
        df: pd.DataFrame,
        train_months: int = 6,
        test_months: int = 1,
        n_candidates: int = 50,
        objective: Optional[Callable] = None,
        initial_equity: float = 10_000.0,
        seed: int = 42,
    ):
        self.df = df
        self.train_months = train_months
        self.test_months = test_months
        self.n_candidates = n_candidates
        self.initial_equity = initial_equity
        self.seed = seed

        # Default objective: maximize return %
        self.objective = objective or (lambda r: r["total_return_pct"])

        self.registry = ParamRegistry()

    # ------------------------------------------------------------------
    # Window generation
    # ------------------------------------------------------------------

    def _generate_windows(self) -> List[Dict]:
        """Generate anchored walk-forward windows.

        Anchored means the training window always starts at the beginning
        of the dataset and grows (or stays fixed) as we roll forward.

        Returns list of dicts with train_start, train_end, test_start, test_end.
        """
        idx = self.df.index
        data_start = idx.min()
        data_end = idx.max()

        # First train window: train_months from start
        train_end = data_start + pd.DateOffset(months=self.train_months)
        windows = []
        window_id = 0

        while train_end < data_end:
            test_start = train_end
            test_end = test_start + pd.DateOffset(months=self.test_months)

            # Clip test_end to data boundary
            if test_end > data_end:
                test_end = data_end

            # Only add if test window has meaningful data
            test_mask = (idx >= test_start) & (idx < test_end)
            if test_mask.sum() > 50:
                windows.append({
                    "window_id": window_id,
                    "train_start": data_start,
                    "train_end": train_end,
                    "test_start": test_start,
                    "test_end": test_end,
                })
                window_id += 1

            # Roll forward by test_months
            train_end = train_end + pd.DateOffset(months=self.test_months)

        return windows

    # ------------------------------------------------------------------
    # Single-window optimization
    # ------------------------------------------------------------------

    def _build_model(self, params: dict) -> MeanReversionBB:
        """Build a MeanReversionBB model from parameter dict."""
        model = MeanReversionBB(
            bb_period=params.get("bb_period", 20),
            bb_std_dev=params.get("bb_std_dev", 2.0),
            bb_inner_std_dev=params.get("bb_inner_std_dev", 1.0),
            vwap_period=params.get("vwap_period", 50),
            kc_period=params.get("kc_period", 20),
            kc_atr_multiplier=params.get("kc_atr_multiplier", 1.5),
            rsi_period=params.get("rsi_period", 14),
        )
        # Apply remaining params via registry
        self.registry.apply_to_model(model, params)
        return model

    def _run_backtest(self, df_slice: pd.DataFrame, params: dict) -> dict:
        """Run a single backtest with given params on a data slice."""
        model = self._build_model(params)
        sim = DirectionalSimulator(
            model=model,
            initial_equity=self.initial_equity,
            random_seed=self.seed,
        )
        return sim.run_backtest(df_slice)

    def _optimize_window(
        self, train_df: pd.DataFrame, candidates: List[dict],
    ) -> tuple:
        """Find best params on training data.

        Returns (best_params, best_score, best_result).
        """
        best_score = float("-inf")
        best_params = candidates[0] if candidates else self.registry.to_dict()
        best_result = None

        for params in candidates:
            result = self._run_backtest(train_df, params)
            score = self.objective(result)
            if score > best_score:
                best_score = score
                best_params = params
                best_result = result

        return best_params, best_score, best_result

    def _evaluate_window(self, window: dict, candidates: List[dict]) -> WindowResult:
        """Run optimization + OOS validation for one window."""
        idx = self.df.index
        train_mask = (idx >= window["train_start"]) & (idx < window["train_end"])
        test_mask = (idx >= window["test_start"]) & (idx < window["test_end"])

        train_df = self.df.loc[train_mask]
        test_df = self.df.loc[test_mask]

        # Optimize on training data
        best_params, _, is_result = self._optimize_window(train_df, candidates)

        is_return = is_result["total_return_pct"] if is_result else 0.0
        is_trades = is_result["total_trades"] if is_result else 0

        # Validate on test data
        oos_result = self._run_backtest(test_df, best_params)
        oos_return = oos_result["total_return_pct"]
        oos_trades = oos_result["total_trades"]

        # WF efficiency
        if is_return > 0:
            wf_eff = oos_return / is_return
        else:
            wf_eff = float("nan")

        return WindowResult(
            window_id=window["window_id"],
            train_start=window["train_start"],
            train_end=window["train_end"],
            test_start=window["test_start"],
            test_end=window["test_end"],
            best_params=best_params,
            is_return_pct=is_return,
            oos_return_pct=oos_return,
            is_trades=is_trades,
            oos_trades=oos_trades,
            wf_efficiency=wf_eff,
            oos_equity_curve=oos_result.get("equity_curve", []),
            oos_trade_log=oos_result.get("trade_log", []),
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, verbose: bool = True) -> WalkForwardReport:
        """Run the full walk-forward optimization.

        Args:
            verbose: Print progress to stdout

        Returns:
            WalkForwardReport with all window results and aggregate stats.
        """
        windows = self._generate_windows()
        if not windows:
            raise ValueError(
                f"Not enough data for walk-forward: need at least "
                f"{self.train_months + self.test_months} months"
            )

        if verbose:
            print(f"Walk-forward: {len(windows)} windows "
                  f"(train={self.train_months}m, test={self.test_months}m, "
                  f"candidates={self.n_candidates})")

        # Generate candidate parameters once (shared across windows)
        candidates = self.registry.generate_random(self.n_candidates, seed=self.seed)

        results: List[WindowResult] = []
        for window in windows:
            if verbose:
                print(
                    f"  Window {window['window_id']}: "
                    f"train {window['train_start'].strftime('%Y-%m-%d')} -> "
                    f"{window['train_end'].strftime('%Y-%m-%d')} | "
                    f"test -> {window['test_end'].strftime('%Y-%m-%d')}",
                    end="",
                    flush=True,
                )

            wr = self._evaluate_window(window, candidates)
            results.append(wr)

            if verbose:
                eff_str = f"{wr.wf_efficiency:.2f}" if wr.wf_efficiency == wr.wf_efficiency else "N/A"
                print(
                    f" | IS={wr.is_return_pct:+.1f}% OOS={wr.oos_return_pct:+.1f}% "
                    f"WFE={eff_str}"
                )

        # Aggregate
        valid_effs = [r.wf_efficiency for r in results if r.wf_efficiency == r.wf_efficiency]  # filter NaN
        mean_eff = sum(valid_effs) / len(valid_effs) if valid_effs else float("nan")
        sorted_effs = sorted(valid_effs)
        median_eff = (
            sorted_effs[len(sorted_effs) // 2] if sorted_effs else float("nan")
        )

        total_oos_return = sum(r.oos_return_pct for r in results)
        total_oos_trades = sum(r.oos_trades for r in results)
        profitable = sum(1 for r in results if r.oos_return_pct > 0)

        report = WalkForwardReport(
            windows=results,
            mean_wf_efficiency=mean_eff,
            median_wf_efficiency=median_eff,
            total_oos_return_pct=total_oos_return,
            total_oos_trades=total_oos_trades,
            num_profitable_windows=profitable,
            num_windows=len(results),
        )

        if verbose:
            print()
            print("=" * 60)
            print("WALK-FORWARD SUMMARY")
            print("=" * 60)
            print(f"Windows:             {report.num_windows}")
            print(f"Profitable windows:  {report.num_profitable_windows}/{report.num_windows}")
            print(f"Mean WF efficiency:  {report.mean_wf_efficiency:.3f}")
            print(f"Median WF efficiency:{report.median_wf_efficiency:.3f}")
            print(f"Total OOS return:    {report.total_oos_return_pct:+.2f}%")
            print(f"Total OOS trades:    {report.total_oos_trades}")
            eff_pass = "PASS" if report.mean_wf_efficiency > 0.5 else "FAIL"
            print(f"WFE > 0.5 check:     {eff_pass}")
            print("=" * 60)

        return report
