"""
BTCMomentumScalper Strategy

A momentum-based BTC scalping strategy for the 5-minute timeframe.
Combines fast EMA crossovers (9/21) with RSI momentum signals and ADX trend filter.

Target Metrics:
- Sharpe Ratio: > 1.5
- Max Drawdown: < 25%
- Win Rate: > 40%
- Profit Factor: > 1.5

Entry Logic:
- EMA 9 crosses above EMA 21 (bullish momentum)
- RSI(3) < 70 (not overbought on fast RSI)
- RSI(14) > 40 (confirming upward momentum on slower RSI)
- ADX > 20 (trending market, avoid chop)
- Volume above average (liquidity confirmation)

Exit Logic:
- EMA 9 crosses below EMA 21 (bearish reversal)
- Note: RSI-based exits disabled due to false signals

Risk Management:
- Hard stoploss: -2%
- Trailing stop: 0.5% distance, activates after 1% profit
- ROI target: 1%
"""

from functools import reduce
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import (
    DecimalParameter,
    IStrategy,
    IntParameter,
)
import freqtrade.vendor.qtpylib.indicators as qtpylib


class BTCMomentumScalper(IStrategy):
    """
    Momentum-based BTC scalping strategy using EMA crossover and RSI confirmation.
    Optimized for 5-minute timeframe with tight risk management.
    """

    INTERFACE_VERSION = 3

    timeframe = "5m"

    # ROI table - quick profit-taking for scalping
    minimal_roi = {
        "0": 0.01,    # 1% profit target
        "30": 0.005,  # 0.5% after 30 minutes
        "60": 0.0,    # Break-even after 60 minutes
    }

    # Stoploss configuration
    stoploss = -0.02  # -2% hard stoploss

    # Trailing stop configuration
    trailing_stop = True
    trailing_stop_positive = 0.005  # 0.5% trailing distance
    trailing_stop_positive_offset = 0.01  # Activate after 1% profit
    trailing_only_offset_is_reached = True

    # Strategy behavior settings
    process_only_new_candles = True
    use_exit_signal = False  # Rely on ROI/stoploss for exits - EMA exit too aggressive
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles needed before producing valid signals
    startup_candle_count: int = 30

    # Hyperopt parameters - Entry
    buy_ema_short = IntParameter(5, 15, default=9, space="buy", optimize=True)
    buy_ema_long = IntParameter(15, 30, default=21, space="buy", optimize=True)
    buy_rsi_max = IntParameter(60, 80, default=70, space="buy", optimize=True)
    buy_volume_factor = DecimalParameter(
        0.5, 2.0, default=1.0, decimals=1, space="buy", optimize=True
    )

    # Hyperopt parameters - Exit
    sell_rsi_max = IntParameter(70, 90, default=80, space="sell", optimize=True)

    # Order settings
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {
        "entry": "GTC",
        "exit": "GTC",
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Generate all indicators used by the strategy.
        Calculates indicator ranges for hyperopt optimization.
        """
        # RSI - fast period for scalping entry timing
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=3)

        # RSI - slower period for trend confirmation
        dataframe["rsi_14"] = ta.RSI(dataframe, timeperiod=14)

        # ADX - trend strength filter to avoid choppy markets
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        # Calculate all EMA short values for hyperopt
        for val in self.buy_ema_short.range:
            dataframe[f"ema_short_{val}"] = ta.EMA(dataframe, timeperiod=val)

        # Calculate all EMA long values for hyperopt
        for val in self.buy_ema_long.range:
            dataframe[f"ema_long_{val}"] = ta.EMA(dataframe, timeperiod=val)

        # Volume moving average for liquidity filter
        dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define entry conditions based on EMA crossover with multiple confirmations.

        Entry when:
        1. EMA short crosses above EMA long (bullish momentum trigger)
        2. RSI(3) is below threshold (not overbought on fast RSI)
        3. RSI(14) > 40 (confirming upward momentum)
        4. ADX > 20 (trending market, avoid choppy conditions)
        5. Volume is above average (liquidity confirmation)
        """
        conditions = []

        # EMA crossover - short EMA crosses above long EMA
        ema_short_col = f"ema_short_{self.buy_ema_short.value}"
        ema_long_col = f"ema_long_{self.buy_ema_long.value}"

        conditions.append(
            qtpylib.crossed_above(dataframe[ema_short_col], dataframe[ema_long_col])
        )

        # RSI momentum - not overbought on fast RSI
        conditions.append(dataframe["rsi"] < self.buy_rsi_max.value)

        # RSI(14) confirmation - must show bullish momentum (not oversold bearish)
        conditions.append(dataframe["rsi_14"] > 40)

        # ADX trend filter - only enter in trending markets
        conditions.append(dataframe["adx"] > 20)

        # Volume filter - above average volume
        conditions.append(
            dataframe["volume"] > (dataframe["volume_mean"] * self.buy_volume_factor.value)
        )

        # Basic volume check (non-zero)
        conditions.append(dataframe["volume"] > 0)

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define exit conditions based on EMA crossover reversal only.

        Exit when:
        1. EMA short crosses below EMA long (bearish reversal)

        Note: RSI-based exits are too aggressive with RSI(3), which causes
        premature exits. Instead, rely on ROI and trailing stop for profit-taking.
        """
        conditions = []

        ema_short_col = f"ema_short_{self.buy_ema_short.value}"
        ema_long_col = f"ema_long_{self.buy_ema_long.value}"

        # EMA bearish crossover only (RSI exits were too aggressive)
        conditions.append(
            qtpylib.crossed_below(dataframe[ema_short_col], dataframe[ema_long_col])
        )

        # Basic volume check
        conditions.append(dataframe["volume"] > 0)

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), "exit_long"] = 1

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
        """
        Return 1x leverage for spot trading (no leverage).
        """
        return 1.0
