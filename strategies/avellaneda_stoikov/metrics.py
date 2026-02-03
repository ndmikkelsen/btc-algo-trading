"""Performance metrics for backtesting analysis.

Calculates key trading metrics:
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
- Win Rate
- Profit Factor
- Calmar Ratio
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional


def calculate_returns(equity_curve: List[Dict]) -> pd.Series:
    """Calculate returns from equity curve."""
    equity = pd.Series([e['equity'] for e in equity_curve])
    returns = equity.pct_change().dropna()
    return returns


def sharpe_ratio(
    equity_curve: List[Dict],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 8760,  # Hourly data
) -> float:
    """
    Calculate annualized Sharpe Ratio.

    Args:
        equity_curve: List of equity curve dictionaries
        risk_free_rate: Annual risk-free rate (default 0)
        periods_per_year: Number of periods in a year

    Returns:
        Annualized Sharpe Ratio
    """
    returns = calculate_returns(equity_curve)

    if len(returns) < 2 or returns.std() == 0:
        return 0.0

    # Annualize
    excess_returns = returns - (risk_free_rate / periods_per_year)
    annualized_return = excess_returns.mean() * periods_per_year
    annualized_std = returns.std() * np.sqrt(periods_per_year)

    if annualized_std == 0:
        return 0.0

    return annualized_return / annualized_std


def sortino_ratio(
    equity_curve: List[Dict],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 8760,
) -> float:
    """
    Calculate annualized Sortino Ratio (downside risk only).

    Args:
        equity_curve: List of equity curve dictionaries
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods in a year

    Returns:
        Annualized Sortino Ratio
    """
    returns = calculate_returns(equity_curve)

    if len(returns) < 2:
        return 0.0

    # Downside returns only
    downside_returns = returns[returns < 0]

    if len(downside_returns) == 0:
        return float('inf')  # No downside

    downside_std = downside_returns.std() * np.sqrt(periods_per_year)

    if downside_std == 0:
        return float('inf')

    excess_returns = returns - (risk_free_rate / periods_per_year)
    annualized_return = excess_returns.mean() * periods_per_year

    return annualized_return / downside_std


def max_drawdown(equity_curve: List[Dict]) -> Dict[str, float]:
    """
    Calculate maximum drawdown and related metrics.

    Returns:
        Dict with max_drawdown_pct, max_drawdown_duration, recovery_time
    """
    equity = pd.Series([e['equity'] for e in equity_curve])

    # Rolling maximum
    rolling_max = equity.expanding().max()

    # Drawdown series
    drawdown = (equity - rolling_max) / rolling_max

    # Maximum drawdown
    max_dd = drawdown.min()

    # Find drawdown duration
    in_drawdown = drawdown < 0
    drawdown_periods = []
    current_period = 0

    for is_dd in in_drawdown:
        if is_dd:
            current_period += 1
        else:
            if current_period > 0:
                drawdown_periods.append(current_period)
            current_period = 0

    if current_period > 0:
        drawdown_periods.append(current_period)

    max_duration = max(drawdown_periods) if drawdown_periods else 0

    return {
        'max_drawdown_pct': max_dd * 100,
        'max_drawdown_duration': max_duration,
    }


def win_rate(trades: List[Dict]) -> float:
    """
    Calculate win rate from trades.

    Note: For market making, we calculate based on round-trip trades.
    """
    if not trades:
        return 0.0

    # Group trades into round trips (buy followed by sell or vice versa)
    # For simplicity, calculate profit per trade pair
    buys = [t for t in trades if t['side'] == 'buy']
    sells = [t for t in trades if t['side'] == 'sell']

    if not buys or not sells:
        return 0.0

    # Match buys with sells (FIFO)
    profitable = 0
    total = min(len(buys), len(sells))

    for i in range(total):
        buy_price = buys[i]['price']
        sell_price = sells[i]['price']

        if sell_price > buy_price:
            profitable += 1

    return profitable / total if total > 0 else 0.0


def profit_factor(trades: List[Dict]) -> float:
    """
    Calculate profit factor (gross profit / gross loss).

    Returns:
        Profit factor (>1 is profitable)
    """
    if not trades:
        return 0.0

    buys = [t for t in trades if t['side'] == 'buy']
    sells = [t for t in trades if t['side'] == 'sell']

    if not buys or not sells:
        return 0.0

    # Calculate P&L per round trip
    gross_profit = 0.0
    gross_loss = 0.0

    total = min(len(buys), len(sells))

    for i in range(total):
        buy_value = buys[i]['price'] * buys[i]['quantity']
        sell_value = sells[i]['price'] * sells[i]['quantity']
        pnl = sell_value - buy_value

        if pnl > 0:
            gross_profit += pnl
        else:
            gross_loss += abs(pnl)

    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0

    return gross_profit / gross_loss


def calmar_ratio(
    equity_curve: List[Dict],
    periods_per_year: int = 8760,
) -> float:
    """
    Calculate Calmar Ratio (annualized return / max drawdown).
    """
    if len(equity_curve) < 2:
        return 0.0

    # Calculate total return
    initial = equity_curve[0]['equity']
    final = equity_curve[-1]['equity']
    total_return = (final - initial) / initial

    # Annualize
    periods = len(equity_curve)
    years = periods / periods_per_year
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

    # Get max drawdown
    dd_info = max_drawdown(equity_curve)
    max_dd = abs(dd_info['max_drawdown_pct'] / 100)

    if max_dd == 0:
        return float('inf') if annualized_return > 0 else 0.0

    return annualized_return / max_dd


def calculate_all_metrics(
    equity_curve: List[Dict],
    trades: List[Dict],
    initial_capital: float,
    periods_per_year: int = 8760,
) -> Dict[str, float]:
    """
    Calculate all performance metrics.

    Args:
        equity_curve: List of equity dictionaries
        trades: List of trade dictionaries
        initial_capital: Starting capital
        periods_per_year: Trading periods per year

    Returns:
        Dictionary with all metrics
    """
    if not equity_curve:
        return {}

    final_equity = equity_curve[-1]['equity']
    total_return = (final_equity - initial_capital) / initial_capital * 100

    dd_info = max_drawdown(equity_curve)

    return {
        'total_return_pct': total_return,
        'sharpe_ratio': sharpe_ratio(equity_curve, periods_per_year=periods_per_year),
        'sortino_ratio': sortino_ratio(equity_curve, periods_per_year=periods_per_year),
        'max_drawdown_pct': dd_info['max_drawdown_pct'],
        'max_drawdown_duration': dd_info['max_drawdown_duration'],
        'calmar_ratio': calmar_ratio(equity_curve, periods_per_year=periods_per_year),
        'win_rate': win_rate(trades),
        'profit_factor': profit_factor(trades),
        'total_trades': len(trades),
    }
