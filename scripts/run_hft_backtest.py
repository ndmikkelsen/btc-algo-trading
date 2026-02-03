#!/usr/bin/env python3
"""HFT Backtest runner for Avellaneda-Stoikov strategy.

Configured for:
- $1,000 starting capital
- 4% risk per trade
- 2:1 Risk:Reward ratio

Usage:
    python scripts/run_hft_backtest.py [--timeframe 5m]
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path

from strategies.avellaneda_stoikov import (
    AvellanedaStoikov,
    OrderManager,
    MarketSimulator,
)
from strategies.avellaneda_stoikov.risk_manager import RiskManager
from strategies.avellaneda_stoikov.metrics import calculate_all_metrics
from strategies.avellaneda_stoikov.config_hft import (
    INITIAL_CAPITAL,
    RISK_PER_TRADE,
    RISK_REWARD_RATIO,
    MAX_POSITION_PCT,
    RISK_AVERSION,
    ORDER_BOOK_LIQUIDITY,
    VOLATILITY_WINDOW,
    MIN_SPREAD,
    MAX_SPREAD,
    STOP_LOSS_PCT,
    SESSION_LENGTH,
    MAKER_FEE,
    USE_REGIME_FILTER,
    TREND_POSITION_SCALE,
)


def load_data(timeframe: str = "5m", data_dir: str = "data") -> pd.DataFrame:
    """Load BTC/USDT OHLCV data."""
    data_path = Path(data_dir) / f"btcusdt_{timeframe}.csv"

    if not data_path.exists():
        raise FileNotFoundError(
            f"Data file not found: {data_path}\n"
            f"Run: python scripts/download_data.py --timeframe {timeframe}"
        )

    df = pd.read_csv(data_path, parse_dates=['timestamp'], index_col='timestamp')
    return df


def run_hft_backtest(
    df: pd.DataFrame,
    verbose: bool = True,
) -> dict:
    """
    Run HFT backtest with risk management.

    Uses:
    - $1,000 capital
    - 4% risk per trade ($40)
    - 2:1 R:R ratio
    """
    # Risk manager for position sizing
    risk_manager = RiskManager(
        initial_capital=INITIAL_CAPITAL,
        risk_per_trade=RISK_PER_TRADE,
        risk_reward_ratio=RISK_REWARD_RATIO,
        max_position_pct=MAX_POSITION_PCT,
    )

    if verbose:
        print("=" * 60)
        print("AVELLANEDA-STOIKOV HFT BACKTEST")
        print("=" * 60)
        print()
        print("Risk Parameters")
        print("-" * 40)
        print(f"  Initial Capital:    ${INITIAL_CAPITAL:,.2f}")
        print(f"  Risk Per Trade:     {RISK_PER_TRADE * 100:.1f}% (${risk_manager.get_risk_amount():.2f})")
        print(f"  Risk:Reward:        {RISK_REWARD_RATIO}:1")
        print(f"  Stop Loss:          {STOP_LOSS_PCT * 100:.2f}%")
        print(f"  Take Profit:        {STOP_LOSS_PCT * RISK_REWARD_RATIO * 100:.2f}%")
        print(f"  Max Position:       {MAX_POSITION_PCT * 100:.0f}% of capital")
        print()
        print("Model Parameters")
        print("-" * 40)
        print(f"  Risk Aversion (γ):  {RISK_AVERSION}")
        print(f"  Liquidity (κ):      {ORDER_BOOK_LIQUIDITY}")
        print(f"  Min Spread:         {MIN_SPREAD * 100:.3f}%")
        print(f"  Max Spread:         {MAX_SPREAD * 100:.1f}%")
        print(f"  Regime Filter:      {'ON' if USE_REGIME_FILTER else 'OFF'}")
        print()
        print("Data")
        print("-" * 40)
        print(f"  Candles:            {len(df)}")
        print(f"  Period:             {df.index[0]} to {df.index[-1]}")
        print()

    # Calculate dynamic order size based on current price
    current_price = df['close'].iloc[0]
    order_size = risk_manager.get_position_size_for_spread(
        mid_price=current_price,
        spread=MIN_SPREAD * 2,  # Assume typical spread
    )

    if verbose:
        print(f"  Order Size:         {order_size:.6f} BTC (${order_size * current_price:.2f})")
        print()

    # Initialize components
    model = AvellanedaStoikov(
        risk_aversion=RISK_AVERSION,
        order_book_liquidity=ORDER_BOOK_LIQUIDITY,
        volatility_window=VOLATILITY_WINDOW,
        min_spread=MIN_SPREAD,
        max_spread=MAX_SPREAD,
    )

    manager = OrderManager(
        initial_cash=INITIAL_CAPITAL,
        max_inventory=MAX_POSITION_PCT * INITIAL_CAPITAL / current_price,
        maker_fee=MAKER_FEE,
    )

    simulator = MarketSimulator(
        model=model,
        order_manager=manager,
        session_length=SESSION_LENGTH,
        order_size=order_size,
        use_regime_filter=USE_REGIME_FILTER,
    )

    # Run backtest
    results = simulator.run_backtest(df)

    # Calculate metrics
    periods_per_year = 365 * 24 * 12 if '5m' in str(df.index.freq or '5m') else 8760
    metrics = calculate_all_metrics(
        equity_curve=results['equity_curve'],
        trades=results['trades'],
        initial_capital=INITIAL_CAPITAL,
        periods_per_year=periods_per_year,
    )

    # Final equity
    final_equity = results['equity_curve'][-1]['equity'] if results['equity_curve'] else INITIAL_CAPITAL

    if verbose:
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print()
        print("Performance")
        print("-" * 40)
        print(f"  Final Equity:       ${final_equity:,.2f}")
        print(f"  Total Return:       {metrics.get('total_return_pct', 0):+.2f}%")
        print(f"  Max Drawdown:       {metrics.get('max_drawdown_pct', 0):.2f}%")
        print()
        print("Risk Metrics")
        print("-" * 40)
        sharpe = metrics.get('sharpe_ratio', 0)
        sortino = metrics.get('sortino_ratio', 0)
        print(f"  Sharpe Ratio:       {sharpe:.2f}" if sharpe != float('inf') else "  Sharpe Ratio:       ∞")
        print(f"  Sortino Ratio:      {sortino:.2f}" if sortino != float('inf') else "  Sortino Ratio:      ∞")
        print(f"  Calmar Ratio:       {metrics.get('calmar_ratio', 0):.2f}")
        print()
        print("Trading Statistics")
        print("-" * 40)
        print(f"  Total Trades:       {results['total_trades']}")
        wr = metrics.get('win_rate', 0)
        pf = metrics.get('profit_factor', 0)
        print(f"  Win Rate:           {wr * 100:.1f}%" if wr > 0 else "  Win Rate:           N/A")
        print(f"  Profit Factor:      {pf:.2f}" if pf != float('inf') else "  Profit Factor:      ∞")
        print()
        print("P&L Breakdown")
        print("-" * 40)
        print(f"  Realized P&L:       ${results['realized_pnl']:,.2f}")
        print(f"  Unrealized P&L:     ${results['unrealized_pnl']:,.2f}")
        print(f"  Total Fees:         ${manager.total_fees_paid:,.2f}")
        print(f"  Final Inventory:    {results['final_inventory']:.6f} BTC")

        # Regime stats
        if USE_REGIME_FILTER and results.get('regime_stats'):
            rs = results['regime_stats']
            print()
            print("Regime Analysis")
            print("-" * 40)
            print(f"  Trending Up:        {rs.get('trending_up_pct', 0):.1f}%")
            print(f"  Trending Down:      {rs.get('trending_down_pct', 0):.1f}%")
            print(f"  Ranging:            {rs.get('ranging_pct', 0):.1f}%")
            print(f"  Skipped Candles:    {results.get('skipped_candles', 0)}")

        print()
        print("=" * 60)

    return {
        'results': results,
        'metrics': metrics,
        'final_equity': final_equity,
        'risk_manager': risk_manager,
    }


def main():
    parser = argparse.ArgumentParser(description="Run A-S HFT backtest")
    parser.add_argument('--timeframe', '-t', default='5m', help='Timeframe (1m, 5m, 15m)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress output')

    args = parser.parse_args()

    # Load data
    try:
        df = load_data(args.timeframe)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nTrying 1h data instead...")
        df = load_data('1h')
        df = df.tail(200)  # Use last 200 hours

    # Run backtest
    results = run_hft_backtest(
        df=df,
        verbose=not args.quiet,
    )

    return results


if __name__ == "__main__":
    main()
