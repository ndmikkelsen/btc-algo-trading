"""
Signal generation for BTCMomentumScalper strategy.

Functions for detecting entry/exit signals based on indicator values.
"""

from functools import reduce
from typing import List

from pandas import DataFrame, Series

import freqtrade.vendor.qtpylib.indicators as qtpylib


def check_ema_crossover_bullish(
    dataframe: DataFrame, short_col: str, long_col: str
) -> Series:
    """
    Check for bullish EMA crossover (short crosses above long).

    Args:
        dataframe: DataFrame with EMA columns
        short_col: Name of short EMA column
        long_col: Name of long EMA column

    Returns:
        Boolean Series where True indicates bullish crossover
    """
    return qtpylib.crossed_above(dataframe[short_col], dataframe[long_col])


def check_ema_crossover_bearish(
    dataframe: DataFrame, short_col: str, long_col: str
) -> Series:
    """
    Check for bearish EMA crossover (short crosses below long).

    Args:
        dataframe: DataFrame with EMA columns
        short_col: Name of short EMA column
        long_col: Name of long EMA column

    Returns:
        Boolean Series where True indicates bearish crossover
    """
    return qtpylib.crossed_below(dataframe[short_col], dataframe[long_col])


def check_rsi_conditions(
    dataframe: DataFrame, fast_rsi_max: int, slow_rsi_min: int
) -> Series:
    """
    Check RSI conditions for entry.

    Args:
        dataframe: DataFrame with 'rsi' and 'rsi_14' columns
        fast_rsi_max: Maximum value for fast RSI (not overbought)
        slow_rsi_min: Minimum value for slow RSI (confirming momentum)

    Returns:
        Boolean Series where True indicates RSI conditions met
    """
    fast_ok = dataframe["rsi"] < fast_rsi_max
    slow_ok = dataframe["rsi_14"] > slow_rsi_min
    return fast_ok & slow_ok


def check_adx_filter(dataframe: DataFrame, threshold: int = 20) -> Series:
    """
    Check ADX trend filter.

    Args:
        dataframe: DataFrame with 'adx' column
        threshold: Minimum ADX value for trending market (default 20)

    Returns:
        Boolean Series where True indicates trending market
    """
    return dataframe["adx"] > threshold


def check_volume_filter(
    dataframe: DataFrame, factor: float = 1.0
) -> Series:
    """
    Check volume filter (above average).

    Args:
        dataframe: DataFrame with 'volume' and 'volume_mean' columns
        factor: Multiplier for volume threshold (default 1.0)

    Returns:
        Boolean Series where True indicates sufficient volume
    """
    return dataframe["volume"] > (dataframe["volume_mean"] * factor)


def check_volume_nonzero(dataframe: DataFrame) -> Series:
    """
    Check that volume is non-zero.

    Args:
        dataframe: DataFrame with 'volume' column

    Returns:
        Boolean Series where True indicates non-zero volume
    """
    return dataframe["volume"] > 0


def combine_conditions(conditions: List[Series]) -> Series:
    """
    Combine multiple boolean conditions with AND logic.

    Args:
        conditions: List of boolean Series

    Returns:
        Boolean Series with all conditions combined
    """
    if not conditions:
        raise ValueError("At least one condition required")
    return reduce(lambda x, y: x & y, conditions)
