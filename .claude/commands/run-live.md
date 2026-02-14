---
triggers: ['/run-live', 'start live trading', 'run live trader', 'go live']
description: Launch GLFT market maker with real orders on Bybit Futures
---

# /run-live — Live Trading Launcher

Launch the GLFT market maker with real orders on Bybit Futures.

## Usage

```
/run-live                              # Defaults: BTCUSDT, GLFT, live kappa
/run-live --symbol ETHUSDT             # Different symbol
/run-live --gamma 0.001                # Custom risk aversion
/run-live --kappa constant --kappa-value 0.05  # Fixed kappa
/run-live --order-size 0.005           # Larger orders
/run-live --interval 3                 # Faster updates
/run-live --min-spread 10 --max-spread 200     # Custom spread bounds
/run-live --capital 5000               # More capital
/run-live --no-regime-filter           # Disable regime detection
/run-live --dry-run                    # Override: paper trade instead
```

## Implementation

When user invokes `/run-live`, execute the following steps:

### Step 1: Parse Arguments

Extract flags from the user's command. All flags are optional with smart defaults:

| Flag | Default | Description |
|------|---------|-------------|
| `--symbol` | `BTC/USDT:USDT` | Trading pair (Bybit perpetual format) |
| `--leverage` | `5` | Leverage (1-100x) |
| `--gamma` | `0.005` | Risk aversion γ (1/$² units) |
| `--kappa` | `constant` | Kappa mode: `constant` (Bybit futures) or `live` |
| `--kappa-value` | `0.5` | κ value when `--kappa=constant` (1/$ units) |
| `--arrival-rate` | `50.0` | Arrival rate A for constant kappa mode |
| `--order-size` | `0.001` | Order size in BTC (min 0.001 for Bybit) |
| `--interval` | `5.0` | Quote update interval (seconds) |
| `--min-spread` | `5.0` | Minimum spread in dollars |
| `--max-spread` | `100.0` | Maximum spread in dollars |
| `--capital` | `500.0` | Initial capital in USDT |
| `--fee-tier` | `bybit_vip0` | Fee tier: `bybit_vip0`, `bybit_vip1` |
| `--no-regime-filter` | false | Disable regime detection |
| `--dry-run` | false | Override to paper trade mode |

### Step 2: Validate Environment

```bash
# Check that Bybit credentials are set (required for live trading)
if [ -z "$BYBIT_API_KEY" ] || [ -z "$BYBIT_API_SECRET" ]; then
  # Try loading from .env
  source .env 2>/dev/null
fi
```

If `--dry-run` is NOT set, verify `BYBIT_API_KEY` and `BYBIT_API_SECRET` are available.
If missing, **stop and warn the user** — do NOT proceed with live trading without credentials.

If `--dry-run` IS set, credentials are optional (dummy keys used automatically).

Also check for `SOCKS5_PROXY` if geo-blocking is an issue (Bybit blocks some regions).

### Step 3: Confirm Live Trading

**CRITICAL SAFETY CHECK** — Unless `--dry-run` is set:

Display this confirmation to the user:

```
⚠️  LIVE TRADING MODE ⚠️

  Symbol:        {symbol}
  Order Size:    {order_size} BTC
  Capital:       {capital} USDT
  Risk Aversion: γ = {gamma}
  Kappa Mode:    {kappa}
  Spread Bounds: ${min_spread} - ${max_spread}
  Interval:      {interval}s
  Regime Filter: {enabled/disabled}

  This will place REAL orders on MEXC with REAL money.

  Proceed? [y/N]
```

Use AskUserQuestion to get explicit confirmation. **Do NOT skip this step.**

### Step 4: Generate Log Filename

```bash
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="${LOG_DIR}/live-${SYMBOL}-${TIMESTAMP}.log"
```

### Step 5: Build and Launch Command

Construct the command from parsed arguments:

```bash
LIVE_FLAG="--live"
# Override to dry-run if --dry-run was passed
if [ "$DRY_RUN" = true ]; then
  LIVE_FLAG=""
fi

CMD="python3 scripts/run_paper_trader.py \
  --futures \
  --model=glft \
  --leverage=${LEVERAGE} \
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
  ${REGIME_FLAG} \
  ${LIVE_FLAG}"
```

### Step 6: Launch with Dashboard

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
echo "Trader started (PID: ${TRADER_PID})"
echo "Logging to: ${LOG_FILE}"
echo "Stop with: kill ${TRADER_PID}  or  /stop"
```

Use the Bash tool to launch the command. Run it in the background so Claude remains responsive.

### Step 7: Report Launch Status

After launching, display:

```
Live trader started.

  PID:      {pid}
  Log:      {log_file}
  Symbol:   {symbol}
  Mode:     {live or dry-run}

  Monitor:  tail -f {log_file}
  Stop:     /stop  or  kill {pid}
```

## Safety Rules

1. **NEVER skip the confirmation step** for live trading
2. **NEVER default to live mode** — the `--live` flag on `run_paper_trader.py` must be explicitly set
3. **Always log to a file** with auto-generated timestamp filename
4. If any parameter looks suspicious (e.g., order_size > 0.1 BTC, capital > 50000), warn the user
5. If `--dry-run` is passed, skip confirmation and run in paper trade mode

## Quick Reference

```
# Conservative settings (tight spreads, small orders)
/run-live --gamma 0.01 --order-size 0.001 --min-spread 10

# Aggressive settings (wide spreads, larger orders)
/run-live --gamma 0.0005 --order-size 0.005 --max-spread 300

# Paper trade first (no real orders)
/run-live --dry-run

# Fixed kappa (skip live calibration)
/run-live --kappa constant --kappa-value 0.03
```
