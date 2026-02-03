"""Optimized HFT Configuration for Avellaneda-Stoikov Strategy.

Based on parameter optimization results:
- Best performance in RANGING markets
- 11.39% return in March 2025 test period
- Fee efficiency: $8.04 return per $1 fee

KEY INSIGHT: This strategy works best in RANGING markets.
Use regime detection to ONLY trade when ADX < 25.

Optimized for:
- $1,000 starting capital
- 4% risk per trade
- 2:1 Risk:Reward ratio
"""

# =============================================================================
# Capital & Risk Parameters
# =============================================================================

INITIAL_CAPITAL = 1000.0  # Starting capital in USDT

RISK_PER_TRADE = 0.04  # 4% risk per trade

RISK_REWARD_RATIO = 2.0  # 2:1 R:R

MAX_POSITION_PCT = 0.60  # Max 60% of capital in single position

# =============================================================================
# OPTIMIZED A-S Model Parameters
# =============================================================================

# Risk aversion - lower for more trades in ranging markets
RISK_AVERSION = 0.1

# Order book liquidity
ORDER_BOOK_LIQUIDITY = 2.5

# Volatility window
VOLATILITY_WINDOW = 20

# =============================================================================
# OPTIMIZED Spread Parameters
# =============================================================================

# Minimum spread - must be > 0.2% (round-trip fee)
# Optimal found: 0.3% - 0.8% all performed similarly
MIN_SPREAD = 0.004  # 0.4% - provides buffer above fee

# Maximum spread
MAX_SPREAD = 0.03  # 3%

# =============================================================================
# OPTIMIZED Position Sizing
# =============================================================================

# Order size - larger captures more spread per trade
ORDER_SIZE = 0.003  # 0.003 BTC (~$240 at $80k)

# Stop loss distance (% from entry)
STOP_LOSS_PCT = 0.005  # 0.5%

# =============================================================================
# CRITICAL: Regime Filter Settings
# =============================================================================

# ENABLE regime filter - only trade in ranging markets
USE_REGIME_FILTER = True

# ADX threshold - trade ONLY when ADX < this value
ADX_TREND_THRESHOLD = 25  # Standard threshold

# ADX calculation period
ADX_PERIOD = 14

# In trends, reduce to this fraction (or 0 to stop completely)
TREND_POSITION_SCALE = 0.0  # STOP trading in trends

# =============================================================================
# Session & Timing
# =============================================================================

SESSION_LENGTH = 86400  # 24 hours

QUOTE_REFRESH_INTERVAL = 1.0  # Every candle

# =============================================================================
# Fees
# =============================================================================

MAKER_FEE = 0.001  # 0.1%

# Fee efficiency threshold: only trade if expected profit > 2x fees
MIN_PROFIT_MULTIPLIER = 2.0

# =============================================================================
# Calculated Values
# =============================================================================

def is_trade_profitable(spread: float) -> bool:
    """Check if a trade at given spread would be profitable after fees."""
    round_trip_fee = MAKER_FEE * 2  # 0.2%
    min_profitable_spread = round_trip_fee * MIN_PROFIT_MULTIPLIER
    return spread >= min_profitable_spread

def get_optimal_order_size(equity: float, price: float) -> float:
    """Get optimal order size based on equity and risk."""
    max_position_value = equity * MAX_POSITION_PCT
    return min(ORDER_SIZE, max_position_value / price)


# =============================================================================
# Performance Expectations (Based on Backtests)
# =============================================================================
#
# RANGING MARKETS (ADX < 25):
#   - Expected monthly return: 5-15%
#   - Trades per month: 40-60
#   - Win rate: ~55%
#   - Fee impact: ~10-15% of gross profit
#
# TRENDING MARKETS (ADX > 25):
#   - DO NOT TRADE - high inventory risk
#   - Strategy will skip these periods
#
# OVERALL:
#   - Market is ranging ~26% of the time
#   - Expected active trading: ~8 days per month
#   - Compound annual return potential: 30-50% (in favorable conditions)
#
# =============================================================================
