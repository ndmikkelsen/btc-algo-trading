"""
BTCMeanReversion Strategy

A mean reversion strategy that buys oversold conditions and exits when
price reverts to the mean. Uses Bollinger Bands and RSI to identify extremes.

Logic:
- Price oscillates around a moving average (mean)
- When price drops too far below mean = oversold = BUY opportunity
- When price returns to mean or goes too far above = EXIT

Entry Conditions (ALL must be true):
1. Price at or below lower Bollinger Band (%B <= 0)
2. RSI < 30 (oversold confirmation)
3. Volume spike (confirms selling exhaustion)

Exit Conditions (ANY triggers exit):
1. Price crosses above middle Bollinger Band (reverted to mean)
2. RSI > 70 (overbought)
3. ROI/Stoploss hit

Risk Management:
- Tight stoploss (-3%) since trends are the enemy of mean reversion
- Quick profit taking as price reverts
"""

from typing import Optional

from pandas import DataFrame

from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter, IStrategy

try:
    from . import config
    from .indicators import (
        calculate_bollinger_bands,
        calculate_percent_b,
        calculate_rsi,
        calculate_z_score,
    )
    from .signals import (
        check_bb_middle_cross_up,
        check_bb_oversold,
        check_rsi_overbought,
        check_rsi_oversold,
        check_volume_nonzero,
        check_volume_spike,
        combine_conditions,
    )
except ImportError:
    import config
    from indicators import (
        calculate_bollinger_bands,
        calculate_percent_b,
        calculate_rsi,
        calculate_z_score,
    )
    from signals import (
        check_bb_middle_cross_up,
        check_bb_oversold,
        check_rsi_overbought,
        check_rsi_oversold,
        check_volume_nonzero,
        check_volume_spike,
        combine_conditions,
    )


class BTCMeanReversion(IStrategy):
    """
    Mean reversion strategy using Bollinger Bands and RSI.
    Buys oversold, sells when price reverts to mean.
    """

    INTERFACE_VERSION = 3

    # Import settings from config
    timeframe = config.TIMEFRAME
    minimal_roi = config.MINIMAL_ROI
    stoploss = config.STOPLOSS
    trailing_stop = config.TRAILING_STOP
    trailing_stop_positive = config.TRAILING_STOP_POSITIVE
    trailing_stop_positive_offset = config.TRAILING_STOP_POSITIVE_OFFSET
    trailing_only_offset_is_reached = config.TRAILING_ONLY_OFFSET_IS_REACHED
    order_types = config.ORDER_TYPES
    order_time_in_force = config.ORDER_TIME_IN_FORCE
    process_only_new_candles = config.PROCESS_ONLY_NEW_CANDLES
    use_exit_signal = config.USE_EXIT_SIGNAL
    exit_profit_only = config.EXIT_PROFIT_ONLY
    ignore_roi_if_entry_signal = config.IGNORE_ROI_IF_ENTRY_SIGNAL
    startup_candle_count: int = config.STARTUP_CANDLE_COUNT

    # Hyperopt parameters - Bollinger Bands
    bb_period = IntParameter(10, 30, default=20, space="buy", optimize=True)
    # Only these std values are pre-calculated to avoid column explosion
    bb_std = CategoricalParameter([1.5, 2.0, 2.5, 3.0], default=2.0, space="buy", optimize=True)

    # Hyperopt parameters - RSI
    rsi_period = IntParameter(7, 21, default=14, space="buy", optimize=True)
    rsi_oversold = IntParameter(20, 40, default=30, space="buy", optimize=True)
    rsi_overbought = IntParameter(60, 80, default=70, space="sell", optimize=True)

    # Hyperopt parameters - Entry refinement
    bb_oversold_threshold = DecimalParameter(
        -0.2, 0.2, default=0.0, decimals=2, space="buy", optimize=True
    )
    volume_factor = DecimalParameter(
        1.0, 2.5, default=1.5, decimals=1, space="buy", optimize=True
    )

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate all indicators used by the strategy."""

        # Calculate Bollinger Bands for hyperopt ranges
        # Limit std values to reduce column explosion
        std_values = [1.5, 2.0, 2.5, 3.0]
        for period in self.bb_period.range:
            for std in std_values:
                upper, middle, lower = calculate_bollinger_bands(
                    dataframe, period=period, std_dev=std
                )
                # Format std consistently: 1.5 -> "1_5", 2.0 -> "2_0"
                std_str = f"{int(std)}_{int((std % 1) * 10)}"
                dataframe[f"bb_upper_{period}_{std_str}"] = upper
                dataframe[f"bb_middle_{period}_{std_str}"] = middle
                dataframe[f"bb_lower_{period}_{std_str}"] = lower

                # Calculate %B for this BB configuration
                dataframe[f"percent_b_{period}_{std_str}"] = calculate_percent_b(
                    dataframe,
                    f"bb_upper_{period}_{std_str}",
                    f"bb_lower_{period}_{std_str}",
                )

        # Calculate RSI for all period values (hyperopt)
        for period in self.rsi_period.range:
            dataframe[f"rsi_{period}"] = calculate_rsi(dataframe, period=period)

        # Z-Score for additional confirmation
        dataframe["z_score"] = calculate_z_score(dataframe, period=20)

        # Volume moving average
        dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry conditions for mean reversion:
        1. Price at/below lower Bollinger Band
        2. RSI oversold
        3. Volume spike (optional confirmation)
        """
        # Get column names based on current hyperopt values
        std_val = float(self.bb_std.value)
        std_str = f"{int(std_val)}_{int((std_val % 1) * 10)}"
        percent_b_col = f"percent_b_{self.bb_period.value}_{std_str}"
        bb_middle_col = f"bb_middle_{self.bb_period.value}_{std_str}"
        rsi_col = f"rsi_{self.rsi_period.value}"

        conditions = [
            # Price at or below lower Bollinger Band
            check_bb_oversold(dataframe, percent_b_col, self.bb_oversold_threshold.value),
            # RSI confirms oversold
            check_rsi_oversold(dataframe, rsi_col, self.rsi_oversold.value),
            # Volume confirmation
            check_volume_spike(dataframe, self.volume_factor.value),
            # Basic volume check
            check_volume_nonzero(dataframe),
        ]

        dataframe.loc[combine_conditions(conditions), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit conditions for mean reversion:
        1. Price crosses above middle Bollinger Band (reverted to mean)
        2. OR RSI overbought
        """
        std_val = float(self.bb_std.value)
        std_str = f"{int(std_val)}_{int((std_val % 1) * 10)}"
        bb_middle_col = f"bb_middle_{self.bb_period.value}_{std_str}"
        rsi_col = f"rsi_{self.rsi_period.value}"

        # Exit when price reverts to mean OR becomes overbought
        exit_conditions = (
            check_bb_middle_cross_up(dataframe, bb_middle_col)
            | check_rsi_overbought(dataframe, rsi_col, self.rsi_overbought.value)
        )

        # Also need volume
        exit_conditions = exit_conditions & check_volume_nonzero(dataframe)

        dataframe.loc[exit_conditions, "exit_long"] = 1
        return dataframe

    def leverage(
        self,
        pair: str,
        current_time: "datetime",
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> float:
        """Return 1x leverage for spot trading."""
        return 1.0
