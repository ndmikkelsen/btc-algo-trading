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


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate ADX (Average Directional Index) for trend strength.

    ADX measures trend strength regardless of direction:
    - ADX < 20: Weak trend / ranging market
    - ADX 20-40: Developing trend
    - ADX > 40: Strong trend

    DI+ and DI- show trend direction:
    - DI+ > DI-: Uptrend
    - DI- > DI+: Downtrend

    Args:
        df: DataFrame with OHLCV columns
        period: ADX period (default: 14)

    Returns:
        DataFrame with adx, di_plus, di_minus columns added
    """
    result = df.copy()

    # Calculate True Range
    high_low = result["high"] - result["low"]
    high_close = abs(result["high"] - result["close"].shift(1))
    low_close = abs(result["low"] - result["close"].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    # Calculate directional movement
    up_move = result["high"] - result["high"].shift(1)
    down_move = result["low"].shift(1) - result["low"]

    # +DM and -DM
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # Smoothed TR, +DM, -DM using Wilder's smoothing
    atr = pd.Series(tr).ewm(span=period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm).ewm(span=period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).ewm(span=period, adjust=False).mean() / atr

    # DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(span=period, adjust=False).mean()

    result["adx"] = adx
    result["di_plus"] = plus_di
    result["di_minus"] = minus_di

    return result


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all MACD, Bollinger Band, and ADX indicators to dataframe.

    Args:
        df: DataFrame with OHLCV columns

    Returns:
        DataFrame with all indicators added
    """
    result = calculate_macd(df)
    result = calculate_bollinger_bands(result)
    result = calculate_adx(result)
    return result
