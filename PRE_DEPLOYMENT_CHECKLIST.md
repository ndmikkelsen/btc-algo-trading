# Pre-Deployment Validation Checklist

Run this checklist before deploying Bybit futures strategy to production.

## ✅ Code Validation

### 1. Run Unit Tests
```bash
python -m pytest tests/ -v
```
**Expected:** All 369 tests passing ✅

### 2. Check for Syntax Errors
```bash
python -m py_compile strategies/avellaneda_stoikov/bybit_futures_client.py
python -m py_compile strategies/avellaneda_stoikov/live_trader.py
```
**Expected:** No errors ✅

### 3. Validate Configuration
```bash
python -c "
from strategies.avellaneda_stoikov.config import *
print(f'Leverage: {LEVERAGE}x')
print(f'Liquidation Threshold: {LIQUIDATION_THRESHOLD}')
print(f'Phase 2 Features: {DYNAMIC_GAMMA_ENABLED, ASYMMETRIC_SPREADS_ENABLED}')
"
```
**Expected:** Proper values loaded ✅

## ✅ API Connectivity (Run on Your Server)

### 1. Test Bybit API Access
```bash
python -c "
import ccxt
exchange = ccxt.bybit({'options': {'defaultType': 'swap'}})
ticker = exchange.fetch_ticker('BTC/USDT:USDT')
print(f'✅ Bybit API working: BTC = \${ticker[\"last\"]:,.2f}')
"
```
**Expected:** Current BTC price returned

### 2. Test with Dry-Run (1 minute)
```bash
timeout 60 python scripts/run_paper_trader.py --futures --leverage=50
```
**Expected:**
- ✅ Starts without errors
- ✅ Shows "Quotes updated"
- ✅ Safety controls initialized

## ✅ Strategy Validation

### Run Test Suite
```bash
chmod +x scripts/test_bybit_strategy.sh
./scripts/test_bybit_strategy.sh
```

**Check for:**
- [ ] API connectivity working
- [ ] Quotes updating every 5 seconds
- [ ] Safety controls activating (displacement, asymmetric, etc.)
- [ ] Fills executing properly
- [ ] No errors in logs
- [ ] Liquidation monitoring active
- [ ] P&L tracking correctly

## ✅ Risk Management Check

### 1. Verify Liquidation Protection
```bash
grep "LIQUIDATION_THRESHOLD\|EMERGENCY_REDUCE" strategies/avellaneda_stoikov/config.py
```
**Expected:**
- LIQUIDATION_THRESHOLD = 0.20 (20%)
- EMERGENCY_REDUCE_RATIO = 0.5 (50%)

### 2. Verify Inventory Limits
```bash
grep "INVENTORY.*LIMIT" strategies/avellaneda_stoikov/config.py
```
**Expected:**
- INVENTORY_SOFT_LIMIT = 3
- INVENTORY_HARD_LIMIT = 5

### 3. Check Spread Bounds
```bash
python -c "
from strategies.avellaneda_stoikov.config import MIN_SPREAD_DOLLAR, MAX_SPREAD_DOLLAR
print(f'Spread range: \${MIN_SPREAD_DOLLAR} - \${MAX_SPREAD_DOLLAR}')
"
```
**Expected:** $5 - $100

## ✅ Security Check

### 1. API Keys Not Committed
```bash
git log --all --full-history --source --pretty=format: -- .env | grep -i "key\|secret"
```
**Expected:** No results (keys not in git history)

### 2. .env File Protected
```bash
ls -la .env 2>/dev/null && stat -f "%A" .env
```
**Expected:** 600 permissions or file doesn't exist yet

### 3. Sensitive Files in .gitignore
```bash
grep -E "\.env|.*secret|.*key" .gitignore
```
**Expected:** .env and credentials excluded

## ✅ Performance Baseline

### Run 30-Minute Dry-Run
```bash
timeout 1800 python scripts/run_paper_trader.py \
  --futures \
  --leverage=50 \
  --order-size=0.001 \
  --gamma=0.01 \
  --kappa-value=1.0 \
  --arrival-rate=50 \
  2>&1 | tee logs/baseline_test.log
```

### Analyze Results
```bash
python scripts/analyze_performance.py logs/baseline_test.log
```

**Check for:**
- [ ] Win rate > 50%
- [ ] No critical errors
- [ ] Reasonable fill rate (10-50 fills in 30 min)
- [ ] Spreads within bounds
- [ ] Safety controls active
- [ ] Liquidation protection working

### Expected Baseline (30 min dry-run):
- Fills: 10-30
- Win rate: 50-70%
- P&L: -$5 to +$10 (highly variable)
- Errors: 0
- Safety activations: 5-20

## ✅ Final Pre-Launch Checklist

Before going live with real money:

- [ ] All unit tests passing (369/369)
- [ ] Dry-run test successful (30+ min)
- [ ] API connectivity verified
- [ ] Safety controls validated
- [ ] Liquidation protection tested
- [ ] No errors in logs
- [ ] Performance baseline acceptable
- [ ] API keys secured
- [ ] .env file created with real keys
- [ ] Starting capital decided ($500-1000 recommended)
- [ ] Leverage level decided (start with 10x, not 50x!)
- [ ] Order size calculated (0.0001-0.001 BTC)
- [ ] Monitoring plan in place
- [ ] Stop-loss protocol defined
- [ ] Emergency contact access confirmed

## 🚦 Go/No-Go Decision

### GREEN LIGHT ✅ (Safe to proceed with conservative live test)
- All tests passing
- No errors in 30-min dry-run
- Safety controls active
- Win rate > 50% in dry-run
- You understand the risks

**Start with:**
- Capital: $200-500
- Leverage: 10x (NOT 50x yet!)
- Order size: 0.0001 BTC
- Duration: 1-2 hours monitored

### YELLOW LIGHT ⚠️ (Needs investigation)
- Some tests failing
- Errors in logs but system recovers
- Win rate 40-50%
- Unusual behavior

**Action:** Review logs, adjust parameters, retest

### RED LIGHT 🛑 (Do NOT go live)
- Critical errors
- System crashes
- Cannot connect to API
- Win rate < 40%
- Liquidation triggers frequently

**Action:** Debug issues, fix code, comprehensive retest

## 📊 Ongoing Monitoring (Once Live)

### Every Hour:
- [ ] Check P&L
- [ ] Verify no errors in logs
- [ ] Check liquidation distance
- [ ] Verify fills are profitable

### Daily:
- [ ] Review full day performance
- [ ] Analyze win rate trend
- [ ] Check safety control frequency
- [ ] Adjust parameters if needed

### Weekly:
- [ ] Calculate weekly P&L
- [ ] Review max drawdown
- [ ] Optimize parameters
- [ ] Consider leverage scaling

## 🆘 Emergency Procedures

**If things go wrong:**

1. **Stop the bot immediately:**
   ```bash
   pkill -f "run_paper_trader.py"
   ```

2. **Check current position:**
   ```bash
   # Log into Bybit web interface
   # Check open positions
   # Manually close if needed
   ```

3. **Review what happened:**
   ```bash
   python scripts/analyze_performance.py logs/trader_*.log
   grep -i "error\|liquidation" logs/trader_*.log
   ```

4. **Don't restart until issue is understood**

---

**Remember:** This is high-risk trading with leverage. Start small, test thoroughly, scale gradually.
