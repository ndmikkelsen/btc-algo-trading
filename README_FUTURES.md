# Bybit Futures HFT Quick Start

High-frequency trading with 50x leverage on Bybit perpetual futures.

## 🚀 Quick Start

### 1. Setup (2 minutes)

```bash
# Install dependencies
pip install -r requirements.txt

# Set API keys (for live trading)
export BYBIT_API_KEY='your-api-key'
export BYBIT_API_SECRET='your-api-secret'
```

### 2. Test (5 minutes)

```bash
# Dry-run test (no API keys needed)
python scripts/run_paper_trader.py --futures --leverage=50 --order-size 0.001
```

### 3. Deploy (when ready)

```bash
# Live trading with 50x leverage
python scripts/run_paper_trader.py --futures --leverage=50 --live
```

## 📊 What You Get

- ✅ **50-100x Leverage** - Configurable leverage for HFT
- ✅ **Bybit Perpetual Futures** - BTC/USDT:USDT contract
- ✅ **Liquidation Protection** - Emergency position reduction
- ✅ **Phase 1 + 2 Safety** - 10+ safety controls active
- ✅ **Real-time Risk Management** - Position limits, cooldowns, displacement guards
- ✅ **0.01% Maker Fees** - Low fees for high-frequency trading

## 🎯 Performance Targets (50x leverage, $1,000 capital)

**Daily:**
- Trades: 50-200
- Win rate: 55-65%
- P&L: +$5 to +$20 (0.5-2% daily)

**Monthly:**
- P&L: +$100 to +$400 (10-40% monthly)

## ⚠️ Risk Warning

**High leverage = High risk**
- 50x leverage amplifies gains AND losses
- Liquidation is possible (but protected)
- Only trade with capital you can afford to lose
- Start with 10x leverage, scale up gradually

## 📖 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- **[BYBIT_FUTURES_DESIGN.md](BYBIT_FUTURES_DESIGN.md)** - Architecture details

## 🛠️ Key Parameters

**Leverage:**
- Conservative: 10-20x
- Moderate: 30-40x
- Aggressive: 50-75x

**GLFT Model:**
- `--gamma` (risk aversion): 0.005-0.02 (default: 0.01)
- `--kappa-value` (liquidity): 0.5-2.0 (default: 1.0)
- `--arrival-rate`: 20-100 (default: 50)

**Order Sizing:**
- Small: 0.0001 BTC ($6 per trade at $60k)
- Medium: 0.001 BTC ($60 per trade)
- Large: 0.002 BTC ($120 per trade)

## 🔍 Monitoring

```bash
# Analyze performance
python scripts/analyze_performance.py logs/trader_*.log

# Monitor live
tail -f logs/trader_$(date +%Y%m%d).log | grep "FILL:\|P&L:\|LIQUIDATION"
```

## 🆘 Emergency Stop

```bash
# Kill the process
pkill -f "run_paper_trader.py"

# Or press Ctrl+C in the terminal
```

## 📞 Support

1. Read [DEPLOYMENT.md](DEPLOYMENT.md) for detailed setup
2. Check logs for errors: `grep Error logs/trader_*.log`
3. Test in dry-run mode first before going live
4. Start with low leverage (10x) and scale up

## 🎓 Learning Path

1. ✅ **Week 1:** Dry-run testing, understand the system
2. ✅ **Week 2:** Live trading with 10x leverage, $100-200 capital
3. ✅ **Week 3:** Scale to 25x leverage if profitable
4. ✅ **Week 4+:** Scale to 50x leverage with proven strategy

**Remember:** Patience and discipline > aggressive leverage

---

**Built with:**
- Python 3.9+
- ccxt (Bybit API)
- GLFT market making model
- Phase 1 + 2 safety controls

**License:** Use at your own risk. No guarantees or warranties.
