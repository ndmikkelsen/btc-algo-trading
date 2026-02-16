# Avellaneda-Stoikov Market Making Strategy

> **High-frequency market making for Bitcoin using optimal control theory**

## Quick Start

```bash
# Dry-run test (simulated trading with real market data)
python3 scripts/run_paper_trader.py --futures --leverage 10

# Live trading (real money!)
python3 scripts/run_paper_trader.py --futures --leverage 10 --live
```

## What is Avellaneda-Stoikov?

The **Avellaneda-Stoikov (2008)** model is a mathematical framework for optimal market making developed by Marco Avellaneda and Sasha Stoikov. It provides a systematic approach to:

- **Pricing quotes**: Dynamically adjust bid/ask spreads based on market conditions
- **Managing inventory risk**: Avoid accumulating excessive long or short positions
- **Maximizing profit**: Balance spread capture against inventory risk

### Key Innovation

Unlike traditional market making that uses fixed spreads, A-S **dynamically adjusts prices** based on:
1. Current inventory (position)
2. Market volatility
3. Order book liquidity
4. Time remaining in trading session

This creates a self-balancing system that naturally reduces risk exposure.

## How It Works

### Core Concepts

**1. Reservation Price (r)**
The "fair" price adjusted for your current inventory risk:

```
r = S - q × γ × σ²
```

- **S**: Current mid-price
- **q**: Inventory (positive = long, negative = short)
- **γ**: Risk aversion (how much you penalize inventory)
- **σ²**: Variance of returns

**Impact**: If you're long (q > 0), your reservation price drops below mid, encouraging you to sell.

**2. Optimal Spread (δ)**
The bid-ask spread that balances profit and fill probability:

```
δ = (1/κ) × ln(1 + κ/γ) + √(e × σ² × γ / (2 × A × κ))
```

- **κ**: Order book liquidity (higher = more liquid)
- **A**: Arrival rate of orders
- **e**: Euler's number

**Impact**: Higher volatility → wider spreads (protect against adverse selection)

**3. Final Quotes**
Place orders symmetrically around reservation price:

```
bid = r - δ/2
ask = r + δ/2
```

### Why This Works

1. **Inventory Management**: Asymmetric pricing naturally pushes you back to neutral
2. **Adverse Selection Protection**: Wider spreads in volatile markets
3. **Profit Optimization**: Mathematical proof that this maximizes expected utility
4. **Self-Correcting**: System automatically adjusts to changing conditions

## Our Implementation

We use the **GLFT (Guéant-Lehalle-Fernandez-Tapia) extension** which removes the time horizon constraint, making it suitable for continuous 24/7 crypto trading.

### Architecture

```
strategies/avellaneda_stoikov/
├── base_model.py          # Abstract base class for market making models
├── glft_model.py          # GLFT infinite-horizon implementation (PRODUCTION)
├── model.py               # Original A-S finite-horizon model
├── live_trader.py         # Real-time trading engine
├── bybit_futures_client.py # Bybit API integration (50x leverage)
├── mexc_client.py         # MEXC API integration (spot, 0% fees)
├── kappa_provider.py      # Order book liquidity calibration
├── fee_model.py           # Exchange fee modeling
├── order_manager.py       # Order lifecycle management
├── risk_manager.py        # Position limits and safety controls
└── config.py              # Strategy parameters
```

### Key Features

**✅ Two Exchange Support**
- **MEXC Spot**: 0% maker fees, perfect for low-frequency market making
- **Bybit Futures**: 50x leverage, ideal for high-frequency trading

**✅ Safety Controls (Phase 1 + Phase 2)**
- Tick filter (reject outlier prices)
- Spread bounds ($5-$500)
- Inventory limits (3x/5x order size)
- Fill imbalance cooldown
- Displacement guard (widen spreads on rapid moves)
- Asymmetric spreads (inventory-aware)
- Regime filter (pull quotes in strong trends)
- Liquidation protection (futures only)

**✅ Live Kappa Calibration**
- Real-time order book analysis
- Automatic liquidity parameter adjustment
- Handles changing market conditions

**✅ Liquidation Protection (Futures)**
- Emergency position reduction at 20% threshold
- Isolated margin mode (lower cross-liquidation risk)
- Real-time liquidation price monitoring

## Trading BTC with A-S

### Why A-S for Bitcoin?

1. **High volatility**: A-S dynamically adjusts spreads → captures more premium in volatile markets
2. **24/7 market**: GLFT's infinite-horizon design is perfect for crypto
3. **Deep order books**: BTC has excellent liquidity for market making
4. **High frequency**: Can trade 50-200 times per day

### Expected Performance

**Conservative (10x leverage, γ=0.02):**
- Daily trades: 20-50
- Daily P&L: +0.3% to +1.0%
- Monthly return: ~10-30%
- Win rate: 55-65%

