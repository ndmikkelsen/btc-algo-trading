"""HFT Configuration for Avellaneda-Stoikov Strategy.

Optimized for:
- $1,000 starting capital
- 4% risk per trade
- 2:1 Risk:Reward ratio
- High-frequency trading (5m timeframe)
"""

# =============================================================================
# Capital & Risk Parameters
# =============================================================================

INITIAL_CAPITAL = 1000.0  # Starting capital in USDT

RISK_PER_TRADE = 0.04  # 4% risk per trade

RISK_REWARD_RATIO = 2.0  # 2:1 R:R

MAX_POSITION_PCT = 0.50  # Max 50% of capital in single position

# =============================================================================
# A-S Model Parameters (Tuned for HFT)
# =============================================================================

# Risk aversion - higher for HFT to manage inventory aggressively
RISK_AVERSION = 0.3

# Order book liquidity - higher for tighter spreads in HFT
ORDER_BOOK_LIQUIDITY = 3.0

# Volatility window - shorter for HFT responsiveness
VOLATILITY_WINDOW = 20

# =============================================================================
# Spread Parameters (Tighter for HFT)
# =============================================================================

# Minimum spread (tighter for HFT)
MIN_SPREAD = 0.0003  # 0.03%

# Maximum spread
MAX_SPREAD = 0.02  # 2%

# =============================================================================
# Position Sizing
# =============================================================================

# Stop loss distance (% from entry)
STOP_LOSS_PCT = 0.005  # 0.5%

# Take profit = STOP_LOSS_PCT * RISK_REWARD_RATIO = 1.0%

# =============================================================================
# Session & Timing
# =============================================================================

# Session length for time decay (shorter for HFT)
SESSION_LENGTH = 14400  # 4 hours in seconds

# Quote refresh - how often to update quotes
QUOTE_REFRESH_INTERVAL = 1.0  # Every candle

# =============================================================================
# Fees (Bybit Spot)
# =============================================================================

MAKER_FEE = 0.001  # 0.1%
TAKER_FEE = 0.001  # 0.1%

# =============================================================================
# Regime Detection
# =============================================================================

USE_REGIME_FILTER = True
ADX_TREND_THRESHOLD = 25
ADX_PERIOD = 14
TREND_POSITION_SCALE = 0.3  # Reduce to 30% in trends

# =============================================================================
# Calculated Values
# =============================================================================

def get_risk_amount(equity: float = INITIAL_CAPITAL) -> float:
    """Get dollar risk per trade."""
    return equity * RISK_PER_TRADE

def get_take_profit_pct() -> float:
    """Get take profit distance."""
    return STOP_LOSS_PCT * RISK_REWARD_RATIO

# Example with $1000 capital, BTC at $80,000:
# - Risk per trade: $40
# - Stop loss: 0.5% = $400 per BTC
# - Position size: $40 / $400 = 0.1 BTC (limited by max position)
# - Max position: $500 / $80000 = 0.00625 BTC
# - Take profit: 1.0% = $800 per BTC
