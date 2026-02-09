"""Configuration parameters for Grid Trading Strategy.

References:
- Humphrey (2010) "Grid Trading and the Role of Market Microstructure"
- DeMark (1994) "The New Science of Technical Analysis" (support/resistance levels)
"""

# =============================================================================
# Grid Structure Parameters
# =============================================================================

# Number of grid levels above and below center
GRID_LEVELS = 10

# Grid spacing as decimal (0.005 = 0.5%)
GRID_SPACING = 0.005

# Grid type: 'arithmetic' (fixed spacing) or 'geometric' (% spacing)
GRID_TYPE = "geometric"

# Order size per grid level (base currency)
ORDER_SIZE_PER_LEVEL = 0.001  # 0.001 BTC

# =============================================================================
# Dynamic Grid Parameters
# =============================================================================

# ATR period for dynamic grid spacing
ATR_PERIOD = 14

# ATR multiplier for dynamic spacing
# Grid spacing = ATR * multiplier / price
ATR_SPACING_MULTIPLIER = 0.5

# Recenter grid when price moves beyond this % of grid range
RECENTER_THRESHOLD = 0.7  # 70% of grid range

# Minimum time between recentering (candles)
MIN_RECENTER_INTERVAL = 12

# =============================================================================
# Ranging Market Detection
# =============================================================================

# ADX threshold for ranging market (below = ranging)
ADX_RANGING_THRESHOLD = 20

# Bollinger Band width threshold for low volatility
BB_WIDTH_LOW = 0.02

# Minimum ranging duration (candles) to activate grid
MIN_RANGING_DURATION = 20

# =============================================================================
# Risk Parameters
# =============================================================================

# Maximum total grid exposure as % of equity
MAX_GRID_EXPOSURE = 0.5  # 50%

# Stop loss: if price breaks beyond grid range by this %
GRID_STOP_LOSS_PCT = 0.03  # 3% beyond grid

# Take profit: accumulated profit target before grid reset
GRID_TAKE_PROFIT_PCT = 0.05  # 5%

# Maximum simultaneous open orders
MAX_OPEN_ORDERS = 20

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
