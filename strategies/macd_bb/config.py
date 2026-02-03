"""Configuration parameters for MACD + Bollinger Bands strategy."""

# MACD Settings
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger Bands Settings
BB_PERIOD = 20
BB_STD = 2.0

# Signal Generation
BB_NEAR_THRESHOLD = 0.02  # 2% threshold for "near" band detection
BB_LOOKBACK = 5  # Candles to look back for recent BB touch
EXIT_ON_UPPER_BB = False  # Exit when price reaches upper BB (disabled - use trailing stop)

# Trend Filter (avoid catching falling knives)
USE_TREND_FILTER = True  # Enable ADX-based trend filter
ADX_THRESHOLD = 25.0  # Block entries when ADX > this AND in downtrend

# Risk Management
STOPLOSS = -0.03  # 3% stop loss
TAKE_PROFIT = 0.02  # 2% take profit
TRAILING_STOP = True
TRAILING_STOP_POSITIVE = 0.015  # 1.5% trailing distance
TRAILING_STOP_POSITIVE_OFFSET = 0.03  # Activate trailing at 3% profit (let winners run)
