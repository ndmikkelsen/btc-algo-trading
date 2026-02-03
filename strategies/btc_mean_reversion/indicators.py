"""
Indicator calculations for BTCMeanReversion strategy.

Mean reversion indicators to identify oversold/overbought conditions.
"""

import talib.abstract as ta
from pandas import DataFrame
import numpy as np


def calculate_bollinger_bands(
    dataframe: DataFrame, period: int = 20, std_dev: float = 2.0
) -> tuple:
    """
    Calculate Bollinger Bands.

    Args:
        dataframe: OHLCV dataframe
        period: Moving average period (default 20)
        std_dev: Number of standard deviations (default 2.0)

    Returns:
        Tuple of (upper_band, middle_band, lower_band) Series
    """
    bb = ta.BBANDS(dataframe, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
    # Abstract API returns DataFrame with 'upperband', 'middleband', 'lowerband' columns
    return bb["upperband"], bb["middleband"], bb["lowerband"]


def calculate_rsi(dataframe: DataFrame, period: int = 14) -> DataFrame:
    """
    Calculate RSI (Relative Strength Index).

    Args:
        dataframe: OHLCV dataframe
        period: RSI period (default 14)

    Returns:
        Series with RSI values (0-100)
    """
    return ta.RSI(dataframe, timeperiod=period)


def calculate_bb_width(dataframe: DataFrame, upper_col: str, lower_col: str, middle_col: str) -> DataFrame:
    """
    Calculate Bollinger Band width (volatility indicator).

    Args:
        dataframe: DataFrame with BB columns
        upper_col: Name of upper band column
        lower_col: Name of lower band column
        middle_col: Name of middle band column

    Returns:
        Series with BB width values
    """
    return (dataframe[upper_col] - dataframe[lower_col]) / dataframe[middle_col]


def calculate_percent_b(dataframe: DataFrame, upper_col: str, lower_col: str) -> DataFrame:
    """
    Calculate %B - where price is relative to Bollinger Bands.

    %B = (Price - Lower Band) / (Upper Band - Lower Band)
    - %B < 0: Below lower band (very oversold)
    - %B = 0: At lower band (oversold)
    - %B = 0.5: At middle band
    - %B = 1: At upper band (overbought)
    - %B > 1: Above upper band (very overbought)

    Args:
        dataframe: DataFrame with BB columns and close price
        upper_col: Name of upper band column
        lower_col: Name of lower band column

    Returns:
        Series with %B values
    """
    return (dataframe["close"] - dataframe[lower_col]) / (
        dataframe[upper_col] - dataframe[lower_col]
    )


def calculate_z_score(dataframe: DataFrame, period: int = 20) -> DataFrame:
    """
    Calculate Z-Score - how many standard deviations from mean.

    Args:
        dataframe: OHLCV dataframe
        period: Lookback period for mean/std calculation

    Returns:
        Series with Z-score values (typically -3 to +3)
    """
    rolling_mean = dataframe["close"].rolling(window=period).mean()
    rolling_std = dataframe["close"].rolling(window=period).std()
    return (dataframe["close"] - rolling_mean) / rolling_std


def calculate_stoch_rsi(dataframe: DataFrame, period: int = 14) -> tuple:
    """
    Calculate Stochastic RSI.

    Args:
        dataframe: OHLCV dataframe
        period: Period for calculation

    Returns:
        Tuple of (stoch_rsi_k, stoch_rsi_d) Series
    """
    fastk, fastd = ta.STOCHRSI(dataframe, timeperiod=period)
    return fastk, fastd
