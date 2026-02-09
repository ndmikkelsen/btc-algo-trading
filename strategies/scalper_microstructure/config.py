"""Configuration parameters for Scalper / Microstructure Strategy.

References:
- Kyle (1985) "Continuous Auctions and Insider Trading"
- Glosten & Milgrom (1985) "Bid, Ask and Transaction Prices"
- Cartea, Jaimungal, Penalva (2015) "Algorithmic and High-Frequency Trading"
"""

# =============================================================================
# Order Flow Analysis Parameters
# =============================================================================

# Order flow imbalance window (ticks/candles)
OFI_WINDOW = 20

# Order flow imbalance threshold for signal
# Positive = buy pressure, negative = sell pressure
OFI_ENTRY_THRESHOLD = 0.6  # 60% imbalance

# Volume delta calculation period
VOLUME_DELTA_PERIOD = 10

# Cumulative volume delta smoothing
CVD_SMOOTHING = 5

# =============================================================================
# Bid-Ask Spread Analysis
# =============================================================================

# Minimum spread to capture (as decimal)
MIN_CAPTURE_SPREAD = 0.0003  # 3 bps

# Spread percentile threshold (use historical spread distribution)
SPREAD_PERCENTILE_ENTRY = 75  # Enter when spread is above 75th percentile

# Spread calculation window (candles)
SPREAD_WINDOW = 100

# =============================================================================
# Microstructure Signals
# =============================================================================

# Trade arrival rate estimation window (candles)
ARRIVAL_RATE_WINDOW = 50

# Toxicity indicator: VPIN (Volume-synchronized PIN) period
VPIN_PERIOD = 50
VPIN_BUCKET_SIZE = 50  # Volume per bucket

# Toxicity threshold (above this, reduce/pause trading)
VPIN_TOXICITY_THRESHOLD = 0.7

# =============================================================================
# Scalping Parameters
# =============================================================================

# Target profit per trade (as decimal)
TARGET_PROFIT = 0.0005  # 5 bps

# Maximum holding time (seconds)
MAX_HOLDING_TIME = 60  # 1 minute

# Scalp entry: RSI extreme period
RSI_PERIOD = 7  # Short period for scalping
RSI_OVERSOLD = 25
RSI_OVERBOUGHT = 75

# =============================================================================
# Risk Parameters
# =============================================================================

# Risk per trade as decimal
RISK_PER_TRADE = 0.01  # 1% (small due to high frequency)

# Maximum position as % of equity
MAX_POSITION_PCT = 0.1

# Stop loss per trade (as decimal)
STOP_LOSS_PCT = 0.001  # 10 bps tight stop

# Maximum trades per hour (circuit breaker)
MAX_TRADES_PER_HOUR = 60

# Maximum consecutive losses before cooldown
MAX_CONSECUTIVE_LOSSES = 5

# Cooldown period after consecutive losses (seconds)
LOSS_COOLDOWN = 300  # 5 minutes

# =============================================================================
# Execution Parameters
# =============================================================================

TIMEFRAME = "1m"
QUOTE_REFRESH_INTERVAL = 0.5  # Sub-second refresh

# =============================================================================
# Fee Parameters (Bybit Spot)
# =============================================================================

MAKER_FEE = 0.001
TAKER_FEE = 0.001
