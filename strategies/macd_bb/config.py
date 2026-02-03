"""Configuration parameters for MACD + Bollinger Bands strategy."""

# MACD Settings
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger Bands Settings
BB_PERIOD = 20
BB_STD = 2.0

# Risk Management
STOPLOSS = -0.03  # 3% stop loss
TAKE_PROFIT = 0.02  # 2% take profit
TRAILING_STOP = True
TRAILING_STOP_POSITIVE = 0.01  # 1% trailing
TRAILING_STOP_POSITIVE_OFFSET = 0.015  # Activate trailing at 1.5% profit
