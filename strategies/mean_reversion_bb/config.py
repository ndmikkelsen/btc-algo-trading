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
# Optimized: 2.5σ reduces false signals in crypto's fat-tailed distributions
BB_STD_DEV = 2.5

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
# Regime Filter Parameters
# =============================================================================

# ADX period for trend strength measurement
ADX_PERIOD = 14

# ADX threshold: below this = ranging (favorable for MR)
# Optimized: 22 balances signal frequency with quality (was 25 standard)
ADX_THRESHOLD = 22.0

# Enable/disable regime filter (for A/B testing)
USE_REGIME_FILTER = True

# =============================================================================
# Signal Parameters
# =============================================================================

# Entry: price touches outer band and RSI confirms
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# Mean reversion target (% of distance to center band)
# Optimized: 90% captures more profit per trade (was 80%)
REVERSION_TARGET = 0.9

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
# Optimized: wider stops for MR (was 1.5x; literature warns tight stops hurt MR)
STOP_ATR_MULTIPLIER = 2.5

# =============================================================================
# Configurable Toggles
# =============================================================================

# Side filter: "both", "long_only", "short_only"
SIDE_FILTER = "both"

# Enable/disable squeeze filter (when False, entries allowed during squeeze)
USE_SQUEEZE_FILTER = True

# Enable/disable band walking exit (when False, band walking never triggers exit)
USE_BAND_WALKING_EXIT = True

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
