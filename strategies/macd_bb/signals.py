"""Signal generation for MACD + Bollinger Bands strategy."""

import pandas as pd

# Opt-in to future pandas behavior to avoid deprecation warnings
pd.set_option("future.no_silent_downcasting", True)


def detect_macd_crossover(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect MACD crossovers.

    Args:
        df: DataFrame with 'macd' and 'macd_signal' columns

    Returns:
        DataFrame with macd_bullish_cross and macd_bearish_cross columns added
    """
    result = df.copy()

    # Calculate position relative to signal line
    macd_above = result["macd"] > result["macd_signal"]
    macd_above_prev = macd_above.shift(1)

    # Fill NaN from shift with False to avoid type errors
    macd_above_prev = macd_above_prev.fillna(False)
    macd_above_prev = macd_above_prev.infer_objects(copy=False).astype(bool)
    macd_above = macd_above.astype(bool)

    # Bullish cross: MACD crosses above signal (was below, now above)
    result["macd_bullish_cross"] = (~macd_above_prev) & macd_above

    # Bearish cross: MACD crosses below signal (was above, now below)
    result["macd_bearish_cross"] = macd_above_prev & (~macd_above)

    return result


def detect_bb_position(
    df: pd.DataFrame,
    near_threshold: float = 0.02,
    lookback: int = 3,
) -> pd.DataFrame:
    """
    Detect price position relative to Bollinger Bands.

    Args:
        df: DataFrame with 'close', 'bb_lower', 'bb_upper' columns
        near_threshold: Percentage threshold for "near" band (default 2%)
        lookback: Number of candles to look back for recent BB touch

    Returns:
        DataFrame with BB position columns added
    """
    result = df.copy()

    # Price at or below lower band (oversold)
    result["at_lower_bb"] = result["close"] <= result["bb_lower"]

    # Price near lower band (within threshold)
    result["near_lower_bb"] = result["close"] <= result["bb_lower"] * (1 + near_threshold)

    # Price was near lower BB recently (within lookback candles)
    result["recent_lower_bb"] = result["near_lower_bb"].rolling(
        window=lookback, min_periods=1
    ).max().astype(bool)

    # Price at or above upper band (overbought)
    result["at_upper_bb"] = result["close"] >= result["bb_upper"]

    # Price near upper band (within threshold)
    result["near_upper_bb"] = result["close"] >= result["bb_upper"] * (1 - near_threshold)

    return result


def generate_entry_signal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate entry signals.

    Entry when:
    - MACD bullish crossover (momentum shift)
    - Price was recently near lower Bollinger Band (oversold condition)

    This uses a lookback window because MACD crossovers typically occur
    after price has bounced off the lower BB, not exactly at it.

    Args:
        df: DataFrame with macd_bullish_cross and recent_lower_bb columns

    Returns:
        DataFrame with enter_long column added
    """
    result = df.copy()

    # Entry requires MACD crossover with recent oversold condition
    result["enter_long"] = (
        result["macd_bullish_cross"] & result["recent_lower_bb"]
    ).astype(int)

    return result


def generate_exit_signal(
    df: pd.DataFrame,
    exit_on_upper_bb: bool = False,
) -> pd.DataFrame:
    """
    Generate exit signals.

    Exit when:
    - MACD bearish crossover (momentum reversal)
    - OR price near upper Bollinger Band (if exit_on_upper_bb is True)

    Args:
        df: DataFrame with macd_bearish_cross and near_upper_bb columns
        exit_on_upper_bb: Whether to exit when price reaches upper BB

    Returns:
        DataFrame with exit_long column added
    """
    result = df.copy()

    if exit_on_upper_bb:
        # Exit on MACD bearish cross OR upper BB
        result["exit_long"] = (
            result["macd_bearish_cross"] | result["near_upper_bb"]
        ).astype(int)
    else:
        # Exit only on MACD bearish cross (let trailing stop handle profits)
        result["exit_long"] = result["macd_bearish_cross"].astype(int)

    return result
