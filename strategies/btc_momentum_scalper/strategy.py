"""
BTCMomentumScalper Strategy

A momentum-based BTC scalping strategy for the 5-minute timeframe.
Combines fast EMA crossovers (9/21) with RSI momentum signals and ADX trend filter.

Target Metrics:
- Sharpe Ratio: > 1.5
- Max Drawdown: < 25%
- Win Rate: > 40%
- Profit Factor: > 1.5
"""

from typing import Optional

from pandas import DataFrame

from freqtrade.strategy import DecimalParameter, IntParameter, IStrategy

try:
    # When loaded as package (e.g., pytest)
    from . import config
    from .indicators import (
        calculate_adx,
        calculate_ema,
        calculate_rsi,
        calculate_volume_ma,
    )
    from .signals import (
        check_adx_filter,
        check_ema_crossover_bearish,
        check_ema_crossover_bullish,
        check_rsi_conditions,
        check_volume_filter,
        check_volume_nonzero,
        combine_conditions,
    )
except ImportError:
    # When loaded directly by freqtrade
    import config
    from indicators import (
        calculate_adx,
        calculate_ema,
        calculate_rsi,
        calculate_volume_ma,
    )
    from signals import (
        check_adx_filter,
        check_ema_crossover_bearish,
        check_ema_crossover_bullish,
        check_rsi_conditions,
        check_volume_filter,
        check_volume_nonzero,
        combine_conditions,
    )


class BTCMomentumScalper(IStrategy):
    """
    Momentum-based BTC scalping strategy using EMA crossover and RSI confirmation.
    Optimized for 5-minute timeframe with tight risk management.
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

    # Hyperopt parameters - Entry
    buy_ema_short = IntParameter(5, 15, default=9, space="buy", optimize=True)
    buy_ema_long = IntParameter(15, 30, default=21, space="buy", optimize=True)
    buy_rsi_max = IntParameter(60, 80, default=70, space="buy", optimize=True)
    buy_volume_factor = DecimalParameter(
        0.5, 2.0, default=1.0, decimals=1, space="buy", optimize=True
    )

    # Hyperopt parameters - Exit
    sell_rsi_max = IntParameter(70, 90, default=80, space="sell", optimize=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate all indicators used by the strategy."""
        # RSI - fast period for scalping entry timing
        dataframe["rsi"] = calculate_rsi(dataframe, period=3)

        # RSI - slower period for trend confirmation
        dataframe["rsi_14"] = calculate_rsi(dataframe, period=14)

        # ADX - trend strength filter
        dataframe["adx"] = calculate_adx(dataframe, period=14)

        # Calculate all EMA short values for hyperopt
        for val in self.buy_ema_short.range:
            dataframe[f"ema_short_{val}"] = calculate_ema(dataframe, period=val)

        # Calculate all EMA long values for hyperopt
        for val in self.buy_ema_long.range:
            dataframe[f"ema_long_{val}"] = calculate_ema(dataframe, period=val)

        # Volume moving average for liquidity filter
        dataframe["volume_mean"] = calculate_volume_ma(dataframe, window=20)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define entry conditions based on EMA crossover with confirmations."""
        ema_short_col = f"ema_short_{self.buy_ema_short.value}"
        ema_long_col = f"ema_long_{self.buy_ema_long.value}"

        conditions = [
            check_ema_crossover_bullish(dataframe, ema_short_col, ema_long_col),
            check_rsi_conditions(dataframe, self.buy_rsi_max.value, slow_rsi_min=40),
            check_adx_filter(dataframe, threshold=20),
            check_volume_filter(dataframe, factor=self.buy_volume_factor.value),
            check_volume_nonzero(dataframe),
        ]

        dataframe.loc[combine_conditions(conditions), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Define exit conditions based on EMA crossover reversal."""
        ema_short_col = f"ema_short_{self.buy_ema_short.value}"
        ema_long_col = f"ema_long_{self.buy_ema_long.value}"

        conditions = [
            check_ema_crossover_bearish(dataframe, ema_short_col, ema_long_col),
            check_volume_nonzero(dataframe),
        ]

        dataframe.loc[combine_conditions(conditions), "exit_long"] = 1
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
        """Return 1x leverage for spot trading (no leverage)."""
        return 1.0
