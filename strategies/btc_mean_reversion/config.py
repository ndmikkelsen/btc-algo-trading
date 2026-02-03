"""
Configuration for BTCMeanReversion strategy.

Mean reversion strategy that buys oversold conditions and sells overbought.
Uses Bollinger Bands and RSI to identify extremes.
"""

# Strategy timeframe
TIMEFRAME = "5m"

# Number of candles needed before producing valid signals
STARTUP_CANDLE_COUNT = 50

# ROI table - take profits as price reverts to mean
MINIMAL_ROI = {
    "0": 0.03,    # 3% immediate target
    "30": 0.02,   # 2% after 30 minutes
    "60": 0.01,   # 1% after 60 minutes
    "120": 0.005, # 0.5% after 2 hours
    "240": 0.0,   # Break-even after 4 hours
}

# Stoploss - tighter for mean reversion (trends are the enemy)
STOPLOSS = -0.03  # -3% hard stoploss

# Trailing stop configuration
TRAILING_STOP = True
TRAILING_STOP_POSITIVE = 0.01  # 1% trailing distance
TRAILING_STOP_POSITIVE_OFFSET = 0.015  # Activate after 1.5% profit
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
USE_EXIT_SIGNAL = True  # Use exit signals for mean reversion
EXIT_PROFIT_ONLY = False
IGNORE_ROI_IF_ENTRY_SIGNAL = False
