"""
Indicator calculations for BTCMomentumScalper strategy.

Pure functions for calculating technical indicators used in the strategy.
"""

import talib.abstract as ta
from pandas import DataFrame


def calculate_rsi(dataframe: DataFrame, period: int = 14) -> DataFrame:
    """
    Calculate RSI (Relative Strength Index).

    Args:
        dataframe: OHLCV dataframe with 'close' column
        period: RSI period (default 14)

    Returns:
        Series with RSI values (0-100 range)
    """
    return ta.RSI(dataframe, timeperiod=period)


def calculate_adx(dataframe: DataFrame, period: int = 14) -> DataFrame:
    """
    Calculate ADX (Average Directional Index) for trend strength.

    Args:
        dataframe: OHLCV dataframe with high, low, close columns
        period: ADX period (default 14)

    Returns:
        Series with ADX values (0-100 range, >25 indicates trending)
    """
    return ta.ADX(dataframe, timeperiod=period)


def calculate_ema(dataframe: DataFrame, period: int) -> DataFrame:
    """
    Calculate EMA (Exponential Moving Average).

    Args:
        dataframe: OHLCV dataframe with 'close' column
        period: EMA period

    Returns:
        Series with EMA values
    """
    return ta.EMA(dataframe, timeperiod=period)


def calculate_volume_ma(dataframe: DataFrame, window: int = 20) -> DataFrame:
    """
    Calculate volume moving average.

    Args:
        dataframe: OHLCV dataframe with 'volume' column
        window: Rolling window size (default 20)

    Returns:
        Series with volume moving average values
    """
    return dataframe["volume"].rolling(window=window).mean()
