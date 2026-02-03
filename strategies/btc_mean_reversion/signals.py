"""
Signal generation for BTCMeanReversion strategy.

Entry signals when price is oversold, exit when price reverts to mean.
"""

from functools import reduce
from typing import List

from pandas import DataFrame, Series


def check_bb_oversold(dataframe: DataFrame, percent_b_col: str, threshold: float = 0.0) -> Series:
    """
    Check if price is at or below lower Bollinger Band (oversold).

    Args:
        dataframe: DataFrame with %B column
        percent_b_col: Name of %B column
        threshold: %B threshold (0 = at lower band, negative = below)

    Returns:
        Boolean Series where True indicates oversold
    """
    return dataframe[percent_b_col] <= threshold


def check_bb_overbought(dataframe: DataFrame, percent_b_col: str, threshold: float = 1.0) -> Series:
    """
    Check if price is at or above upper Bollinger Band (overbought).

    Args:
        dataframe: DataFrame with %B column
        percent_b_col: Name of %B column
        threshold: %B threshold (1 = at upper band, >1 = above)

    Returns:
        Boolean Series where True indicates overbought
    """
    return dataframe[percent_b_col] >= threshold


def check_bb_middle_cross_up(dataframe: DataFrame, middle_col: str) -> Series:
    """
    Check if price crosses above middle Bollinger Band (mean).

    Args:
        dataframe: DataFrame with middle band column
        middle_col: Name of middle band column

    Returns:
        Boolean Series where True indicates cross above middle
    """
    return (dataframe["close"] > dataframe[middle_col]) & (
        dataframe["close"].shift(1) <= dataframe[middle_col].shift(1)
    )


def check_rsi_oversold(dataframe: DataFrame, rsi_col: str, threshold: int = 30) -> Series:
    """
    Check if RSI indicates oversold condition.

    Args:
        dataframe: DataFrame with RSI column
        rsi_col: Name of RSI column
        threshold: RSI threshold (default 30)

    Returns:
        Boolean Series where True indicates oversold
    """
    return dataframe[rsi_col] < threshold


def check_rsi_overbought(dataframe: DataFrame, rsi_col: str, threshold: int = 70) -> Series:
    """
    Check if RSI indicates overbought condition.

    Args:
        dataframe: DataFrame with RSI column
        rsi_col: Name of RSI column
        threshold: RSI threshold (default 70)

    Returns:
        Boolean Series where True indicates overbought
    """
    return dataframe[rsi_col] > threshold


def check_rsi_exiting_oversold(dataframe: DataFrame, rsi_col: str, threshold: int = 30) -> Series:
    """
    Check if RSI is exiting oversold territory (turning up from below threshold).

    Args:
        dataframe: DataFrame with RSI column
        rsi_col: Name of RSI column
        threshold: RSI threshold

    Returns:
        Boolean Series where True indicates RSI turning up from oversold
    """
    return (dataframe[rsi_col] > threshold) & (dataframe[rsi_col].shift(1) <= threshold)


def check_z_score_oversold(dataframe: DataFrame, z_col: str, threshold: float = -2.0) -> Series:
    """
    Check if Z-score indicates oversold (price far below mean).

    Args:
        dataframe: DataFrame with Z-score column
        z_col: Name of Z-score column
        threshold: Z-score threshold (default -2.0 = 2 std devs below)

    Returns:
        Boolean Series where True indicates oversold
    """
    return dataframe[z_col] < threshold


def check_z_score_overbought(dataframe: DataFrame, z_col: str, threshold: float = 2.0) -> Series:
    """
    Check if Z-score indicates overbought (price far above mean).

    Args:
        dataframe: DataFrame with Z-score column
        z_col: Name of Z-score column
        threshold: Z-score threshold (default 2.0 = 2 std devs above)

    Returns:
        Boolean Series where True indicates overbought
    """
    return dataframe[z_col] > threshold


def check_volume_spike(dataframe: DataFrame, factor: float = 1.5) -> Series:
    """
    Check for volume spike (confirms reversal).

    Args:
        dataframe: DataFrame with volume and volume_mean columns
        factor: Volume multiplier threshold

    Returns:
        Boolean Series where True indicates volume spike
    """
    return dataframe["volume"] > (dataframe["volume_mean"] * factor)


def check_volume_nonzero(dataframe: DataFrame) -> Series:
    """Check that volume is non-zero."""
    return dataframe["volume"] > 0


def combine_conditions(conditions: List[Series]) -> Series:
    """Combine multiple boolean conditions with AND logic."""
    if not conditions:
        raise ValueError("At least one condition required")
    return reduce(lambda x, y: x & y, conditions)
