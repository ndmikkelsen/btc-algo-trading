"""Configuration parameters for Adaptive Momentum Strategy.

References:
- Jegadeesh & Titman (1993) "Returns to Buying Winners and Selling Losers"
- Moskowitz, Ooi, Pedersen (2012) "Time Series Momentum"
- Baltas & Kosowski (2013) "Momentum Strategies in Futures Markets and Trend-Following Funds"
"""

# =============================================================================
# Momentum Calculation Parameters
# =============================================================================

# Fast momentum lookback (candles)
FAST_MOMENTUM_PERIOD = 12

# Slow momentum lookback (candles)
SLOW_MOMENTUM_PERIOD = 26

# Signal smoothing period (candles)
SIGNAL_PERIOD = 9

# RSI period
RSI_PERIOD = 14

# RSI overbought/oversold thresholds
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# =============================================================================
# Adaptive Parameters
# =============================================================================

# Regime detection: ADX period and threshold
ADX_PERIOD = 14
ADX_TREND_THRESHOLD = 25

# Volatility scaling window (candles)
VOLATILITY_WINDOW = 20

# Target annualized volatility for position sizing
TARGET_VOLATILITY = 0.15  # 15%

# Momentum decay factor (exponential weighting)
# Higher = more weight on recent momentum
MOMENTUM_DECAY = 0.94

# Minimum momentum strength to enter (absolute value)
MIN_MOMENTUM_STRENGTH = 0.5

# =============================================================================
# Multi-Timeframe Parameters
# =============================================================================

# Timeframes for multi-timeframe confirmation
TIMEFRAMES = ["5m", "15m", "1h"]

# Weight for each timeframe in signal aggregation
TIMEFRAME_WEIGHTS = {
    "5m": 0.2,
    "15m": 0.3,
    "1h": 0.5,
}

# Minimum agreement across timeframes (0.0 to 1.0)
MIN_TIMEFRAME_AGREEMENT = 0.6

# =============================================================================
# Risk Parameters
# =============================================================================

# Risk per trade as decimal
RISK_PER_TRADE = 0.03

# Maximum position as % of equity
MAX_POSITION_PCT = 0.3

# Trailing stop activation (% profit)
TRAILING_STOP_ACTIVATION = 0.02  # 2%

# Trailing stop distance (% from peak)
TRAILING_STOP_DISTANCE = 0.01  # 1%

# Maximum holding period (candles) - momentum decay
MAX_HOLDING_PERIOD = 200

# =============================================================================
# Execution Parameters
# =============================================================================

TIMEFRAME = "5m"
QUOTE_REFRESH_INTERVAL = 5.0

# =============================================================================
# Fee Parameters (Bybit Spot)
# =============================================================================

MAKER_FEE = 0.001
TAKER_FEE = 0.001