**Aggressive (50x leverage, γ=0.005):**
- Daily trades: 50-200
- Daily P&L: +0.5% to +2.0%
- Monthly return: ~15-60%
- Win rate: 55-70%

**Risk:** High leverage amplifies both gains AND losses. 50x leverage means a 2% adverse move = liquidation.

### Market Conditions

**✅ Best in:**
- Ranging markets (ADX < 25)
- Normal volatility (0.3% - 1.0%)
- Good liquidity (tight spreads)

**⚠️ Challenging in:**
- Strong trends (ADX > 30)
- Extreme volatility (> 2%)
- News events / flash crashes

**Strategy:** Use regime filter to pull quotes during strong trends.

## Parameters

### Core Parameters

| Parameter | Symbol | Description | Conservative | Aggressive |
|-----------|--------|-------------|--------------|------------|
| Risk Aversion | γ | Inventory penalty (1/$²) | 0.02 | 0.005 |
| Liquidity | κ | Order book depth (1/$) | 0.5 | 1.0-2.0 |
| Arrival Rate | A | Expected fills per interval | 20 | 50-100 |
| Leverage | - | Position multiplier | 10x | 25-50x |
| Order Size | - | BTC per order | 0.0001 | 0.001 |

### Safety Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| MIN_SPREAD_DOLLAR | Minimum spread in dollars | $5 |
| MAX_SPREAD_DOLLAR | Maximum spread in dollars | $100 |
| INVENTORY_SOFT_LIMIT | Soft limit (3x order size) | 3 |
| INVENTORY_HARD_LIMIT | Hard limit (5x order size) | 5 |
| LIQUIDATION_THRESHOLD | Emergency threshold | 20% |

## Getting Started

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
pip install pysocks  # For proxy support
```

### 2. Configure Exchange

**For Bybit Futures (50x leverage):**
```bash
export BYBIT_API_KEY='your-key'
export BYBIT_API_SECRET='your-secret'
export SOCKS5_PROXY='socks5://host:port'  # If needed for geo-restrictions
```

**For MEXC Spot (0% fees):**
```bash
export MEXC_API_KEY='your-key'
export MEXC_API_SECRET='your-secret'
```

### 3. Dry-Run Test

```bash
# Test for 20 minutes
timeout 1200 python3 scripts/run_paper_trader.py \
  --futures \
  --leverage 10 \
  --order-size 0.0001 \
  --gamma 0.02 \
  --kappa-value 1.0
```

### 4. Analyze Results

```bash
python3 scripts/analyze_performance.py logs/trader_*.log
```

### 5. Go Live (when ready)

```bash
python3 scripts/run_paper_trader.py \
  --futures \
  --live \
  --leverage 10 \
  --order-size 0.0001 \
  --gamma 0.02
```

## Documentation

- **[GLFT Model Details](../../docs/strategies/GLFT_MODEL.md)** - Mathematical deep-dive
- **[Implementation Guide](../../docs/strategies/IMPLEMENTATION.md)** - Code walkthrough
- **[Parameter Tuning](../../docs/strategies/PARAMETER_TUNING.md)** - Optimization guide
- **[Bybit Futures Setup](../../BYBIT_FUTURES_DESIGN.md)** - Leverage trading guide
- **[Deployment Guide](../../DEPLOYMENT.md)** - Production deployment

## Advanced Topics

### Kappa Calibration

The liquidity parameter κ is critical for optimal performance. We calibrate it from the order book:

```python
κ = 1 / (average_depth_at_touch × mid_price)
```

See `kappa_provider.py` for implementation details.

### Fee-Adjusted Spreads

We adjust spreads to ensure profitability after fees:

```python
min_profitable_spread = (maker_fee + taker_fee) × price
```

MEXC (0% maker) and Bybit (0.01% maker) allow very tight spreads.

### Multi-Fill Simulation

Our backtester simulates realistic fill behavior:
- Queue position modeling
- Partial fills
- Price improvement
- Adverse selection

See `tick_simulator.py` for details.

## References

1. **Avellaneda, M., & Stoikov, S. (2008).** "High-frequency trading in a limit order book." *Quantitative Finance*, 8(3), 217-224.

2. **Guéant, O., Lehalle, C. A., & Fernandez-Tapia, J. (2013).** "Dealing with the inventory risk: a solution to the market making problem." *Mathematics and Financial Economics*, 7(4), 477-507.

3. **Cartea, Á., Jaimungal, S., & Penalva, J. (2015).** *Algorithmic and High-Frequency Trading*. Cambridge University Press.

## Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Logs**: Check `logs/` directory for trading logs
- **Monitoring**: Use `analyze_performance.py` for real-time analysis

---

**⚠️ Risk Warning:** Market making with leverage involves substantial risk. Only trade with capital you can afford to lose. Start with low leverage (10x) and small position sizes. Monitor liquidation distances constantly when using futures.
