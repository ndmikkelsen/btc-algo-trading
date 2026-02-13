"""Configuration parameters for VWAP/TWAP Execution Strategy.

References:
- Berkowitz, Logue, Noser (1988) "The Total Cost of Transactions on the NYSE"
- Almgren & Chriss (2001) "Optimal Execution of Portfolio Transactions"
- Kissell & Glantz (2003) "Optimal Trading Strategies"
"""

# =============================================================================
# VWAP Parameters
# =============================================================================

# VWAP calculation period (candles)
VWAP_LOOKBACK = 50

# Volume profile bins for intraday volume prediction
VOLUME_PROFILE_BINS = 24  # Hourly bins for 24h cycle

# Volume profile lookback (days) for pattern estimation
VOLUME_PROFILE_DAYS = 7

# Maximum deviation from VWAP to accept fill (%)
MAX_VWAP_DEVIATION = 0.002  # 0.2%

# =============================================================================
# TWAP Parameters
# =============================================================================

# Number of time slices for TWAP execution
TWAP_SLICES = 20

# Randomization factor for slice timing (0.0 = uniform, 1.0 = fully random)
TWAP_RANDOMIZATION = 0.3

# Minimum time between slices (seconds)
MIN_SLICE_INTERVAL = 30

# Maximum time between slices (seconds)
MAX_SLICE_INTERVAL = 300

# =============================================================================
# Execution Algorithm Selection
# =============================================================================

# Algorithm: 'vwap', 'twap', 'adaptive'
# adaptive switches between VWAP and TWAP based on conditions
DEFAULT_ALGORITHM = "adaptive"

# Minimum order size to trigger algorithmic execution (USDT value)
# Below this, use simple market/limit order
MIN_ALGO_ORDER_SIZE = 500.0

# =============================================================================
# Participation Rate Parameters
# =============================================================================

# Maximum participation rate (% of market volume)
MAX_PARTICIPATION_RATE = 0.05  # 5% of volume

# Target participation rate
TARGET_PARTICIPATION_RATE = 0.02  # 2% of volume

# Volume estimation window (candles)
VOLUME_ESTIMATION_WINDOW = 20

# =============================================================================
# Price Impact Model
# =============================================================================

# Temporary impact coefficient (bps per 1% of ADV)
TEMPORARY_IMPACT_COEFF = 5.0

# Permanent impact coefficient (bps per 1% of ADV)
PERMANENT_IMPACT_COEFF = 2.0

# Impact decay half-life (candles)
IMPACT_DECAY_HALFLIFE = 10

# =============================================================================
# Risk Parameters
# =============================================================================

# Maximum execution time (candles)
MAX_EXECUTION_TIME = 100

# Price limit: cancel if price moves more than this %
PRICE_LIMIT_PCT = 0.01  # 1%

# Urgency parameter (0.0 = patient, 1.0 = aggressive)
DEFAULT_URGENCY = 0.5

# =============================================================================
# Execution Parameters
# =============================================================================

TIMEFRAME = "1m"
QUOTE_REFRESH_INTERVAL = 1.0

# =============================================================================
# Fee Parameters (Bybit Spot)
# =============================================================================

MAKER_FEE = 0.001
TAKER_FEE = 0.001
