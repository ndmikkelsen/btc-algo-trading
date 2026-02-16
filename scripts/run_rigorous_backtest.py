#!/usr/bin/env python3
"""Rigorous backtesting suite with anti-overfitting measures.

Runs comprehensive analysis including:
1. Walk-forward analysis
2. Out-of-sample testing
3. Parameter sensitivity analysis
4. Fee sensitivity
5. Slippage sensitivity
6. Fill rate sensitivity
7. Multi-source data comparison
8. Monte Carlo simulation

Usage:
    python scripts/run_rigorous_backtest.py
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from itertools import product
import sys
import json

from strategies.avellaneda_stoikov import AvellanedaStoikov, OrderManager, MarketSimulator
from strategies.avellaneda_stoikov.metrics import calculate_all_metrics
from strategies.avellaneda_stoikov.config import (
    MAKER_FEE, FILL_AGGRESSIVENESS, MAX_SLIPPAGE_PCT, STOP_LOSS_PCT,
)


# Default parameters (post-fix baseline)
DEFAULT_PARAMS = {
    'risk_aversion': 0.1,
    'order_book_liquidity': 1.5,
    'order_size': 0.001,
    'initial_cash': 10000.0,
    'max_inventory': 0.1,
    'maker_fee': MAKER_FEE,
    'use_regime_filter': True,
    'fill_aggressiveness': FILL_AGGRESSIVENESS,
    'max_slippage_pct': MAX_SLIPPAGE_PCT,
    'stop_loss_pct': STOP_LOSS_PCT,
    'min_spread': 0.0005,
    'max_spread': 0.05,
    'volatility_window': 50,
}


def load_data(filepath: str) -> pd.DataFrame:
    """Load OHLCV data from CSV."""
    df = pd.read_csv(filepath, parse_dates=['timestamp'], index_col='timestamp')
    return df


def run_single_backtest(
    df: pd.DataFrame,
    params: dict = None,
    random_seed: int = 42,
    verbose: bool = False,
) -> dict:
    """Run a single backtest with given parameters."""
    p = {**DEFAULT_PARAMS, **(params or {})}

    model = AvellanedaStoikov(
        risk_aversion=p['risk_aversion'],
        order_book_liquidity=p['order_book_liquidity'],
        volatility_window=p.get('volatility_window', 50),
        min_spread=p.get('min_spread', 0.0005),
        max_spread=p.get('max_spread', 0.05),
    )

    manager = OrderManager(
        initial_cash=p['initial_cash'],
        max_inventory=p['max_inventory'],
        maker_fee=p['maker_fee'],
    )

    simulator = MarketSimulator(
        model=model,
        order_manager=manager,
        order_size=p['order_size'],
        use_regime_filter=p['use_regime_filter'],
        fill_aggressiveness=p['fill_aggressiveness'],
        max_slippage_pct=p['max_slippage_pct'],
        stop_loss_pct=p['stop_loss_pct'],
        random_seed=random_seed,
    )

    results = simulator.run_backtest(df)

    if not results['equity_curve']:
        return {
            'total_return_pct': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown_pct': 0.0,
            'total_trades': 0,
            'final_pnl': 0.0,
            'realized_pnl': 0.0,
            'stop_loss_count': 0,
            'results': results,
        }

    metrics = calculate_all_metrics(
        equity_curve=results['equity_curve'],
        trades=results['trades'],
        initial_capital=p['initial_cash'],
        periods_per_year=8760,
    )

    return {
        'total_return_pct': metrics.get('total_return_pct', 0),
        'sharpe_ratio': metrics.get('sharpe_ratio', 0),
        'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
        'total_trades': results['total_trades'],
        'final_pnl': results['final_pnl'],
        'realized_pnl': results['realized_pnl'],
        'win_rate': metrics.get('win_rate', 0),
        'profit_factor': metrics.get('profit_factor', 0),
        'stop_loss_count': len(results.get('stop_loss_events', [])),
        'skipped_candles': results.get('skipped_candles', 0),
        'results': results,
    }


# =============================================================================
# 1. Walk-Forward Analysis
# =============================================================================

def walk_forward_analysis(df: pd.DataFrame, verbose: bool = True) -> list:
    """
    Walk-forward analysis: train on 6 months, test on 2 months, roll forward.
    """
    if verbose:
        print("\n" + "=" * 70)
        print("1. WALK-FORWARD ANALYSIS")
        print("=" * 70)

    hours_per_month = 24 * 30
    train_months = 6
    test_months = 2
    train_size = train_months * hours_per_month
    test_size = test_months * hours_per_month
    step_size = test_size

    folds = []
    start_idx = 0

    # Small parameter grid (3x3 = 9 combos per fold for speed)
    gamma_grid = [0.05, 0.1, 0.2]
    kappa_grid = [1.0, 1.5, 2.5]

    while start_idx + train_size + test_size <= len(df):
        train_df = df.iloc[start_idx:start_idx + train_size]
        test_df = df.iloc[start_idx + train_size:start_idx + train_size + test_size]

        if verbose:
            print(f"\nFold: Train {train_df.index[0].strftime('%Y-%m-%d')} to "
                  f"{train_df.index[-1].strftime('%Y-%m-%d')}, "
                  f"Test {test_df.index[0].strftime('%Y-%m-%d')} to "
                  f"{test_df.index[-1].strftime('%Y-%m-%d')}")

        # Optimize on training window
        best_return = -999
        best_params = {}

        for gamma, kappa in product(gamma_grid, kappa_grid):
            params = {
                'risk_aversion': gamma,
                'order_book_liquidity': kappa,
            }
            result = run_single_backtest(train_df, params, random_seed=42)
            ret = result['total_return_pct']
            if ret > best_return:
                best_return = ret
                best_params = params.copy()

        # Test best params on out-of-sample
        train_result = run_single_backtest(train_df, best_params, random_seed=42)
        test_result = run_single_backtest(test_df, best_params, random_seed=42)

        fold = {
            'train_start': str(train_df.index[0]),
            'train_end': str(train_df.index[-1]),
            'test_start': str(test_df.index[0]),
            'test_end': str(test_df.index[-1]),
            'best_params': best_params,
            'train_return': train_result['total_return_pct'],
            'test_return': test_result['total_return_pct'],
            'train_sharpe': train_result['sharpe_ratio'],
            'test_sharpe': test_result['sharpe_ratio'],
            'train_trades': train_result['total_trades'],
            'test_trades': test_result['total_trades'],
            'train_drawdown': train_result['max_drawdown_pct'],
            'test_drawdown': test_result['max_drawdown_pct'],
        }
        folds.append(fold)

        if verbose:
            print(f"  Best params: γ={best_params.get('risk_aversion')}, "
                  f"κ={best_params.get('order_book_liquidity')}, "
                  f"min_spread={best_params.get('min_spread')}")
            print(f"  Train: {fold['train_return']:+.2f}% return, "
                  f"Sharpe={fold['train_sharpe']:.2f}")
            print(f"  Test:  {fold['test_return']:+.2f}% return, "
                  f"Sharpe={fold['test_sharpe']:.2f}")

        start_idx += step_size

    return folds


# =============================================================================
# 2. Out-of-Sample Test
# =============================================================================

def out_of_sample_test(df: pd.DataFrame, verbose: bool = True) -> dict:
    """Hold out most recent 3 months, test current params on it."""
    if verbose:
        print("\n" + "=" * 70)
        print("2. OUT-OF-SAMPLE TEST")
        print("=" * 70)

    hours_3months = 24 * 30 * 3
    if len(df) < hours_3months + 720:
        if verbose:
            print("  Insufficient data for out-of-sample test")
        return {}

    in_sample = df.iloc[:-hours_3months]
    out_of_sample = df.iloc[-hours_3months:]

    in_result = run_single_backtest(in_sample, random_seed=42)
    out_result = run_single_backtest(out_of_sample, random_seed=42)

    results = {
        'in_sample_period': f"{in_sample.index[0]} to {in_sample.index[-1]}",
        'out_of_sample_period': f"{out_of_sample.index[0]} to {out_of_sample.index[-1]}",
        'in_sample_return': in_result['total_return_pct'],
        'out_of_sample_return': out_result['total_return_pct'],
        'in_sample_sharpe': in_result['sharpe_ratio'],
        'out_of_sample_sharpe': out_result['sharpe_ratio'],
        'in_sample_trades': in_result['total_trades'],
        'out_of_sample_trades': out_result['total_trades'],
        'in_sample_drawdown': in_result['max_drawdown_pct'],
        'out_of_sample_drawdown': out_result['max_drawdown_pct'],
        'in_sample_stop_losses': in_result['stop_loss_count'],
        'out_of_sample_stop_losses': out_result['stop_loss_count'],
    }

    if verbose:
        print(f"  In-sample: {results['in_sample_return']:+.2f}% return, "
              f"Sharpe={results['in_sample_sharpe']:.2f}, "
              f"Trades={results['in_sample_trades']}")
        print(f"  Out-of-sample: {results['out_of_sample_return']:+.2f}% return, "
              f"Sharpe={results['out_of_sample_sharpe']:.2f}, "
              f"Trades={results['out_of_sample_trades']}")

    return results


# =============================================================================
# 3. Parameter Sensitivity
# =============================================================================

def parameter_sensitivity(df: pd.DataFrame, verbose: bool = True) -> dict:
    """Vary key parameters by -50%, -20%, 0%, +20%, +50%."""
    if verbose:
        print("\n" + "=" * 70)
        print("3. PARAMETER SENSITIVITY ANALYSIS")
        print("=" * 70)

    multipliers = [0.5, 0.8, 1.0, 1.2, 1.5]
    param_names = ['risk_aversion', 'order_book_liquidity', 'min_spread', 'volatility_window']
    base_values = {
        'risk_aversion': DEFAULT_PARAMS['risk_aversion'],
        'order_book_liquidity': DEFAULT_PARAMS['order_book_liquidity'],
        'min_spread': DEFAULT_PARAMS['min_spread'],
        'volatility_window': DEFAULT_PARAMS['volatility_window'],
    }

    # Baseline
    baseline = run_single_backtest(df, random_seed=42)
    baseline_return = baseline['total_return_pct']

    results = {'baseline_return': baseline_return, 'parameters': {}}

    for param_name in param_names:
        param_results = []
        for mult in multipliers:
            val = base_values[param_name] * mult
            if param_name == 'volatility_window':
                val = max(5, int(val))
            params = {param_name: val}
            result = run_single_backtest(df, params, random_seed=42)
            param_results.append({
                'multiplier': mult,
                'value': val,
                'return_pct': result['total_return_pct'],
                'sharpe': result['sharpe_ratio'],
                'trades': result['total_trades'],
            })

        # Check overfitting signal: >50% performance change at +/-20%
        returns_at_mult = {r['multiplier']: r['return_pct'] for r in param_results}
        base_ret = returns_at_mult.get(1.0, 0)

        overfitting_flag = False
        if base_ret != 0:
            for m in [0.8, 1.2]:
                change = abs(returns_at_mult.get(m, 0) - base_ret) / abs(base_ret)
                if change > 0.5:
                    overfitting_flag = True

        results['parameters'][param_name] = {
            'base_value': base_values[param_name],
            'sensitivity': param_results,
            'overfitting_flag': overfitting_flag,
        }

        if verbose:
            print(f"\n  {param_name} (base={base_values[param_name]}):")
            for r in param_results:
                flag = " *** OVERFITTING" if (r['multiplier'] in [0.8, 1.2] and overfitting_flag) else ""
                print(f"    {r['multiplier']:.0%}: val={r['value']:.4f}, "
                      f"return={r['return_pct']:+.2f}%, "
                      f"sharpe={r['sharpe']:.2f}, "
                      f"trades={r['trades']}{flag}")

    return results


# =============================================================================
# 4. Fee Sensitivity
# =============================================================================

def fee_sensitivity(df: pd.DataFrame, verbose: bool = True) -> list:
    """Run at various fee levels to find break-even."""
    if verbose:
        print("\n" + "=" * 70)
        print("4. FEE SENSITIVITY")
        print("=" * 70)

    fee_levels = [0.0005, 0.00075, 0.001, 0.00125, 0.0015, 0.002]
    results = []

    for fee in fee_levels:
        result = run_single_backtest(df, {'maker_fee': fee}, random_seed=42)
        entry = {
            'fee_pct': fee * 100,
            'return_pct': result['total_return_pct'],
            'sharpe': result['sharpe_ratio'],
            'trades': result['total_trades'],
            'pnl': result['final_pnl'],
        }
        results.append(entry)

        if verbose:
            print(f"  Fee {fee*100:.3f}%: return={entry['return_pct']:+.2f}%, "
                  f"sharpe={entry['sharpe']:.2f}, trades={entry['trades']}")

    # Find approximate break-even
    for i, r in enumerate(results):
        if r['return_pct'] <= 0 and i > 0:
            prev = results[i - 1]
            if prev['return_pct'] > 0:
                # Linear interpolation
                break_even = prev['fee_pct'] + (
                    (0 - prev['return_pct']) /
                    (r['return_pct'] - prev['return_pct']) *
                    (r['fee_pct'] - prev['fee_pct'])
                )
                if verbose:
                    print(f"\n  Estimated break-even fee: {break_even:.4f}%")
                break

    return results


# =============================================================================
# 5. Slippage Sensitivity
# =============================================================================

def slippage_sensitivity(df: pd.DataFrame, verbose: bool = True) -> list:
    """Run at various slippage levels."""
    if verbose:
        print("\n" + "=" * 70)
        print("5. SLIPPAGE SENSITIVITY")
        print("=" * 70)

    slippage_levels = [0.0, 0.0001, 0.0002, 0.0005, 0.001]
    results = []

    for slip in slippage_levels:
        result = run_single_backtest(df, {'max_slippage_pct': slip}, random_seed=42)
        entry = {
            'slippage_pct': slip * 100,
            'return_pct': result['total_return_pct'],
            'sharpe': result['sharpe_ratio'],
            'trades': result['total_trades'],
        }
        results.append(entry)

        if verbose:
            print(f"  Slippage {slip*100:.3f}%: return={entry['return_pct']:+.2f}%, "
                  f"sharpe={entry['sharpe']:.2f}")

    return results


# =============================================================================
# 6. Fill Rate Sensitivity
# =============================================================================

def fill_rate_sensitivity(df: pd.DataFrame, verbose: bool = True) -> list:
    """Run at various fill aggressiveness levels."""
    if verbose:
        print("\n" + "=" * 70)
        print("6. FILL RATE SENSITIVITY")
        print("=" * 70)

    aggressiveness_levels = [20.0, 10.0, 5.0, 2.0]
    labels = ['High (20)', 'Default (10)', 'Conservative (5)', 'Very Conservative (2)']
    results = []

    for agg, label in zip(aggressiveness_levels, labels):
        result = run_single_backtest(df, {'fill_aggressiveness': agg}, random_seed=42)
        entry = {
            'label': label,
            'aggressiveness': agg,
            'return_pct': result['total_return_pct'],
            'sharpe': result['sharpe_ratio'],
            'trades': result['total_trades'],
        }
        results.append(entry)

        if verbose:
            print(f"  {label}: return={entry['return_pct']:+.2f}%, "
                  f"sharpe={entry['sharpe']:.2f}, trades={entry['trades']}")

    return results


# =============================================================================
# 7. Multi-Source Data Test
# =============================================================================

def multi_source_test(data_dir: str = "data", verbose: bool = True) -> list:
    """Run same config on data from each exchange."""
    if verbose:
        print("\n" + "=" * 70)
        print("7. MULTI-SOURCE DATA COMPARISON")
        print("=" * 70)

    exchanges = {
        'OKX': 'okx_btcusdt_1h.csv',
        'KuCoin': 'kucoin_btcusdt_1h.csv',
        'Bitfinex': 'bitfinex_btcusdt_1h.csv',
        'Kraken': 'kraken_btcusd_1h.csv',
        'Bitstamp': 'bitstamp_btcusd_1h.csv',
    }

    results = []
    for name, filename in exchanges.items():
        filepath = Path(data_dir) / filename
        if not filepath.exists():
            if verbose:
                print(f"  {name}: data not found, skipping")
            continue

        try:
            df = load_data(str(filepath))
            if len(df) < 720:  # Need at least 30 days
                if verbose:
                    print(f"  {name}: insufficient data ({len(df)} rows), skipping")
                continue

            result = run_single_backtest(df, random_seed=42)
            entry = {
                'exchange': name,
                'candles': len(df),
                'return_pct': result['total_return_pct'],
                'sharpe': result['sharpe_ratio'],
                'trades': result['total_trades'],
                'drawdown': result['max_drawdown_pct'],
                'stop_losses': result['stop_loss_count'],
            }
            results.append(entry)

            if verbose:
                print(f"  {name} ({len(df)} candles): "
                      f"return={entry['return_pct']:+.2f}%, "
                      f"sharpe={entry['sharpe']:.2f}, "
                      f"trades={entry['trades']}, "
                      f"drawdown={entry['drawdown']:.2f}%")
        except Exception as e:
            if verbose:
                print(f"  {name}: error - {e}")

    return results


# =============================================================================
# 8. Monte Carlo Simulation
# =============================================================================

def monte_carlo_simulation(
    df: pd.DataFrame,
    n_iterations: int = 100,
    verbose: bool = True,
) -> dict:
    """Run many iterations with different random seeds for fill probability."""
    if verbose:
        print("\n" + "=" * 70)
        print("8. MONTE CARLO SIMULATION (varying fill randomness)")
        print("=" * 70)

    returns = []
    sharpes = []
    trades_list = []

    for i in range(n_iterations):
        result = run_single_backtest(df, random_seed=i)
        returns.append(result['total_return_pct'])
        sharpes.append(result['sharpe_ratio'])
        trades_list.append(result['total_trades'])

        if verbose and (i + 1) % 20 == 0:
            print(f"  Completed {i + 1}/{n_iterations} iterations...")

    returns = np.array(returns)
    sharpes = np.array(sharpes)

    results = {
        'n_iterations': n_iterations,
        'return_mean': float(np.mean(returns)),
        'return_median': float(np.median(returns)),
        'return_5th': float(np.percentile(returns, 5)),
        'return_95th': float(np.percentile(returns, 95)),
        'return_std': float(np.std(returns)),
        'sharpe_mean': float(np.mean(sharpes)),
        'sharpe_median': float(np.median(sharpes)),
        'sharpe_5th': float(np.percentile(sharpes, 5)),
        'sharpe_95th': float(np.percentile(sharpes, 95)),
        'trades_mean': float(np.mean(trades_list)),
        'trades_std': float(np.std(trades_list)),
        'pct_profitable': float(np.sum(returns > 0) / len(returns) * 100),
    }

    if verbose:
        print(f"\n  Returns: mean={results['return_mean']:+.2f}%, "
              f"median={results['return_median']:+.2f}%")
        print(f"  90% CI: [{results['return_5th']:+.2f}%, {results['return_95th']:+.2f}%]")
        print(f"  Sharpe: mean={results['sharpe_mean']:.2f}, "
              f"median={results['sharpe_median']:.2f}")
        print(f"  Profitable iterations: {results['pct_profitable']:.0f}%")
        print(f"  Avg trades: {results['trades_mean']:.0f} ± {results['trades_std']:.0f}")

    return results


# =============================================================================
# Report Generation
# =============================================================================

def generate_report(all_results: dict, output_path: str = "docs/BACKTEST_REPORT.md"):
    """Generate comprehensive markdown report."""
    lines = []
    lines.append("# Rigorous Backtest Report")
    lines.append("")
    lines.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Strategy**: Avellaneda-Stoikov Market Making (post-audit fixes)")
    lines.append("**Fixes Applied**: C1 (double-fill), C2 (fill model), "
                 "C3 (reservation price), C4 (spread scaling), C5 (stop-loss)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    mc = all_results.get('monte_carlo', {})
    oos = all_results.get('out_of_sample', {})
    if mc:
        lines.append(f"- **Monte Carlo Mean Return**: {mc.get('return_mean', 0):+.2f}% "
                     f"(90% CI: [{mc.get('return_5th', 0):+.2f}%, {mc.get('return_95th', 0):+.2f}%])")
        lines.append(f"- **Profitable in**: {mc.get('pct_profitable', 0):.0f}% of simulations")
        lines.append(f"- **Mean Sharpe**: {mc.get('sharpe_mean', 0):.2f}")
    if oos:
        lines.append(f"- **Out-of-Sample Return**: {oos.get('out_of_sample_return', 0):+.2f}%")
        lines.append(f"- **Out-of-Sample Sharpe**: {oos.get('out_of_sample_sharpe', 0):.2f}")
    lines.append("")

    # Verdict
    has_edge = False
    if mc and mc.get('pct_profitable', 0) > 55 and mc.get('return_mean', 0) > 0:
        has_edge = True
    verdict = "POSSIBLE EDGE" if has_edge else "NO RELIABLE EDGE DETECTED"
    lines.append(f"**Verdict**: **{verdict}**")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Walk-Forward
    lines.append("## 1. Walk-Forward Analysis")
    lines.append("")
    wf = all_results.get('walk_forward', [])
    if wf:
        lines.append("| Fold | Train Period | Test Period | Train Return | Test Return | Train Sharpe | Test Sharpe |")
        lines.append("|------|-------------|------------|-------------|------------|-------------|------------|")
        for i, f in enumerate(wf):
            lines.append(
                f"| {i+1} | {f['train_start'][:10]}→{f['train_end'][:10]} | "
                f"{f['test_start'][:10]}→{f['test_end'][:10]} | "
                f"{f['train_return']:+.2f}% | {f['test_return']:+.2f}% | "
                f"{f['train_sharpe']:.2f} | {f['test_sharpe']:.2f} |"
            )
        lines.append("")
        avg_train = np.mean([f['train_return'] for f in wf])
        avg_test = np.mean([f['test_return'] for f in wf])
        lines.append(f"**Average Train Return**: {avg_train:+.2f}%")
        lines.append(f"**Average Test Return**: {avg_test:+.2f}%")
        degradation = ((avg_train - avg_test) / abs(avg_train) * 100) if avg_train != 0 else 0
        lines.append(f"**Performance Degradation**: {degradation:.0f}%")
    else:
        lines.append("Insufficient data for walk-forward analysis.")
    lines.append("")

    # 2. Out-of-Sample
    lines.append("## 2. Out-of-Sample Test")
    lines.append("")
    if oos:
        lines.append("| Metric | In-Sample | Out-of-Sample |")
        lines.append("|--------|-----------|--------------|")
        lines.append(f"| Return | {oos['in_sample_return']:+.2f}% | {oos['out_of_sample_return']:+.2f}% |")
        lines.append(f"| Sharpe | {oos['in_sample_sharpe']:.2f} | {oos['out_of_sample_sharpe']:.2f} |")
        lines.append(f"| Trades | {oos['in_sample_trades']} | {oos['out_of_sample_trades']} |")
        lines.append(f"| Max DD | {oos['in_sample_drawdown']:.2f}% | {oos['out_of_sample_drawdown']:.2f}% |")
        lines.append(f"| Stop-losses | {oos['in_sample_stop_losses']} | {oos['out_of_sample_stop_losses']} |")
    else:
        lines.append("Insufficient data for out-of-sample test.")
    lines.append("")

    # 3. Parameter Sensitivity
    lines.append("## 3. Parameter Sensitivity")
    lines.append("")
    ps = all_results.get('parameter_sensitivity', {})
    if ps:
        for param_name, data in ps.get('parameters', {}).items():
            flag = " **OVERFITTING RISK**" if data['overfitting_flag'] else ""
            lines.append(f"### {param_name} (base={data['base_value']}){flag}")
            lines.append("")
            lines.append("| Multiplier | Value | Return | Sharpe | Trades |")
            lines.append("|-----------|-------|--------|--------|--------|")
            for s in data['sensitivity']:
                lines.append(
                    f"| {s['multiplier']:.0%} | {s['value']:.4f} | "
                    f"{s['return_pct']:+.2f}% | {s['sharpe']:.2f} | {s['trades']} |"
                )
            lines.append("")
    lines.append("")

    # 4. Fee Sensitivity
    lines.append("## 4. Fee Sensitivity")
    lines.append("")
    fees = all_results.get('fee_sensitivity', [])
    if fees:
        lines.append("| Fee Level | Return | Sharpe | Trades |")
        lines.append("|----------|--------|--------|--------|")
        for f in fees:
            lines.append(f"| {f['fee_pct']:.3f}% | {f['return_pct']:+.2f}% | "
                        f"{f['sharpe']:.2f} | {f['trades']} |")
    lines.append("")

    # 5. Slippage Sensitivity
    lines.append("## 5. Slippage Sensitivity")
    lines.append("")
    slips = all_results.get('slippage_sensitivity', [])
    if slips:
        lines.append("| Max Slippage | Return | Sharpe | Trades |")
        lines.append("|-------------|--------|--------|--------|")
        for s in slips:
            lines.append(f"| {s['slippage_pct']:.3f}% | {s['return_pct']:+.2f}% | "
                        f"{s['sharpe']:.2f} | {s['trades']} |")
    lines.append("")

    # 6. Fill Rate Sensitivity
    lines.append("## 6. Fill Rate Sensitivity")
    lines.append("")
    fills = all_results.get('fill_rate_sensitivity', [])
    if fills:
        lines.append("| Fill Level | Return | Sharpe | Trades |")
        lines.append("|-----------|--------|--------|--------|")
        for f in fills:
            lines.append(f"| {f['label']} | {f['return_pct']:+.2f}% | "
                        f"{f['sharpe']:.2f} | {f['trades']} |")
    lines.append("")

    # 7. Multi-Source
    lines.append("## 7. Multi-Source Data Comparison")
    lines.append("")
    multi = all_results.get('multi_source', [])
    if multi:
        lines.append("| Exchange | Candles | Return | Sharpe | Trades | Max DD | Stop-Losses |")
        lines.append("|---------|---------|--------|--------|--------|--------|-------------|")
        for m in multi:
            lines.append(
                f"| {m['exchange']} | {m['candles']} | {m['return_pct']:+.2f}% | "
                f"{m['sharpe']:.2f} | {m['trades']} | {m['drawdown']:.2f}% | "
                f"{m['stop_losses']} |"
            )
        if len(multi) > 1:
            returns = [m['return_pct'] for m in multi]
            lines.append("")
            lines.append(f"**Return Spread**: {max(returns) - min(returns):.2f}% "
                        f"(max {max(returns):+.2f}%, min {min(returns):+.2f}%)")
            if max(returns) - min(returns) > 5:
                lines.append("**WARNING**: Large return spread suggests data-source dependency.")
    lines.append("")

    # 8. Monte Carlo
    lines.append("## 8. Monte Carlo Simulation")
    lines.append("")
    if mc:
        lines.append(f"**Iterations**: {mc['n_iterations']}")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Mean Return | {mc['return_mean']:+.2f}% |")
        lines.append(f"| Median Return | {mc['return_median']:+.2f}% |")
        lines.append(f"| 5th Percentile | {mc['return_5th']:+.2f}% |")
        lines.append(f"| 95th Percentile | {mc['return_95th']:+.2f}% |")
        lines.append(f"| Std Dev | {mc['return_std']:.2f}% |")
        lines.append(f"| Mean Sharpe | {mc['sharpe_mean']:.2f} |")
        lines.append(f"| Median Sharpe | {mc['sharpe_median']:.2f} |")
        lines.append(f"| % Profitable | {mc['pct_profitable']:.0f}% |")
        lines.append(f"| Avg Trades | {mc['trades_mean']:.0f} ± {mc['trades_std']:.0f} |")
    lines.append("")

    # Conclusion
    lines.append("---")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append("### Key Findings After Fixes")
    lines.append("")

    # Build conclusion from data
    if mc:
        if mc['return_mean'] > 0 and mc['pct_profitable'] > 60:
            lines.append("1. Strategy shows positive expected return after realistic fill modeling")
        elif mc['return_mean'] > 0:
            lines.append("1. Strategy is marginally positive but unreliable "
                        f"(profitable in only {mc['pct_profitable']:.0f}% of simulations)")
        else:
            lines.append("1. **Strategy is NOT profitable** after applying realistic fill model, "
                        "slippage, and stop-losses")

    if oos:
        if oos['out_of_sample_return'] > 0:
            lines.append(f"2. Out-of-sample performance is positive ({oos['out_of_sample_return']:+.2f}%)")
        else:
            lines.append(f"2. Out-of-sample performance is NEGATIVE ({oos['out_of_sample_return']:+.2f}%)")

    ps_flags = sum(1 for p in ps.get('parameters', {}).values() if p.get('overfitting_flag'))
    if ps_flags > 0:
        lines.append(f"3. **{ps_flags} parameter(s) show overfitting risk** "
                    "(>50% performance change at ±20%)")
    else:
        lines.append("3. Parameters show reasonable stability (no overfitting flags)")

    if multi and len(multi) > 1:
        returns = [m['return_pct'] for m in multi]
        spread = max(returns) - min(returns)
        if spread > 5:
            lines.append(f"4. **Results vary significantly across data sources** "
                        f"(spread: {spread:.1f}%)")
        else:
            lines.append(f"4. Results are consistent across data sources (spread: {spread:.1f}%)")

    lines.append("")
    lines.append("### Impact of Audit Fixes")
    lines.append("")
    lines.append("- **C1 (Double-fill fix)**: Only one side fills per candle — "
                "eliminates free spread capture")
    lines.append("- **C2 (Realistic fills)**: Fill probability based on penetration depth, "
                "slippage added")
    lines.append("- **C3 (Reservation price)**: Using paper's exact formula "
                "(absolute adjustment, not percentage)")
    lines.append("- **C4 (Spread normalization)**: Spread properly scaled relative to price")
    lines.append("- **C5 (Stop-loss)**: Positions force-closed at "
                f"{DEFAULT_PARAMS['stop_loss_pct']*100:.1f}% loss")
    lines.append("")

    # Write report
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines))
    print(f"\nReport written to {output_path}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Rigorous backtesting suite")
    parser.add_argument('--data', default='data/okx_btcusdt_1h.csv',
                       help='Primary data file')
    parser.add_argument('--data-dir', default='data',
                       help='Directory with multi-source data')
    parser.add_argument('--monte-carlo-n', type=int, default=100,
                       help='Monte Carlo iterations')
    parser.add_argument('--output', default='docs/BACKTEST_REPORT.md',
                       help='Report output path')
    parser.add_argument('--quiet', '-q', action='store_true')
    args = parser.parse_args()

    verbose = not args.quiet

    print("=" * 70)
    print("RIGOROUS BACKTEST SUITE")
    print("Post-audit strategy evaluation with anti-overfitting measures")
    print("=" * 70)

    # Load primary data
    df = load_data(args.data)
    print(f"\nPrimary data: {len(df)} candles from {df.index[0]} to {df.index[-1]}")

    all_results = {}

    # Run all analyses
    all_results['walk_forward'] = walk_forward_analysis(df, verbose)
    all_results['out_of_sample'] = out_of_sample_test(df, verbose)
    all_results['parameter_sensitivity'] = parameter_sensitivity(df, verbose)
    all_results['fee_sensitivity'] = fee_sensitivity(df, verbose)
    all_results['slippage_sensitivity'] = slippage_sensitivity(df, verbose)
    all_results['fill_rate_sensitivity'] = fill_rate_sensitivity(df, verbose)
    all_results['multi_source'] = multi_source_test(args.data_dir, verbose)
    all_results['monte_carlo'] = monte_carlo_simulation(df, args.monte_carlo_n, verbose)

    # Generate report
    generate_report(all_results, args.output)

    return all_results


if __name__ == "__main__":
    main()
