# Bybit Futures HFT Deployment Guide

## Quick Start

### Prerequisites

1. **Bybit Account** with API access
   - Sign up at https://www.bybit.com
   - Complete KYC verification
   - Enable 2FA for security

2. **API Keys** with Contract Trading permissions
   - Go to API Management
   - Create new API key
   - Enable permissions: "Contract" + "Read-Write"
   - Restrict by IP address (recommended)
   - Save API key and secret securely

3. **Server Requirements**
   - Ubuntu 20.04+ or similar Linux distribution
   - Python 3.9+
   - 2GB+ RAM
   - Stable internet connection (low latency preferred)
   - Geographic location with Bybit API access (use VPN if needed)

## Installation

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd algo-imp
```

### 2. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Create .env file
cat > .env <<EOF
# Bybit API credentials
BYBIT_API_KEY=your-api-key-here
BYBIT_API_SECRET=your-api-secret-here

# Optional: MEXC credentials for spot trading
MEXC_API_KEY=your-mexc-key
MEXC_API_SECRET=your-mexc-secret
EOF

# Secure the .env file
chmod 600 .env
```

## Testing Phase

### Step 1: Dry-Run Testing (Paper Trading)

Test with simulated trading to verify the system works:

```bash
# 30-minute dry-run test with 50x leverage
timeout 1800 python scripts/run_paper_trader.py \
  --futures \
  --leverage=50 \
  --order-size=0.001 \
  --interval=5 \
  --gamma=0.01 \
  --kappa-value=1.0 \
  --arrival-rate=50
```

**Expected behavior:**
- System starts and shows configuration
- Quotes are updated every 5 seconds
- Trades execute when conditions are met
- P&L is tracked continuously
- Safety controls activate (displacement guard, asymmetric spreads, etc.)

**Monitor for:**
- ✅ No errors in ticker fetching
- ✅ Quotes updating regularly
- ✅ Reasonable spread sizes (not too wide or narrow)
- ✅ Liquidation price calculated correctly
- ✅ Emergency position reduction triggers when needed

### Step 2: Conservative Live Test

Start with minimal capital and conservative leverage:

```bash
# Live trading with 10x leverage, small size
python scripts/run_paper_trader.py \
  --futures \
  --leverage=10 \
  --order-size=0.0001 \
  --live \
  --interval=5
```

**Safety checklist:**
- [ ] Start with $100-200 capital
- [ ] Use 10x leverage initially
- [ ] Monitor for 1-2 hours
- [ ] Verify fills are profitable
- [ ] Check liquidation distances
- [ ] Review fee impact

### Step 3: Scale Up Gradually

Once comfortable with 10x leverage:

```bash
# Increase to 25x leverage
python scripts/run_paper_trader.py \
  --futures \
  --leverage=25 \
  --order-size=0.0005 \
  --live

# Eventually scale to 50x for HFT
python scripts/run_paper_trader.py \
  --futures \
  --leverage=50 \
  --order-size=0.001 \
  --live
```

## Production Deployment

### Recommended Configuration

```bash
#!/bin/bash
# production_start.sh

python scripts/run_paper_trader.py \
  --futures \
  --leverage=50 \
  --order-size=0.001 \
  --interval=5 \
  --gamma=0.01 \
  --kappa-value=1.0 \
  --arrival-rate=50 \
  --max-spread=100 \
  --min-spread=5 \
  --live \
  2>&1 | tee -a logs/trader_$(date +%Y%m%d_%H%M%S).log
```

### Running as a Service (systemd)

Create a systemd service for automatic restart:

```ini
# /etc/systemd/system/bybit-hft.service
[Unit]
Description=Bybit HFT Market Maker
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/algo-imp
Environment="PATH=/path/to/algo-imp/venv/bin"
ExecStart=/path/to/algo-imp/venv/bin/python scripts/run_paper_trader.py --futures --leverage=50 --live
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable bybit-hft
sudo systemctl start bybit-hft
sudo systemctl status bybit-hft

# View logs
sudo journalctl -u bybit-hft -f
```

### Using tmux/screen (Alternative)

```bash
# Start in tmux session
tmux new -s hft

# Inside tmux, run the bot
python scripts/run_paper_trader.py --futures --leverage=50 --live

# Detach: Ctrl+B, then D
# Reattach: tmux attach -t hft
```

## Risk Management

### Position Sizing

**Conservative (Recommended for Start):**
- Leverage: 10-20x
- Order size: 0.0001-0.0005 BTC ($6-30 per trade at $60k BTC)
- Capital: $500-1,000

**Moderate:**
- Leverage: 30-40x
- Order size: 0.0005-0.001 BTC ($30-60 per trade)
- Capital: $1,000-2,500

**Aggressive (HFT):**
- Leverage: 50-75x
- Order size: 0.001-0.002 BTC ($60-120 per trade)
- Capital: $2,500-5,000

### Liquidation Safety

The system has built-in protection:
- **Liquidation threshold:** 20% distance to liquidation triggers emergency reduction
- **Emergency reduce:** Cuts position size by 50% when threshold hit
- **Hard limit:** Stops accumulating at 5x order size on one side

**Manual monitoring:**
```bash
# Check position every few hours
# Look for liquidation price in logs
grep "liq_price" logs/trader_*.log | tail -20
```

