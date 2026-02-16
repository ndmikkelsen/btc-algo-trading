#!/usr/bin/env python3
"""Backtest runner for Avellaneda-Stoikov market making strategy.

Usage:
    python scripts/run_as_backtest.py [--timeframe 1h] [--days 30]
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from strategies.avellaneda_stoikov import (
    AvellanedaStoikov,
    OrderManager,
    MarketSimulator,
)
from strategies.avellaneda_stoikov.metrics import calculate_all_metrics
from strategies.avellaneda_stoikov.regime import RegimeDetector
from strategies.avellaneda_stoikov.config import (
    MAKER_FEE, FILL_AGGRESSIVENESS, MAX_SLIPPAGE_PCT, STOP_LOSS_PCT,
)


def load_data(timeframe: str = "1h", data_dir: str = "data") -> pd.DataFrame:
    """Load BTC/USDT OHLCV data."""
    data_path = Path(data_dir) / f"btcusdt_{timeframe}.csv"

    if not data_path.exists():
        raise FileNotFoundError(
            f"Data file not found: {data_path}\n"
            f"Run: python scripts/download_data.py --timeframe {timeframe}"
        )

    df = pd.read_csv(data_path, parse_dates=['timestamp'], index_col='timestamp')
    return df


def run_backtest(
    df: pd.DataFrame,
    initial_cash: float = 10000.0,
    max_inventory: float = 0.1,
    risk_aversion: float = 0.1,
    order_book_liquidity: float = 1.5,
    order_size: float = 0.001,
    maker_fee: float = MAKER_FEE,
    use_regime_filter: bool = False,
    fill_aggressiveness: float = FILL_AGGRESSIVENESS,
    max_slippage_pct: float = MAX_SLIPPAGE_PCT,
    stop_loss_pct: float = STOP_LOSS_PCT,
    random_seed: int = None,
    verbose: bool = True,
) -> dict:
    """
    Run Avellaneda-Stoikov backtest.

    Args:
        df: OHLCV DataFrame
        initial_cash: Starting capital in USDT
        max_inventory: Maximum BTC position (absolute)
        risk_aversion: γ parameter (higher = more aggressive inventory management)
        order_book_liquidity: κ parameter (higher = tighter spreads)
        order_size: Size of each quote order
        maker_fee: Trading fee as decimal (0.001 = 0.1%)
        use_regime_filter: If True, reduce trading in trending markets
        verbose: Print progress updates

    Returns:
        Backtest results dictionary
    """
    if verbose:
        print(f"Running Avellaneda-Stoikov Backtest")
        print(f"=" * 50)
        print(f"Data: {len(df)} candles from {df.index[0]} to {df.index[-1]}")
        print(f"Initial cash: ${initial_cash:,.2f}")
        print(f"Max inventory: {max_inventory} BTC")
        print(f"Risk aversion (γ): {risk_aversion}")
        print(f"Order book liquidity (κ): {order_book_liquidity}")
        print(f"Order size: {order_size} BTC")
        print(f"Maker fee: {maker_fee * 100:.2f}%")
        print(f"Regime filter: {'ON' if use_regime_filter else 'OFF'}")
        print()

    # Initialize components
    model = AvellanedaStoikov(
        risk_aversion=risk_aversion,
        order_book_liquidity=order_book_liquidity,
    )

    manager = OrderManager(
        initial_cash=initial_cash,
        max_inventory=max_inventory,
        maker_fee=maker_fee,
    )

    simulator = MarketSimulator(
        model=model,
        order_manager=manager,
        order_size=order_size,
        use_regime_filter=use_regime_filter,
        fill_aggressiveness=fill_aggressiveness,
        max_slippage_pct=max_slippage_pct,
        stop_loss_pct=stop_loss_pct,
        random_seed=random_seed,
    )

    # Run backtest
    results = simulator.run_backtest(df)

    # Calculate statistics
    equity_df = pd.DataFrame(results['equity_curve'])
    initial_equity = initial_cash
    final_equity = equity_df['equity'].iloc[-1]

    # Trade statistics
    trades = results['trades']
    num_trades = len(trades)

    if num_trades > 0:
        buys = [t for t in trades if t['side'] == 'buy']
        sells = [t for t in trades if t['side'] == 'sell']
    else:
        buys, sells = [], []

    # Calculate performance metrics
    metrics = calculate_all_metrics(
        equity_curve=results['equity_curve'],
        trades=trades,
        initial_capital=initial_cash,
        periods_per_year=8760 if 'h' in str(df.index.freq or '1h') else 365,
    )

    # Get total fees from order manager
    total_fees = manager.total_fees_paid

    stats = {
        'initial_equity': initial_equity,
        'final_equity': final_equity,
        'total_return_pct': metrics.get('total_return_pct', 0),
        'total_pnl': results['final_pnl'],
        'realized_pnl': results['realized_pnl'],
        'unrealized_pnl': results['unrealized_pnl'],
        'total_fees_paid': total_fees,
        'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
        'sharpe_ratio': metrics.get('sharpe_ratio', 0),
        'sortino_ratio': metrics.get('sortino_ratio', 0),
        'calmar_ratio': metrics.get('calmar_ratio', 0),
        'win_rate': metrics.get('win_rate', 0),
        'profit_factor': metrics.get('profit_factor', 0),
        'total_trades': num_trades,
        'buy_trades': len(buys),
        'sell_trades': len(sells),
        'final_inventory': results['final_inventory'],
        'final_cash': results['final_cash'],
    }

    if verbose:
        print("Results")
        print("-" * 50)
        print(f"Final Equity:    ${final_equity:,.2f}")
        print(f"Total Return:    {stats['total_return_pct']:+.2f}%")
        print(f"Max Drawdown:    {stats['max_drawdown_pct']:.2f}%")
        print()
        print("Risk Metrics")
        print("-" * 50)
        sharpe = stats['sharpe_ratio']
        sortino = stats['sortino_ratio']
        print(f"Sharpe Ratio:    {sharpe:.2f}" if sharpe != float('inf') else "Sharpe Ratio:    ∞")
        print(f"Sortino Ratio:   {sortino:.2f}" if sortino != float('inf') else "Sortino Ratio:   ∞")
        print(f"Calmar Ratio:    {stats['calmar_ratio']:.2f}")
        print()
        print("Trade Statistics")
        print("-" * 50)
        print(f"Total Trades:    {num_trades}")
        print(f"  Buy trades:    {len(buys)}")
        print(f"  Sell trades:   {len(sells)}")
        wr = stats['win_rate']
        pf = stats['profit_factor']
        print(f"Win Rate:        {wr * 100:.1f}%" if wr > 0 else "Win Rate:        N/A")
        print(f"Profit Factor:   {pf:.2f}" if pf != float('inf') else "Profit Factor:   ∞")
        print()
        print("P&L Breakdown")
        print("-" * 50)
        print(f"Realized P&L:    ${results['realized_pnl']:,.2f}")
        print(f"Unrealized P&L:  ${results['unrealized_pnl']:,.2f}")
        print(f"Total Fees:      ${total_fees:,.2f}")
        print(f"Final Inventory: {results['final_inventory']:.6f} BTC")

        # Regime stats if enabled
        if use_regime_filter and results.get('regime_stats'):
            rs = results['regime_stats']
            print()
            print("Regime Analysis")
            print("-" * 50)
            print(f"Trending Up:     {rs.get('trending_up_pct', 0):.1f}%")
            print(f"Trending Down:   {rs.get('trending_down_pct', 0):.1f}%")
            print(f"Ranging:         {rs.get('ranging_pct', 0):.1f}%")
            print(f"Avg ADX:         {rs.get('avg_adx', 0):.1f}")
            print(f"Skipped Candles: {results.get('skipped_candles', 0)}")

    return {
        'stats': stats,
        'equity_curve': equity_df,
        'trades': trades,
        'results': results,
    }


def main():
    parser = argparse.ArgumentParser(description="Run A-S market making backtest")
    parser.add_argument('--timeframe', '-t', default='1h', help='Timeframe (1h, 4h, 1d)')
    parser.add_argument('--days', '-d', type=int, default=None, help='Limit to N days')
    parser.add_argument('--cash', '-c', type=float, default=10000.0, help='Initial cash')
    parser.add_argument('--max-inventory', type=float, default=0.1, help='Max BTC position')
    parser.add_argument('--risk-aversion', '-g', type=float, default=0.1, help='γ parameter')
    parser.add_argument('--liquidity', '-k', type=float, default=1.5, help='κ parameter')
    parser.add_argument('--order-size', '-s', type=float, default=0.001, help='Order size BTC')
    parser.add_argument('--fee', '-f', type=float, default=MAKER_FEE, help='Maker fee (decimal)')
    parser.add_argument('--regime-filter', action='store_true', help='Enable regime filter')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress output')

    args = parser.parse_args()

    # Load data
    df = load_data(args.timeframe)

    # Limit to N days if specified
    if args.days:
        df = df.tail(args.days * 24)  # Assuming hourly data

    # Run backtest
    results = run_backtest(
        df=df,
        initial_cash=args.cash,
        max_inventory=args.max_inventory,
        risk_aversion=args.risk_aversion,
        order_book_liquidity=args.liquidity,
        order_size=args.order_size,
        maker_fee=args.fee,
        use_regime_filter=args.regime_filter,
        verbose=not args.quiet,
    )

    return results


if __name__ == "__main__":
    main()
