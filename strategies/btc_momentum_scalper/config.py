"""
Configuration for BTCMomentumScalper strategy.

Contains all strategy parameters, ROI tables, stoploss settings,
and hyperopt parameter definitions.
"""

from freqtrade.strategy import DecimalParameter, IntParameter

# Strategy timeframe
TIMEFRAME = "5m"

# Number of candles needed before producing valid signals
STARTUP_CANDLE_COUNT = 30

# ROI table - quick profit-taking for scalping
MINIMAL_ROI = {
    "0": 0.01,    # 1% profit target
    "30": 0.005,  # 0.5% after 30 minutes
    "60": 0.0,    # Break-even after 60 minutes
}

# Stoploss configuration
STOPLOSS = -0.02  # -2% hard stoploss

# Trailing stop configuration
TRAILING_STOP = True
TRAILING_STOP_POSITIVE = 0.005  # 0.5% trailing distance
TRAILING_STOP_POSITIVE_OFFSET = 0.01  # Activate after 1% profit
TRAILING_ONLY_OFFSET_IS_REACHED = True

# Order settings
ORDER_TYPES = {
    "entry": "limit",
    "exit": "limit",
    "stoploss": "market",
    "stoploss_on_exchange": False,
}

ORDER_TIME_IN_FORCE = {
    "entry": "GTC",
    "exit": "GTC",
}

# Strategy behavior settings
PROCESS_ONLY_NEW_CANDLES = True
USE_EXIT_SIGNAL = False  # Rely on ROI/stoploss for exits
EXIT_PROFIT_ONLY = False
IGNORE_ROI_IF_ENTRY_SIGNAL = False


def create_hyperopt_params():
    """
    Create hyperopt parameter definitions.

    Returns dict of parameter name -> parameter object.
    Must be called within strategy class context.
    """
    return {
        "buy_ema_short": IntParameter(5, 15, default=9, space="buy", optimize=True),
        "buy_ema_long": IntParameter(15, 30, default=21, space="buy", optimize=True),
        "buy_rsi_max": IntParameter(60, 80, default=70, space="buy", optimize=True),
        "buy_volume_factor": DecimalParameter(
            0.5, 2.0, default=1.0, decimals=1, space="buy", optimize=True
        ),
        "sell_rsi_max": IntParameter(70, 90, default=80, space="sell", optimize=True),
    }
