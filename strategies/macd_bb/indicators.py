"""Indicator calculations for MACD + Bollinger Bands strategy."""

import pandas as pd
import numpy as np

from strategies.macd_bb.config import (
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    BB_PERIOD,
    BB_STD,
)


def calculate_macd(
    df: pd.DataFrame,
    fast: int = MACD_FAST,
    slow: int = MACD_SLOW,
    signal: int = MACD_SIGNAL,
) -> pd.DataFrame:
    """
    Calculate MACD indicators.

    Args:
        df: DataFrame with 'close' column
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)

    Returns:
        DataFrame with macd, macd_signal, macd_histogram columns added
    """
    result = df.copy()

    # Calculate EMAs
    ema_fast = result["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = result["close"].ewm(span=slow, adjust=False).mean()

    # MACD line is the difference between fast and slow EMA
    result["macd"] = ema_fast - ema_slow

    # Signal line is EMA of MACD line
    result["macd_signal"] = result["macd"].ewm(span=signal, adjust=False).mean()

    # Histogram is MACD minus signal
    result["macd_histogram"] = result["macd"] - result["macd_signal"]

    return result


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = BB_PERIOD,
    std: float = BB_STD,
) -> pd.DataFrame:
    """
    Calculate Bollinger Bands.

    Args:
        df: DataFrame with 'close' column
        period: Rolling window period (default: 20)
        std: Number of standard deviations (default: 2.0)

    Returns:
        DataFrame with bb_upper, bb_middle, bb_lower columns added
    """
    result = df.copy()

    # Middle band is SMA
    result["bb_middle"] = result["close"].rolling(window=period).mean()

    # Calculate standard deviation
    rolling_std = result["close"].rolling(window=period).std()

    # Upper and lower bands
    result["bb_upper"] = result["bb_middle"] + (rolling_std * std)
    result["bb_lower"] = result["bb_middle"] - (rolling_std * std)

    return result


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all MACD and Bollinger Band indicators to dataframe.

    Args:
        df: DataFrame with OHLCV columns

    Returns:
        DataFrame with all indicators added
    """
    result = calculate_macd(df)
    result = calculate_bollinger_bands(result)
    return result
