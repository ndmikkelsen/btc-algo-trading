# Avellaneda-Stoikov Quick Start Guide

> **Get running with A-S market making in 10 minutes**

## Prerequisites

- Python 3.11+
- Bybit or MEXC account with API keys
- $500-1000 starting capital (recommended)
- Understanding of leverage risks

## Installation

```bash
# Clone repository
git clone <repo-url>
cd btc-algo-trading

# Install dependencies
pip install -r requirements.txt
pip install pysocks  # For proxy support if needed

# Verify installation
python3 -m pytest tests/ -k "test_glft" -v
```

## Configuration

### 1. Set Up API Keys

**For Bybit Futures (50x leverage):**
```bash
export BYBIT_API_KEY='your-api-key'
export BYBIT_API_SECRET='your-api-secret'

# If you need proxy for geo-restrictions
export SOCKS5_PROXY='socks5://host:port'
```

**For MEXC Spot (0% maker fees):**
```bash
export MEXC_API_KEY='your-api-key'
export MEXC_API_SECRET='your-secret'
```

### 2. Configure Strategy Parameters

Edit `strategies/avellaneda_stoikov/config.py`:

```python
# Conservative setup for beginners
USE_FUTURES = True          # True for Bybit, False for MEXC
LEVERAGE = 10               # Start with 10x, scale to 50x later
ORDER_SIZE = 0.0001         # ~$6-10 per trade at $60-100k BTC
INITIAL_CAPITAL = 1000.0    # Starting balance in USDT

# GLFT model parameters (conservative)
RISK_AVERSION = 0.02        # γ in 1/$² (higher = more conservative)
ORDER_BOOK_LIQUIDITY = 1.0  # κ in 1/$ (calibrated from order book)
ARRIVAL_RATE = 50.0         # A (expected fills per hour)

# Safety bounds
MIN_SPREAD_DOLLAR = 5.0     # Minimum spread in dollars
MAX_SPREAD_DOLLAR = 100.0   # Maximum spread in dollars
INVENTORY_SOFT_LIMIT = 3    # Pull quotes at 3x order size
INVENTORY_HARD_LIMIT = 5    # Stop trading at 5x order size
```

## Testing

### Step 1: Dry-Run Test (5 minutes)

Test with simulated trading on real market data:

```bash
timeout 300 python3 scripts/run_paper_trader.py \
  --futures \
  --leverage 10 \
  --order-size 0.0001 \
  --gamma 0.02 \
  --kappa-value 1.0 \
  2>&1 | tee logs/dry_run_5min.log
```

**What to look for:**
- ✅ "Quotes updated" messages every 5 seconds
- ✅ Bid/Ask spreads between $5-$100
- ✅ Safety controls activating (normal behavior)
- ✅ No critical errors
- ✅ Price tracking correctly

### Step 2: Analyze Results

```bash
python3 scripts/analyze_performance.py logs/dry_run_5min.log
```

**Expected output:**
```
=== Performance Analysis ===
Fills: 0-3 (in 5 minutes)
Win Rate: 50-70%
Gross P&L: -$1 to +$3
Safety Activations: 2-8
Errors: 0
```

### Step 3: Extended Dry-Run (20 minutes)

```bash
timeout 1200 python3 scripts/run_paper_trader.py \
  --futures \
  --leverage 10 \
  --order-size 0.0001 \
  --gamma 0.02 \
  --kappa-value 1.0 \
  2>&1 | tee logs/dry_run_20min.log
```

**Expected:**
- Fills: 5-15
- P&L: -$5 to +$15
- Safety activations: 10-30

## Going Live

### Conservative First Live Test

**Start small:**
- Capital: $200-500
- Leverage: 10x (NOT 50x!)
- Order size: 0.0001 BTC
- Duration: 1-2 hours, actively monitored
- Risk: Max loss ~$50-100

```bash
python3 scripts/run_paper_trader.py \
  --futures \
  --live \
  --leverage 10 \
  --order-size 0.0001 \
  --gamma 0.02 \
  --kappa-value 1.0
```