### Stop-Loss Protocol

**Automated:**
- System pulls quotes during strong trends (ADX > threshold)
- Displacement guard widens spreads during volatility
- Inventory limits prevent runaway positions

**Manual:**
1. Set daily loss limit (e.g., -10% of capital)
2. Monitor total P&L regularly
3. Stop trading if daily limit hit
4. Review strategy if consistent losses

## Monitoring & Alerts

### Key Metrics to Monitor

1. **P&L** - Should be net positive over time
2. **Win Rate** - Target 55-70% on closed trades
3. **Fill Rate** - Too many fills may indicate adverse selection
4. **Spread Size** - Should stay within bounds (5-100 bps)
5. **Liquidation Distance** - Never below 20%
6. **Error Count** - Should be 0 or minimal

### Log Analysis

```bash
# Check recent fills
grep "FILL:" logs/trader_*.log | tail -20

# Check safety activations
grep "DISPLACEMENT GUARD\|ASYMMETRIC\|LIQUIDATION" logs/trader_*.log | tail -20

# Check errors
grep "Error\|error" logs/trader_*.log | tail -20

# Calculate win rate
python -c "
import re
fills = []
with open('logs/trader_latest.log') as f:
    for line in f:
        if 'FILL:' in line:
            fills.append(line)
print(f'Total fills: {len(fills)}')
"
```

### Alert Setup (Optional)

Create a simple Discord/Telegram webhook for alerts:

```python
# alert_monitor.py
import requests
import time

DISCORD_WEBHOOK = "your-webhook-url"

def check_liquidation_risk(log_file):
    """Monitor for high liquidation risk"""
    # Implementation here
    pass

def send_alert(message):
    requests.post(DISCORD_WEBHOOK, json={"content": message})

# Run this in a separate process
```

## Parameter Tuning

### GLFT Parameters

**Risk Aversion (γ):**
- Lower γ = tighter spreads, more aggressive
- Higher γ = wider spreads, more conservative
- Default: 0.01 (good for 50x leverage HFT)
- Range: 0.005-0.02

**Order Book Liquidity (κ):**
- Measures how fast limit orders get filled
- Higher κ = faster fills expected
- Default: 1.0 (aggressive)
- Range: 0.5-2.0

**Arrival Rate (A):**
- Expected trades per unit time
- Higher A = tighter spreads
- Default: 50 (HFT-optimized)
- Range: 20-100

### Testing Different Parameters

```bash
# Conservative (wider spreads, safer)
python scripts/run_paper_trader.py --futures --gamma=0.02 --kappa-value=0.5 --arrival-rate=20

# Aggressive (tighter spreads, more trades)
python scripts/run_paper_trader.py --futures --gamma=0.005 --kappa-value=2.0 --arrival-rate=100
```

## Troubleshooting

### Common Issues

**1. "403 Forbidden" errors**
- Geographic restriction from Bybit
- Solution: Use VPN or deploy to supported region

**2. "Insufficient margin" errors**
- Not enough capital for leverage
- Solution: Reduce leverage or increase capital

**3. No fills for extended period**
- Spreads too wide
- Solution: Lower γ, increase A, or increase κ

**4. Too many losing trades**
- Adverse selection during trends
- Safety controls should handle this, but verify they're active

**5. Rapid liquidation approaches**
- Position size too large for volatility
- Solution: Reduce leverage or order size

### Emergency Stop

```bash
# Kill the process
pkill -f "run_paper_trader.py"

# Or in tmux/screen
tmux attach -t hft
# Press Ctrl+C

# Or with systemd
sudo systemctl stop bybit-hft
```

## Performance Expectations

### Realistic Targets (50x leverage, $1,000 capital)

**Daily:**
- Trades: 50-200
- Win rate: 55-65%
- Daily P&L: +$5 to +$20 (0.5-2% daily)
- Max drawdown: -$50 to -$100 (5-10%)

**Monthly:**
- Total P&L: +$100 to +$400 (10-40% monthly)
- Sharpe ratio: 1.5-2.5
- Max drawdown: -15% to -25%

**Risks:**
- One bad day can wipe out a week of gains
- Liquidation events are possible (though protected)
- High leverage amplifies both gains AND losses

## Security Best Practices

1. **Never commit API keys** to git
2. **Use IP whitelist** on Bybit API keys
3. **Enable 2FA** on Bybit account
4. **Restrict API permissions** to minimum needed
5. **Monitor account regularly** for unauthorized access
6. **Rotate API keys** every 3 months
7. **Use separate account** for testing vs production
8. **Keep server updated** with security patches

## Next Steps

1. ✅ Complete dry-run testing (30-60 minutes)
2. ✅ Run conservative live test (10x leverage, 2 hours)
3. ✅ Monitor and tune parameters
4. ✅ Scale up gradually to 50x leverage
5. ✅ Set up monitoring and alerts
6. ✅ Establish daily review routine

## Support

- Review logs regularly
- Test parameter changes in dry-run first
- Start conservative and scale up gradually
- Monitor liquidation distances closely
- Keep capital you can afford to lose

**Remember:** HFT with 50x leverage is extremely risky. Always start small and scale up as you gain confidence in the system.
