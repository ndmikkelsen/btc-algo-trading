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

# Risk Management (2:1 R:R minimum, 5% capital risk per trade)
STOPLOSS = -0.05  # 5% stop loss (wider room for mean reversion)
TAKE_PROFIT = 0.10  # 10% take profit (2:1 R:R with 5% stop)
TRAILING_STOP = True
TRAILING_STOP_POSITIVE = 0.03  # 3% trailing distance
TRAILING_STOP_POSITIVE_OFFSET = 0.10  # Activate trailing at 10% profit (2:1 R:R reached)
