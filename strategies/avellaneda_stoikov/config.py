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
# Tick Size (MEXC BTCUSDT)
# =============================================================================

# Minimum price increment for the instrument
# All model calculations use tick-normalized units internally
TICK_SIZE = 0.10  # MEXC BTCUSDT tick size in dollars

# =============================================================================
# Time Parameters
# =============================================================================

# Trading session length in seconds (T)
# For crypto 24/7 markets, this represents the "horizon" for inventory management
# 86400 = 1 day, 3600 = 1 hour
SESSION_LENGTH = 86400

# =============================================================================
# Quote Parameters (dollar-based)
# =============================================================================

# Minimum spread in dollars
# Floor to prevent quotes that are too tight (must exceed round-trip fees)
MIN_SPREAD_DOLLAR = 5.0  # $5 minimum spread (~5 bps at $100k BTC)

# Maximum spread in dollars
# Ceiling to prevent quotes that are too wide
MAX_SPREAD_DOLLAR = 100.0  # $100 maximum spread (~10 bps at $100k BTC)

# Legacy percentage-based spreads (used by tests expecting pct interface)
MIN_SPREAD = 0.0005  # 0.05% — will be overridden by dollar-based in model
MAX_SPREAD = 0.05    # 5% — will be overridden by dollar-based in model

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
# Fee Parameters (MEXC Spot — Regular tier)
# =============================================================================

# Maker fee (limit orders that add liquidity)
MAKER_FEE = 0.0  # 0% — MEXC charges zero maker fees

# Taker fee (market orders that remove liquidity)
TAKER_FEE = 0.0005  # 0.05%

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

# =============================================================================
# Safety Controls (Phase 1)
# =============================================================================

# Tick filter: reject ticks deviating > this fraction from EMA
BAD_TICK_THRESHOLD = 0.02  # 2%

# Price displacement: widen spread when price moves > this in lookback window
DISPLACEMENT_THRESHOLD = 0.001  # 0.1% move triggers widening
DISPLACEMENT_LOOKBACK = 6       # ticks (6 × 5s = 30s at default interval)
DISPLACEMENT_AGGRESSION = 2.0   # widening multiplier per threshold unit
DISPLACEMENT_MAX_MULT = 3.0     # max spread multiplier

# Inventory limits (multiples of order_size)
INVENTORY_SOFT_LIMIT = 3   # start reducing order size
INVENTORY_HARD_LIMIT = 5   # stop accumulating, reduce-only

# Post-fill cooldown
FILL_COOLDOWN_SECONDS = 3.0  # seconds to wait after a fill before re-quoting
