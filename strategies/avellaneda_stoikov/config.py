"""Configuration parameters for Avellaneda-Stoikov Market Making Model.

Reference: "High-frequency trading in a limit order book" (Avellaneda & Stoikov, 2008)
"""

# =============================================================================
# Risk Parameters
# =============================================================================

# Risk aversion parameter (γ - gamma)
# Higher = more aggressive inventory management, tighter quotes when holding inventory
# Lower = more tolerant of inventory, wider quotes
# Typical range: 0.01 - 1.0
RISK_AVERSION = 0.1

# Maximum inventory (absolute value)
# Position limit to prevent excessive exposure
MAX_INVENTORY = 10

# =============================================================================
# Volatility Estimation
# =============================================================================

# Window size for volatility calculation (number of periods)
VOLATILITY_WINDOW = 50

# Volatility estimation method: 'standard', 'parkinson', 'garman_klass'
VOLATILITY_METHOD = 'standard'

# =============================================================================
# Order Book Parameters
# =============================================================================

# Order book liquidity parameter (κ - kappa)
# Higher = denser order book, smaller spreads needed
# Lower = sparser order book, wider spreads allowed
# Typical range: 1.0 - 10.0
ORDER_BOOK_LIQUIDITY = 1.5

# =============================================================================
# Time Parameters
# =============================================================================

# Trading session length in seconds (T)
# For crypto 24/7 markets, this represents the "horizon" for inventory management
# 86400 = 1 day, 3600 = 1 hour
SESSION_LENGTH = 86400

# =============================================================================
# Quote Parameters
# =============================================================================

# Minimum spread (as decimal, e.g., 0.001 = 0.1%)
# Floor to prevent quotes that are too tight
MIN_SPREAD = 0.0005

# Maximum spread (as decimal, e.g., 0.05 = 5%)
# Ceiling to prevent quotes that are too wide
MAX_SPREAD = 0.05

# Order size (in base currency units)
ORDER_SIZE = 0.001  # 0.001 BTC

# =============================================================================
# Execution Parameters
# =============================================================================

# How often to update quotes (in seconds)
QUOTE_REFRESH_INTERVAL = 1.0

# Cancel orders if price moves more than this (as decimal)
PRICE_TOLERANCE = 0.002

# =============================================================================
# Fee Parameters (Bybit Spot)
# =============================================================================

# Maker fee (limit orders that add liquidity)
MAKER_FEE = 0.001  # 0.1%

# Taker fee (market orders that remove liquidity)
TAKER_FEE = 0.001  # 0.1%

# =============================================================================
# Regime Detection Parameters
# =============================================================================

# ADX threshold for trending market
# Above this = trending, below = ranging
ADX_TREND_THRESHOLD = 25

# ADX calculation period
ADX_PERIOD = 14

# Reduce position size in trending markets by this factor
TREND_POSITION_SCALE = 0.5

# =============================================================================
# Realistic Fill Model Parameters
# =============================================================================

# Fill aggressiveness: controls fill probability based on price penetration
# P(fill) = min(1.0, penetration_pct * FILL_AGGRESSIVENESS)
# Higher = more fills (less conservative)
FILL_AGGRESSIVENESS = 10.0

# Maximum slippage as a percentage of price
# Actual slippage is uniform random between 0 and max_slippage * price
MAX_SLIPPAGE_PCT = 0.0001  # 0.01%

# =============================================================================
# Stop-Loss Parameters
# =============================================================================

# Stop-loss percentage: force-close if unrealized loss exceeds this
STOP_LOSS_PCT = 0.005  # 0.5%
