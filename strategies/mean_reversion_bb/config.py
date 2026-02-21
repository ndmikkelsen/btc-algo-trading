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
# 3.0x gives room for initial reversion; decays to 1.0x over trade lifetime
STOP_ATR_MULTIPLIER = 3.0

# Time-decay stop parameters: stops tighten as trade ages
# Phase boundaries as fraction of max_holding_bars
STOP_DECAY_PHASE_1 = 0.33  # First tightening at 33% of max holding bars
STOP_DECAY_PHASE_2 = 0.66  # Second tightening at 66% of max holding bars
# ATR multipliers at each decay phase (decay from STOP_ATR_MULTIPLIER)
STOP_DECAY_MULT_1 = 2.0    # Tighten to 2.0x ATR at phase 1
STOP_DECAY_MULT_2 = 1.0    # Tighten to 1.0x ATR at phase 2

# =============================================================================
# Asymmetric Short Parameters
# =============================================================================
# Separate thresholds for short entries — research shows shorts need stricter
# conditions in crypto (wider bands, higher RSI, shorter hold, smaller size).
# Defaults match long-side values for backward compatibility;
# the bidirectional preset overrides them.

# BB std dev for short entry band (wider = fewer but higher-conviction entries)
SHORT_BB_STD_DEV = BB_STD_DEV  # 2.5 default, bidirectional preset uses 3.0

# RSI threshold for short entry (higher = only extreme overbought)
SHORT_RSI_THRESHOLD = RSI_OVERBOUGHT  # 70 default, bidirectional preset uses 80

# Max holding bars for shorts (shorter = cut losers faster)
SHORT_MAX_HOLDING_BARS = MAX_HOLDING_BARS  # 50 default, bidirectional preset uses 48

# Max position size for shorts as % of equity (smaller = reduced risk)
SHORT_POSITION_PCT = MAX_POSITION_PCT  # 0.25 default, bidirectional preset uses 0.10

# =============================================================================
# Trend Filter Parameters
# =============================================================================

# Enable/disable trend direction gating (shorts only in bearish/neutral)
USE_TREND_FILTER = False  # Disabled by default for backward compatibility

# EMA period for trend detection (50 for 5m candles ≈ ~4h lookback)
TREND_EMA_PERIOD = 50

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
