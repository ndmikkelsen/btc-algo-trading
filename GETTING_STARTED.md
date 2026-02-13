# Getting Started

A guide to running the BTC algorithmic trading bot — from setup to paper trading.

## What This Is

This is an automated BTC/USDT market-making bot built on the **Avellaneda-Stoikov (A-S) model**, a mathematically optimal framework for quoting bid and ask prices in a limit order book. The model was introduced in *"High-frequency trading in a limit order book"* (Avellaneda & Stoikov, 2008).

The bot continuously places buy and sell limit orders around the current market price, earning the bid-ask spread. It manages inventory risk through a **reservation price** that adjusts quotes based on your current position, and uses **regime detection** (ADX indicator) to pause trading during strong trends — because market making performs best in ranging (sideways) markets.

**Key backtest results:**
- +43.52% annualized return in ranging markets (ADX < 25)
- ~55% win rate with 2:1 risk/reward ratio
- Optimized for $1,000 starting capital

The bot trades on **Bybit** (testnet for paper trading, mainnet for live).

## Prerequisites

- **Python 3.10+**
- **pip** (comes with Python)
- **TA-Lib** — C library for technical indicators (required by dependencies)
- **Bybit account** — testnet for paper trading, mainnet for live
- **Git** — to clone the repository

### Installing TA-Lib

TA-Lib requires a system-level C library before the Python wrapper can install.

**macOS (Homebrew):**
```bash
brew install ta-lib
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y build-essential wget
wget https://github.com/TA-Lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz
tar -xzf ta-lib-0.6.4-src.tar.gz
cd ta-lib-0.6.4/
./configure --prefix=/usr
make
sudo make install
cd .. && rm -rf ta-lib-0.6.4 ta-lib-0.6.4-src.tar.gz
```

**Windows:**