### Monitoring

**Terminal 1: Main process**
```bash
# Your trading script runs here
```

**Terminal 2: Live monitoring**
```bash
tail -f logs/trader_*.log | grep --color=always "Quotes updated\|FILL\|P&L\|ERROR"
```

**Terminal 3: Bybit web interface**
- Monitor open positions
- Check liquidation price
- Verify P&L matches logs

### What to Watch

**🚩 RED FLAGS - Stop immediately:**
- Liquidation distance < 30%
- Consecutive losses > 5
- Critical errors
- Massive slippage (> 1%)
- Position size exceeds limits

**✅ GREEN LIGHTS - Continue:**
- Quotes updating regularly
- Spreads within $5-$100
- Safety controls activating
- Win rate > 50%
- Liquidation distance > 50%

## Troubleshooting

### Issue: "403 Forbidden" API errors

**Solution:** Use SOCKS5 proxy
```bash
export SOCKS5_PROXY="socks5://host:port"
```

### Issue: No fills after 30 minutes

**Possible causes:**
1. Spreads too wide → Lower γ (0.02 → 0.01)
2. Market too volatile → Normal, wait for calmer conditions
3. Order size too large → Reduce to 0.00005 BTC

### Issue: Inventory keeps growing

**Possible causes:**
1. γ too low → Increase to 0.03-0.05
2. Asymmetric spreads disabled → Check config
3. Strong trend → Regime filter should detect this

### Issue: "Rate limit exceeded"

**Solution:** Increase quote interval
```bash
python3 scripts/run_paper_trader.py --interval 10  # 10 seconds instead of 5
```

## Scaling Up

### Week 1: Prove the System
- 10x leverage
- $200-500 capital
- Monitor daily
- **Goal:** Break even or small profit

### Week 2-3: Optimize
- Adjust γ, κ based on observations
- Try 15-20x leverage if profitable
- Increase capital to $1000
- **Goal:** +$20-50/week

### Week 4+: Scale
- 25-50x leverage (if consistently profitable)
- $2000-5000 capital
- Automate monitoring
- **Goal:** +$100-300/week

## Safety Checklist

Before going live, verify:

- [ ] All tests passing (`pytest tests/`)
- [ ] Dry-run successful (20+ minutes)
- [ ] API keys configured
- [ ] Starting capital set
- [ ] Leverage <= 10x for first test
- [ ] Order size appropriate (0.0001 BTC)
- [ ] Liquidation protection enabled
- [ ] Safety controls active
- [ ] Monitoring set up
- [ ] Emergency stop plan ready
- [ ] You understand the risks

## Emergency Procedures

### Stop the Bot

```bash
# Press Ctrl+C, or:
pkill -f "run_paper_trader.py"
```

### Check Position

```bash
# Log into Bybit web interface
# Go to Positions tab
# Manually close if needed
```

### Review What Happened

```bash
python3 scripts/analyze_performance.py logs/trader_*.log
grep -i "error\|liquidation" logs/trader_*.log
```

## Next Steps

Once comfortable with live trading:

1. **Read the theory**: [GLFT_MODEL.md](./GLFT_MODEL.md)
2. **Optimize parameters**: [PARAMETER_TUNING.md](./PARAMETER_TUNING.md)
3. **Deploy to VPS**: [../../DEPLOYMENT.md](../../DEPLOYMENT.md)
4. **Set up monitoring**: Prometheus + Grafana
5. **Backtest variations**: Try different γ, κ, A values

## Support

- **Documentation**: `docs/strategies/`
- **Examples**: `scripts/`
- **Tests**: `tests/unit/avellaneda_stoikov/`
- **Logs**: `logs/`

---

**⚠️ FINAL WARNING**: Market making with leverage is high-risk. You can lose your entire capital. Only trade with money you can afford to lose. Start small, monitor closely, scale gradually.
