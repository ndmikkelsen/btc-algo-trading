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


def detect_bb_position(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect price position relative to Bollinger Bands.

    Args:
        df: DataFrame with 'close', 'bb_lower', 'bb_upper' columns

    Returns:
        DataFrame with at_lower_bb and at_upper_bb columns added
    """
    result = df.copy()

    # Price at or below lower band (oversold)
    result["at_lower_bb"] = result["close"] <= result["bb_lower"]

    # Price at or above upper band (overbought)
    result["at_upper_bb"] = result["close"] >= result["bb_upper"]

    return result


def generate_entry_signal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate entry signals.

    Entry when:
    - MACD bullish crossover (momentum shift)
    - Price at or below lower Bollinger Band (oversold)

    Args:
        df: DataFrame with macd_bullish_cross and at_lower_bb columns

    Returns:
        DataFrame with enter_long column added
    """
    result = df.copy()

    # Entry requires BOTH conditions
    result["enter_long"] = (
        result["macd_bullish_cross"] & result["at_lower_bb"]
    ).astype(int)

    return result


def generate_exit_signal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate exit signals.

    Exit when:
    - MACD bearish crossover (momentum reversal)
    - OR price at upper Bollinger Band (profit target zone)

    Args:
        df: DataFrame with macd_bearish_cross and at_upper_bb columns

    Returns:
        DataFrame with exit_long column added
    """
    result = df.copy()

    # Exit on EITHER condition
    result["exit_long"] = (
        result["macd_bearish_cross"] | result["at_upper_bb"]
    ).astype(int)

    return result