Download the pre-built binary from [TA-Lib releases](https://github.com/TA-Lib/ta-lib/releases) and follow the installation instructions for your platform.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd algo-imp

# Create a virtual environment
python -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

Verify the installation:
```bash
python -c "from strategies.avellaneda_stoikov import AvellanedaStoikov; print('OK')"
```

## Configuration

### 1. Get Bybit Testnet API Keys

1. Go to [https://testnet.bybit.com](https://testnet.bybit.com)
2. Create an account (this is separate from your mainnet account)
3. Navigate to **API Management** in your account settings
4. Create a new API key with **trading permissions** enabled
5. Save the API key and secret — you'll need both

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
BYBIT_API_KEY=your-testnet-api-key-here
BYBIT_API_SECRET=your-testnet-api-secret-here
```

Alternatively, export them in your shell:

```bash
export BYBIT_API_KEY='your-testnet-api-key-here'
export BYBIT_API_SECRET='your-testnet-api-secret-here'
```

### 3. Strategy Parameters

The optimized parameters live in `strategies/avellaneda_stoikov/config_optimized.py`. The defaults are tuned from backtesting and should work out of the box:

| Parameter | Default | Description |
|---|---|---|
| `INITIAL_CAPITAL` | $1,000 | Starting capital in USDT |
| `RISK_AVERSION` | 0.1 | How aggressively inventory is managed (higher = tighter quotes when holding) |
| `ORDER_BOOK_LIQUIDITY` | 2.5 | Order book density assumption (higher = tighter spreads) |
| `ORDER_SIZE` | 0.003 BTC | Size of each limit order |
| `MIN_SPREAD` | 0.4% | Floor for bid-ask spread (must exceed 0.2% round-trip fee) |
| `MAX_SPREAD` | 3% | Ceiling for bid-ask spread |
| `USE_REGIME_FILTER` | True | Pause trading in strong trends |
| `ADX_TREND_THRESHOLD` | 25 | ADX above this = trending market |
| `MAKER_FEE` | 0.1% | Bybit maker fee |

You generally don't need to change these. If you do adjust them, re-run backtests first to validate performance.

## Backtesting

Backtesting lets you test the strategy against historical data before risking any capital.

### Step 1: Download Historical Data

```bash
python scripts/download_data.py --timeframe 1h --days 365
```

This downloads BTC/USDT 1-hour candles from Bybit and saves them to `data/btcusdt_1h.csv`.

Options:
- `--timeframe` / `-t` — Candle interval: `1m`, `5m`, `15m`, `1h`, `4h`, `1d` (default: `1h`)
- `--days` / `-d` — Days of history (default: `365`)
- `--exchange` / `-e` — Exchange source: `bybit`, `binance` (default: `bybit`)

### Step 2: Run the Backtest

```bash
python scripts/run_as_backtest.py
```

With custom parameters:
```bash
python scripts/run_as_backtest.py \
    --timeframe 1h \
    --days 90 \
    --cash 1000 \
    --risk-aversion 0.1 \
    --liquidity 1.5 \
    --order-size 0.001 \
    --regime-filter
```

Options:
- `--timeframe` / `-t` — Must match your downloaded data (default: `1h`)
- `--days` / `-d` — Limit to last N days of data
- `--cash` / `-c` — Starting capital in USDT (default: `$10,000`)
- `--risk-aversion` / `-g` — Risk aversion parameter (default: `0.1`)
- `--liquidity` / `-k` — Order book liquidity (default: `1.5`)
- `--order-size` / `-s` — Order size in BTC (default: `0.001`)
- `--fee` / `-f` — Maker fee as decimal (default: `0.001`)
- `--regime-filter` — Enable regime detection (recommended)
- `--quiet` / `-q` — Suppress output

### Step 3: Interpret Results

The backtest prints a summary like this:

```
Results
--------------------------------------------------
Final Equity:    $10,435.20
Total Return:    +4.35%
Max Drawdown:    1.82%

Risk Metrics
--------------------------------------------------
Sharpe Ratio:    2.14
Sortino Ratio:   3.01
Calmar Ratio:    2.39

Trade Statistics
--------------------------------------------------
Total Trades:    156
  Buy trades:    79
  Sell trades:   77
Win Rate:        54.5%
Profit Factor:   1.87

P&L Breakdown
--------------------------------------------------
Realized P&L:    $412.30
Unrealized P&L:  $22.90
Total Fees:      $31.20
Final Inventory: 0.000300 BTC
```

**What to look for:**

| Metric | Good | Concerning |
|---|---|---|
| Sharpe Ratio | > 1.5 | < 1.0 |
| Max Drawdown | < 5% | > 10% |
| Win Rate | > 50% | < 45% |
| Profit Factor | > 1.5 | < 1.0 |
| Total Return | Positive | Negative after fees |

If you enabled `--regime-filter`, you'll also see a regime breakdown showing how much time the market spent trending vs. ranging, and how many candles were skipped.

## Paper Trading

Paper trading runs the strategy against **live market data** on Bybit's testnet — real prices, fake money. This validates that the strategy works in real-time conditions without risking capital.

### Start Paper Trading

```bash
python scripts/run_paper_trader.py
```

On startup you'll see:
```
============================================================
AVELLANEDA-STOIKOV PAPER TRADER
============================================================
Mode:           TESTNET
Symbol:         BTCUSDT
Initial Capital: $1,000.00
Order Size:     0.003 BTC
Regime Filter:  ON
Quote Interval: 5.0s
============================================================
Waiting for market data...
Trader started. Press Ctrl+C to stop.
```

The bot will log quote updates and fills:
```
[2026-02-09 12:00:05] Quotes updated: Bid $95,412.30 | Ask $95,798.70 | Spread 40.5bps
[2026-02-09 12:00:35] FILL: Buy 0.003 @ $95,412.30
```

### Stop Paper Trading

Press `Ctrl+C` to gracefully stop. The bot cancels all open orders and prints a session summary:

```
============================================================
SESSION SUMMARY
============================================================
Final Price:     $95,600.00
Final Inventory: 0.003000 BTC
Final Cash:      $713.76
Total P&L:       $0.53
Total Trades:    4
Errors:          0
============================================================
```

### What to Monitor

- **Spread in basis points (bps)** — Should stay between 40-300 bps. Too tight means fees eat profits; too wide means fewer fills.
- **Inventory buildup** — The bot should oscillate around zero inventory. Persistent one-sided inventory means the market is trending and the regime filter should be kicking in.
- **Fill rate** — You should see both buy and sell fills. If only one side fills, spreads may be asymmetric.
- **Errors** — Any WebSocket disconnects or API errors. Occasional reconnects are normal; persistent errors need investigation.

### How Long to Paper Trade

Run paper trading for **at least 1-2 weeks** across different market conditions. The strategy performs best in ranging markets, so you want to observe how it handles both trending and sideways periods. Look for:

- Consistent small profits in ranging periods
- Successful pausing during strong trends (regime filter active)
- Stable inventory management (not accumulating a large directional position)
- No errors or crashes over extended periods

## Going Live

**Only transition to live trading after successful paper trading results.**

### Checklist Before Going Live

1. Paper traded for at least 2 weeks with positive results
2. Observed the bot in both trending and ranging markets
3. Comfortable with the maximum drawdown seen in paper trading
4. Bybit mainnet account funded and verified
5. Created mainnet API keys with trading permissions

### Setting Up for Live Trading

1. Create a new set of API keys on [bybit.com](https://www.bybit.com) (mainnet, not testnet)
2. Update your `.env` with mainnet keys:
   ```bash
   BYBIT_API_KEY=your-mainnet-api-key
   BYBIT_API_SECRET=your-mainnet-api-secret
   ```
3. In the `LiveTrader` initialization (in your run script), change `testnet=False`:
   ```python
   trader = LiveTrader(
       api_key=api_key,
       api_secret=api_secret,
       testnet=False,  # MAINNET
       ...
   )
   ```

### Risk Management Rules

- **Start small** — Begin with $500-$1,000 and `order_size=0.001` BTC. Scale up only after weeks of consistent profitability.
- **Never risk more than you can afford to lose** — This is algorithmic trading with real market risk.
- **Monitor actively at first** — Don't walk away from a live bot on day one. Watch it for several sessions.
- **Set the regime filter to ON** — The strategy loses money in strong trends. The regime filter is your kill switch for adverse conditions.
- **Check inventory** — If the bot accumulates a large directional position, something may be wrong. Stop and investigate.
- **Have a manual kill switch** — Know how to cancel all orders and stop the bot immediately (`Ctrl+C` sends a graceful shutdown that cancels open orders).

### Expected Performance

Based on backtests and the optimized configuration:

| Condition | Expected Monthly Return | Active Trading Time |
|---|---|---|
| Ranging market (ADX < 25) | 5-15% | ~8 days/month |
| Trending market (ADX > 25) | 0% (paused) | Bot skips these periods |
| Overall (blended) | 2-5% | ~26% of the time |

These are estimates, not guarantees. Past backtest performance does not predict future results.

## Understanding the Strategy

### The Avellaneda-Stoikov Model

The A-S model is a market-making framework that calculates where to place buy and sell limit orders.

**Reservation Price** — The market maker's "true" valuation, adjusted for inventory risk:

```
r = S - q * γ * σ² * (T - t)
```

- `S` = current mid price
- `q` = current inventory (positive = long)
- `γ` = risk aversion
- `σ` = volatility
- `T - t` = time remaining in session

When you're long, the reservation price drops (encouraging sells to reduce inventory). When short, it rises (encouraging buys).

**Optimal Spread** — How wide to quote around the reservation price:

```
δ = γ * σ² * (T - t) + (2/γ) * ln(1 + γ/κ)
```

- `κ` = order book liquidity parameter

Higher volatility and higher risk aversion widen the spread. Denser order books (higher κ) tighten it.

**Final quotes:**
- Bid = reservation price - spread/2
- Ask = reservation price + spread/2

### Regime Detection

The bot uses ADX (Average Directional Index) to classify the market:

- **ADX < 25** → Ranging market → Full trading
- **ADX 25-37.5** → Mild trend → Reduced position sizes
- **ADX > 37.5** → Strong trend → Trading paused

This is critical because market making earns the spread in sideways markets but suffers inventory losses in trends.

## Key Files

```
strategies/avellaneda_stoikov/
├── model.py              # Core A-S model (reservation price, optimal spread)
├── simulator.py          # Backtesting engine
├── live_trader.py        # Paper/live trading with Bybit
├── bybit_client.py       # Bybit REST + WebSocket client
├── order_manager.py      # Order tracking and inventory management
├── risk_manager.py       # Position sizing and stop losses
├── regime.py             # ADX-based regime detection
├── metrics.py            # Performance metrics (Sharpe, drawdown, etc.)
├── config.py             # Base configuration
└── config_optimized.py   # Optimized parameters from backtesting

scripts/
├── download_data.py      # Download historical OHLCV data
├── run_as_backtest.py    # Run strategy backtests
└── run_paper_trader.py   # Start paper trading

config/
└── config.json           # Exchange configuration

data/                     # Historical data (gitignored)
```

## Troubleshooting

### "Missing API credentials"

```
ERROR: Missing API credentials
```

Your `.env` file is missing or doesn't contain `BYBIT_API_KEY` and `BYBIT_API_SECRET`. Make sure the `.env` file is in the project root directory (same level as `requirements.txt`).

### "Data file not found"

```
Data file not found: data/btcusdt_1h.csv
```

You need to download historical data first:
```bash
python scripts/download_data.py --timeframe 1h --days 365
```

### TA-Lib Installation Errors

```
ERROR: Could not find ta-lib library
```

The TA-Lib C library isn't installed. See [Installing TA-Lib](#installing-ta-lib) above. The Python `ta-lib` package is a wrapper that requires the underlying C library.

### WebSocket Disconnects

```
WebSocket error: Connection closed unexpectedly
WebSocket closed: 1006 - connection was closed uncleanly
```

Occasional disconnects are normal — the bot will attempt to reconnect. If persistent:
- Check your internet connection
- Verify API keys are correct and have the right permissions
- Bybit testnet occasionally has downtime — check [Bybit status](https://status.bybit.com)

### "API Error: Invalid API key"

Double-check that:
- You're using **testnet** keys with the paper trader (testnet=True)
- You're using **mainnet** keys with live trading (testnet=False)
- The API key has **trading permissions** enabled
- The key hasn't expired or been revoked

### Import Errors

```
ModuleNotFoundError: No module named 'strategies'
```

Run scripts from the project root directory, not from within `scripts/`:
```bash
# Correct
python scripts/run_paper_trader.py

# Wrong
cd scripts && python run_paper_trader.py
```

### Running Tests

To verify the codebase is working:
```bash
pytest
```

This runs the full test suite (127 tests). All tests should pass before using the bot.
