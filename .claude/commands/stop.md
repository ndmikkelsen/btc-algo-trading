---
triggers: ['/stop', 'stop trading', 'stop trader', 'kill trader', 'shutdown trader']
description: Gracefully stop running trading processes (live or test)
---

# /stop -- Graceful Trading Shutdown

Stop running `/run-live` or `/run-test` trading processes by sending SIGINT, which triggers the trader's `stop()` method to cancel all open orders and print a session summary.

## Execution

### Step 1: Find Running Trading Processes

```bash
# Find python processes running trading scripts
ps aux | grep -E 'run_paper_trader|run_shadow_trader|live_trader' | grep -v grep
```

If **no processes found**, report that no trading processes are currently running and exit.

### Step 2: Identify Process Details

For each process found, extract:
- **PID** - process ID
- **Script** - which runner script (paper trader, shadow trader)
- **Arguments** - flags like `--live`, `--futures`, `--model`

Display a summary:

```
Trading Processes Found:
  PID 12345 - run_paper_trader.py --futures (Bybit futures dry-run)
  PID 12346 - run_paper_trader.py --live (MEXC spot LIVE)
```

### Step 3: Send SIGINT for Graceful Shutdown

```bash
# Send SIGINT (same as Ctrl+C) to trigger trader.stop()
# This cancels all open orders, prints session summary with PnL
kill -INT <PID>
```

**IMPORTANT:** Use `kill -INT` (SIGINT), NOT `kill -9` (SIGKILL). SIGINT triggers the signal handler in `run_paper_trader.py` which calls `trader.stop()`:
- Cancels all open exchange orders via `cancel_all_orders()`
- Sets `is_running = False`
- Prints the session summary (PnL, trades, fees, inventory)

### Step 4: Verify Shutdown

```bash
# Wait a moment for graceful shutdown
sleep 2

# Verify process has exited
ps aux | grep -E 'run_paper_trader|run_shadow_trader|live_trader' | grep -v grep
```

If process is **still running** after 5 seconds:

```bash
# Try SIGTERM as escalation
kill -TERM <PID>
sleep 2

# Last resort: verify it's gone
ps aux | grep -E 'run_paper_trader|run_shadow_trader|live_trader' | grep -v grep
```

**NEVER use `kill -9` unless explicitly requested by the user.** Force-killing skips the shutdown handler, leaving orders open on the exchange.

### Step 5: Report Results

Display shutdown summary:

```
Trader Shutdown Complete
========================
Process:  run_paper_trader.py (PID 12345)
Mode:     DRY-RUN / LIVE
Exchange: MEXC Spot / Bybit Futures
Signal:   SIGINT (graceful)
Status:   Stopped
```

If the trader printed its session summary to stdout (PnL, trades, fees), relay that information to the user.

## Safety Notes

- **Live mode (--live)**: SIGINT triggers `cancel_all_orders()` on the real exchange before exiting. This is critical -- always prefer graceful shutdown.
- **Dry-run mode**: No real orders to cancel, but the summary still reports simulated PnL.
- **Multiple processes**: If multiple trading processes are found, stop ALL of them (or ask user which one if they seem intentional).
- **Orphaned orders**: If a process was killed ungracefully in a previous session, remind the user to check for open orders on the exchange.

## Related Commands

- `/run-live` - Start live trading
- `/run-test` - Start dry-run paper trading
- `/land` - Session landing protocol
