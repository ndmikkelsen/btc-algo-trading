---
triggers: ['/run-test', 'start paper trading', 'run dry run', 'test trader', 'paper trade']
description: Launch GLFT market maker in dry-run mode (real market data, simulated fills)
---

# /run-test — Dry-Run Paper Trading Launcher

Launch the GLFT market maker in dry-run mode: real MEXC market data with simulated order fills. No real money at risk.

## Usage

```
/run-test                              # Defaults: BTCUSDT, GLFT, live kappa
/run-test --symbol ETHUSDT             # Different symbol
/run-test --gamma 0.001                # Custom risk aversion
/run-test --kappa constant --kappa-value 0.05  # Fixed kappa
/run-test --order-size 0.005           # Larger orders
/run-test --interval 3                 # Faster updates
/run-test --min-spread 10 --max-spread 200     # Custom spread bounds
/run-test --capital 5000               # More capital
/run-test --no-regime-filter           # Disable regime detection
```

## Implementation

When user invokes `/run-test`, execute the following steps:

### Step 1: Parse Arguments

Extract flags from the user's command. All flags are optional with smart defaults:

| Flag | Default | Description |
|------|---------|-------------|
| `--symbol` | `BTCUSDT` | Trading pair |
| `--gamma` | `0.005` | Risk aversion γ (1/$² units) |
| `--kappa` | `live` | Kappa mode: `live` (from order book) or `constant` |
| `--kappa-value` | `0.5` | κ value when `--kappa=constant` (1/$ units) |
| `--arrival-rate` | `20.0` | Arrival rate A for constant kappa mode |
| `--order-pct` | `4.0` | Order size as % of capital (e.g., 4.0 = 4%) |
| `--interval` | `5.0` | Quote update interval (seconds) |
| `--min-spread` | `5.0` | Minimum spread in dollars |
| `--max-spread` | `100.0` | Maximum spread in dollars |
| `--capital` | `1000.0` | Initial capital in USDT |
| `--fee-tier` | `regular` | Fee tier: `regular`, `mx_deduction` |
| `--no-regime-filter` | false | Disable regime detection |

### Step 2: Validate Environment

```bash
# Load .env for MEXC API keys (needed for real market data even in dry-run)
source .env 2>/dev/null || true
```

MEXC API keys are needed even for dry-run mode because the DryRunClient fetches real market data from MEXC. If keys are missing, the script will use dummy keys but market data requests may fail. Warn the user if keys are not found.

### Step 3: Generate Log Filename

```bash
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="${LOG_DIR}/dry-run-${SYMBOL}-${TIMESTAMP}.log"
```

### Step 4: Build and Launch Command

Construct the command from parsed arguments. **Never pass `--live`** — this is always dry-run mode.

```bash
CMD="python scripts/run_paper_trader.py \
  --model=glft \
  --gamma=${GAMMA} \
  --kappa=${KAPPA_MODE} \
  --kappa-value=${KAPPA_VALUE} \
  --arrival-rate=${ARRIVAL_RATE} \
  --order-size=${ORDER_SIZE} \
  --interval=${INTERVAL} \
  --min-spread=${MIN_SPREAD} \
  --max-spread=${MAX_SPREAD} \
  --capital=${CAPITAL} \
  --fee-tier=${FEE_TIER} \
  ${REGIME_FLAG}"
```

Note: No `--live` flag is ever added. The script defaults to dry-run mode.

### Step 5: Launch with Dashboard

Check if the TUI dashboard script exists at `scripts/live_dashboard.py`:

**If TUI dashboard exists:**
```bash
# Launch trader with TUI dashboard
python scripts/live_dashboard.py \
  --trader-cmd "${CMD}" \
  --log-file "${LOG_FILE}" 2>&1 | tee "${LOG_FILE}"
```

**If TUI dashboard does NOT exist yet (fallback):**
```bash
# Run trader directly with output visible and logged
${CMD} 2>&1 | tee "${LOG_FILE}" &
TRADER_PID=$!
echo "Paper trader started (PID: ${TRADER_PID})"
echo "Logging to: ${LOG_FILE}"
echo "Stop with: kill ${TRADER_PID}  or  /stop"
```

Use the Bash tool to launch the command. Run it in the background so Claude remains responsive.

### Step 6: Report Launch Status

After launching, display:

```
Paper trader started (dry-run mode).

  PID:      {pid}
  Log:      {log_file}
  Symbol:   {symbol}
  Mode:     DRY-RUN (simulated fills, real market data)

  Monitor:  tail -f {log_file}
  Stop:     /stop  or  kill {pid}
```

## How Dry-Run Mode Works

The DryRunClient:
- Connects to real MEXC market data (ticker, order book, trades)
- Simulates order fills locally when price crosses your limit orders
- Tracks virtual USDT/BTC balance
- LIMIT_MAKER orders are rejected if they would cross (same as real exchange)
- No real money is at risk

This lets you validate strategy behavior with real market conditions before going live.

## Safety Rules

1. **NEVER pass `--live` flag** — this skill is exclusively for dry-run mode
2. **No confirmation needed** — paper trading is safe, just launch immediately
3. **Always log to a file** with auto-generated timestamp filename
4. If any parameter looks unusual (e.g., order_size > 0.1 BTC, capital > 50000), note it but proceed
5. Use `/run-live` if the user wants real trading

## Quick Reference

```
# Conservative settings (tight spreads, small orders)
/run-test --gamma 0.01 --order-size 0.001 --min-spread 10

# Aggressive settings (wide spreads, larger orders)
/run-test --gamma 0.0005 --order-size 0.005 --max-spread 300

# Fast iteration (quick updates)
/run-test --interval 2

# Fixed kappa (skip live calibration)
/run-test --kappa constant --kappa-value 0.03

# Trade ETH instead
/run-test --symbol ETHUSDT --order-size 0.05
```
