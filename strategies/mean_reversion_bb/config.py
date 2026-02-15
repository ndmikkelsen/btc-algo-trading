"""Configuration parameters for Mean Reversion Bollinger Band Strategy.

References:
- Bollinger (2002) "Bollinger on Bollinger Bands"
- Chan (2013) "Algorithmic Trading: Winning Strategies and Their Rationale"
"""

# =============================================================================
# Bollinger Band Parameters
# =============================================================================

# Moving average period for center band
BB_PERIOD = 20

# Number of standard deviations for upper/lower bands
BB_STD_DEV = 2.0

# Secondary (inner) bands for entry refinement
BB_INNER_STD_DEV = 1.0

# Moving average type: 'sma', 'ema', 'wma'
MA_TYPE = "sma"

# =============================================================================
# VWAP Parameters
# =============================================================================

# VWAP calculation period (candles)
VWAP_PERIOD = 50

# VWAP deviation threshold for confirmation
# Price must be within this % of VWAP to confirm mean reversion
VWAP_CONFIRMATION_PCT = 0.02

# =============================================================================
# Squeeze Detection Parameters
# =============================================================================

# Keltner Channel period (for squeeze detection)
KC_PERIOD = 20

# Keltner Channel ATR multiplier
KC_ATR_MULTIPLIER = 1.5

# Minimum squeeze duration (candles) before breakout entry
MIN_SQUEEZE_DURATION = 6

# =============================================================================
# Signal Parameters
# =============================================================================

# Entry: price touches outer band and RSI confirms
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# Mean reversion target (% of distance to center band)
REVERSION_TARGET = 0.8  # 80% reversion to mean

# Maximum bars to hold position
MAX_HOLDING_BARS = 50

# =============================================================================
# Risk Parameters
# =============================================================================

# Risk per trade as decimal
RISK_PER_TRADE = 0.02

# Maximum position as % of equity
MAX_POSITION_PCT = 0.25

# Stop loss: distance beyond band (ATR multiplier)
STOP_ATR_MULTIPLIER = 1.5

# =============================================================================
# Execution Parameters
# =============================================================================

TIMEFRAME = "5m"
QUOTE_REFRESH_INTERVAL = 5.0

# =============================================================================
# Fee Parameters (Bybit Futures)
# =============================================================================

MAKER_FEE = 0.0001   # 0.01% maker
TAKER_FEE = 0.0006   # 0.06% taker
