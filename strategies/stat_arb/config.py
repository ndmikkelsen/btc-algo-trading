"""Configuration parameters for Statistical Arbitrage Strategy.

References:
- Gatev, Goetzmann, Rouwenhorst (2006) "Pairs Trading: Performance of a Relative-Value Arbitrage Rule"
- Vidyamurthy (2004) "Pairs Trading: Quantitative Methods and Analysis"
"""

# =============================================================================
# Pair Selection Parameters
# =============================================================================

# Minimum correlation coefficient for pair selection
# Pairs must be historically correlated above this threshold
MIN_CORRELATION = 0.7

# Lookback period for correlation calculation (candles)
CORRELATION_WINDOW = 500

# Cointegration p-value threshold (Engle-Granger test)
# Lower = stricter cointegration requirement
COINTEGRATION_PVALUE = 0.05

# Default trading pairs for cross-pair arbitrage
# BTC correlated assets on Bybit
DEFAULT_PAIRS = [
    ("BTC/USDT", "ETH/USDT"),
    ("BTC/USDT", "SOL/USDT"),
    ("ETH/USDT", "SOL/USDT"),
]

# =============================================================================
# Signal Parameters
# =============================================================================

# Z-score entry threshold (standard deviations from mean)
ENTRY_ZSCORE = 2.0

# Z-score exit threshold (mean reversion target)
EXIT_ZSCORE = 0.0

# Z-score stop loss threshold (spread divergence)
STOP_ZSCORE = 3.5

# Spread calculation window (candles)
SPREAD_WINDOW = 100

# Half-life of mean reversion (max acceptable, in candles)
# If spread half-life exceeds this, pair is not suitable
MAX_HALF_LIFE = 50

# =============================================================================
# Risk Parameters
# =============================================================================

# Risk per trade as decimal (0.02 = 2%)
RISK_PER_TRADE = 0.02

# Maximum simultaneous pair positions
MAX_PAIRS = 3

# Maximum exposure per pair as % of equity
MAX_PAIR_EXPOSURE = 0.15

# =============================================================================
# Execution Parameters
# =============================================================================

# Candle timeframe for analysis
TIMEFRAME = "5m"

# Rebalance interval (candles)
REBALANCE_INTERVAL = 1

# Slippage allowance as decimal
SLIPPAGE_TOLERANCE = 0.001

# =============================================================================
# Fee Parameters (Bybit Spot)
# =============================================================================

MAKER_FEE = 0.001
TAKER_FEE = 0.001
