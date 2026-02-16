# Avellaneda-Stoikov Strategy Audit Report

**Date**: 2026-02-09
**Auditor**: Strategy Audit Agent
**Scope**: Full code audit of A-S market making strategy, backtester, and supporting infrastructure
**Verdict**: **NOT READY FOR LIVE TRADING** - Critical issues must be resolved first

---

## Executive Summary

This audit examined the Avellaneda-Stoikov market making implementation across 12 source files and 6 test files. The strategy has a sound theoretical foundation but contains **multiple critical flaws** that would cause live trading performance to diverge significantly from backtest results. The backtester systematically overstates profitability through unrealistic fill assumptions, look-ahead bias, and missing costs. The "optimized" parameters show signs of overfitting. **Trading real money with this code would very likely result in losses.**

**Critical issue count**: 5
**High-risk issue count**: 7
**Medium-risk issue count**: 6
**Low-risk issue count**: 4

---

## 1. Critical Issues (MUST FIX before any real trading)

### C1: Look-Ahead Bias in Fill Simulation
**File**: `simulator.py:161-205` (`check_fills`)
**Severity**: CRITICAL

The simulator uses the full candle's high and low to determine fills:

```python
if order.side == OrderSide.BUY:
    if low <= order.price:
        filled = True
```

**Problem**: This checks fills against the entire candle range *before* the price is actually observed at the close. In the `step()` method (line 296-297), fills are checked BEFORE updating the price state:

```python
fills = self.check_fills(high=high, low=low)  # Line 297
self.update_price(close, high, low, timestamp)  # Line 300
```

This means orders placed in the *previous* candle are evaluated against the *current* candle's full range. While this seems reasonable on the surface, there's a subtle look-ahead: **both the bid and ask can fill in the same candle** (test confirms this at `test_simulator.py:119-133`). In reality, if the price hits your bid first, the subsequent price action within that candle may not reach your ask (and vice versa). The simulator treats the candle as if all price points within it are simultaneously achievable.

**Impact**: Overstates fill rate by 20-40%. In a market making strategy, getting both sides filled in the same candle is the dream scenario - the backtest assumes it happens every time the range covers both quotes, which is wildly optimistic.

**Fix**:
- Use open-to-high-to-low-to-close sequencing (or random permutation) within each candle
- Or conservatively: if both bid and ask are within the candle range, only fill one side (randomly or based on open direction)
- Best: move to tick-level or at minimum sub-candle simulation

### C2: Unrealistic Fill Assumptions - No Slippage, No Queue Priority
**File**: `simulator.py:176-183`
**Severity**: CRITICAL

```python
fill_price = order.price  # Assume fill at limit price
```

**Problems**:
1. **No slippage**: Every fill occurs at the exact limit price. In reality, especially for BTC during volatile periods, you'll often get partial fills or worse prices.
2. **No queue priority**: If the price touches your level, you're assumed to be filled instantly. In reality, there are thousands of orders ahead of you in the queue. A price merely touching your level does NOT guarantee a fill.
3. **100% fill rate at touch**: The simulator fills orders the moment `low <= order.price`. Real exchanges require price to trade *through* your level (not just touch it) for a reliable fill at the back of the queue.

**Impact**: This is probably the single largest source of false positivity. A realistic fill model would reduce the number of filled orders by 50-80%, destroying the strategy's apparent profitability. Market makers at the back of the queue on major exchanges get filled on maybe 10-30% of limit touches.

**Fix**:
- Implement a fill probability model: `P(fill) = f(distance_through_level, volume, queue_position)`
- At minimum, require the price to trade *through* the limit level by some amount (e.g., 1 tick) before filling
- Add random slippage based on order size relative to typical volume
- Model partial fills

### C3: Reservation Price Formula Incorrectly Applied
**File**: `model.py:127-132`
**Severity**: CRITICAL

The A-S paper's reservation price formula is:
```
r = S - q * gamma * sigma^2 * (T - t)
```

The code implements:
```python
adjustment = inventory * self.risk_aversion * variance * time_remaining
reservation_price = mid_price - (mid_price * adjustment)  # Line 131
```

**Problem**: The code multiplies the adjustment by `mid_price`, making it: `r = S - S * q * gamma * sigma^2 * (T-t)` = `S * (1 - q * gamma * sigma^2 * (T-t))`. This is a **percentage-based** adjustment rather than the paper's **absolute** adjustment.

For the original formula, if S = 100,000, q = 1, gamma = 0.1, sigma = 0.02, T-t = 0.5:
- **Paper**: r = 100,000 - 1 * 0.1 * 0.0004 * 0.5 = 100,000 - 0.00002 = ~100,000 (tiny adjustment in absolute terms)
- **Code**: r = 100,000 * (1 - 0.00002) = 100,000 - 2 = 99,998

The code's version gives a much larger adjustment for high-priced assets like BTC. While this might be intentionally adapted for crypto, it's a deviation from the original paper and the parameters are no longer interpretable in the paper's framework. This means **all parameter tuning based on the original paper's guidance is invalid**.

**Impact**: The model doesn't behave as the A-S paper describes. Parameter sensitivity is different. The "optimized" parameters may only work because of this accidental scaling.

**Fix**: Either:
1. Use the paper's exact formula: `reservation_price = mid_price - adjustment` (and re-tune all parameters)
2. Explicitly document this as a modified formula and ensure parameters are tuned for this specific version

### C4: Spread Formula Also Incorrectly Applied
**File**: `model.py:200-202`
**Severity**: CRITICAL

```python
half_spread = (mid_price * spread) / 2
bid_price = reservation_price - half_spread
ask_price = reservation_price + half_spread
```

The `spread` from `calculate_optimal_spread()` is already a decimal (e.g., 0.001 for 0.1%). Then it's multiplied by `mid_price` to get the dollar half-spread. But the `calculate_optimal_spread()` function returns a value in the *same units as the formula* (raw sigma^2 terms), which are not inherently percentages.

Looking at the formula: `delta = gamma * sigma^2 * (T-t) + (2/gamma) * ln(1 + gamma/kappa)`

If sigma is 0.02 (2%), then sigma^2 = 0.0004. With gamma=0.1, kappa=1.5, T-t=0.5:
- `inventory_term = 0.1 * 0.0004 * 0.5 = 0.00002`
- `adverse_selection_term = (2/0.1) * ln(1 + 0.1/1.5) = 20 * ln(1.0667) = 20 * 0.0645 = 1.29`
- `spread = 1.29` (clamped to MAX_SPREAD = 0.05)

The adverse selection term can produce values >1.0, which would be >100% spread when multiplied by mid_price. This is why the clamping at MAX_SPREAD is doing all the heavy lifting. **The formula output is not naturally in percentage/decimal form** - it's in the paper's original units which need to be interpreted differently for different asset price scales.

**Impact**: The actual spread is essentially always clamped to MIN_SPREAD or MAX_SPREAD, meaning the A-S model's sophisticated spread optimization is completely bypassed. You're running a fixed-spread strategy, not an A-S strategy.

**Fix**: The formulas need to be properly scaled for the BTC price level, or the parameters need to be in units that produce sensible spreads before clamping.

### C5: No Stop-Loss in Backtester
**File**: `simulator.py` (entire file)
**Severity**: CRITICAL

The backtester has NO stop-loss mechanism. The `risk_manager.py` has stop-loss calculation functions, but they are **never called** from the simulator or backtest runner. The `live_trader.py` also doesn't implement stop-losses.

**Problem**: Without stop-losses, the strategy can accumulate unlimited inventory in a trending market. Even with the regime filter, there's a window where:
1. ADX hasn't detected the trend yet (lagging indicator)
2. The strategy has already accumulated inventory on the wrong side
3. The position keeps losing until the regime filter finally kicks in

The backtest results don't account for this tail risk. A single black swan event (flash crash, exchange outage during trend) could wipe out months of profits.

**Impact**: Backtest results appear smoother and more profitable than reality. The max drawdown figure understates true risk dramatically.

**Fix**: Implement stop-losses in the simulator that match what will be used live. Re-run backtests with stop-losses active.

---

## 2. High-Risk Issues (likely to cause significant performance divergence)

### H1: FIFO Win Rate Calculation is Fundamentally Flawed
**File**: `metrics.py:136-164`
**Severity**: HIGH

```python
buys = [t for t in trades if t['side'] == 'buy']
sells = [t for t in trades if t['side'] == 'sell']
# Match buys with sells (FIFO)
for i in range(total):
    buy_price = buys[i]['price']
    sell_price = sells[i]['price']
```

**Problem**: This assumes the i-th buy matches the i-th sell. In market making, fills are interleaved unpredictably. Consider:
- Buy at $100k, Buy at $99k, Sell at $99.5k, Sell at $100.5k
- FIFO matching: ($100k buy, $99.5k sell) = LOSS, ($99k buy, $100.5k sell) = WIN → 50% win rate
- Actual result: You made $1k net profit on two round trips

The FIFO matching doesn't account for partial inventory, quantity mismatches, or the actual temporal order of fills. It also ignores fees entirely.

**Impact**: Win rate and profit factor metrics are unreliable. You cannot trust these numbers for strategy evaluation.

**Fix**: Track round trips properly by maintaining a running inventory and matching fills based on actual position changes, including fees.

### H2: Sharpe Ratio Annualization Uses Wrong Period Count
**File**: `metrics.py:24-53`
**Severity**: HIGH

```python
periods_per_year: int = 8760,  # Hourly data
```

**Problem**: The strategy doesn't trade every hour. With the regime filter, it skips trending periods (~74% of the time per `config_optimized.py:128`). If the strategy only trades 26% of hours, the effective number of trading periods is ~2278/year, not 8760. Using 8760 inflates the annualized Sharpe ratio by `sqrt(8760/2278) ≈ 1.96x`.

Additionally, during non-trading periods, the equity changes due to mark-to-market of held inventory but no new trades are placed. These "zero-trade" periods have different return characteristics than active trading periods, violating the i.i.d. assumption of Sharpe annualization.

**Impact**: Reported Sharpe ratio is approximately 2x too high. A reported Sharpe of 2.0 might actually be ~1.0.

**Fix**: Calculate Sharpe only over active trading periods, or use a proper adjustment for inactive periods.

### H3: Equity Curve Includes Unrealized P&L Fluctuations
**File**: `simulator.py:377-379`
**Severity**: HIGH

```python
equity = self.order_manager.cash + (
    self.order_manager.inventory * row['close']
)
```

**Problem**: Equity includes mark-to-market of inventory. During periods where the strategy holds inventory (which can be prolonged if the regime filter pauses trading mid-position), equity fluctuates with BTC price. This makes the Sharpe ratio reflect BTC price volatility, not strategy alpha.

**Impact**: Performance metrics are contaminated by directional BTC exposure. A rising BTC market makes the strategy look better than it is; a falling market makes it look worse.

**Fix**: Track realized P&L separately and calculate Sharpe from realized returns only, or hedge the inventory exposure.

### H4: Fee Model is Optimistic
**File**: `config.py:79-82`, `order_manager.py:237-239`
**Severity**: HIGH

```python
MAKER_FEE = 0.001  # 0.1%
TAKER_FEE = 0.001  # 0.1%
```

**Problems**:
1. Bybit's current maker fee for VIP 0 is 0.1%, but this is the *best case*. During high-volume periods, you may get bumped to taker if your order gets filled before it rests (which happens often with aggressive quoting).
2. Fee is applied as simple `trade_value * maker_fee` but doesn't account for the bid-ask spread cost of entering/exiting positions during emergency liquidations.
3. The MIN_SPREAD of 0.4% in optimized config means each round-trip captures 0.4% gross, minus 0.2% in fees = 0.2% net. Any increase in effective fees (to 0.15% maker) would cut profit by 50%.

**Impact**: Thin margins mean fee sensitivity is extreme. A 0.05% increase in effective fees wipes out half the profits.

### H5: Both Sides Filling in Same Candle (Double-Fill Bias)
**File**: `simulator.py:161-205`
**Severity**: HIGH

The test `test_both_sides_can_fill_in_volatile_candle` explicitly verifies that both bid and ask fill in a single candle. This is a feature, not a bug, from the code's perspective - but it's a massive source of false profitability.

**Problem**: When both sides fill in the same candle, the strategy captures the full spread with zero inventory risk. This is the best possible outcome for a market maker, and the simulator assumes it happens every time the candle range covers both quotes. In reality:
- You'd need to be filled on the bid, then the ask (or vice versa) within the same candle
- Queue priority means you're unlikely to be at the front on both sides
- If one side fills, the price has moved, making the other side less likely to fill

**Impact**: Each double-fill is pure profit equal to the spread. If this happens on, say, 30% of candles where range covers both quotes, the backtest overestimates profit significantly.

### H6: Time Remaining Resets Incorrectly
**File**: `simulator.py:355-363`
**Severity**: HIGH

```python
if hasattr(timestamp, 'hour'):
    hour = timestamp.hour
    minute = getattr(timestamp, 'minute', 0)
    time_elapsed = (hour * 3600) + (minute * 60)
```

**Problem**: Time elapsed is calculated from midnight, resetting every day. But the A-S model uses time_remaining as the fraction of the *trading session* remaining. Since crypto markets are 24/7, this creates a daily cycle where:
- At midnight: time_remaining = 1.0 (full session)
- At noon: time_remaining = 0.5 (half session)
- At 23:59: time_remaining ≈ 0.0 (session ending)

This means spreads widen at midnight and narrow toward end of day - an artificial pattern. The live trader handles this differently: `time_remaining = 0.5` (hardcoded constant, line 235), creating a **live vs backtest discrepancy**.

**Impact**: Backtest results reflect an artificial daily cycle in spread behavior that won't exist in live trading.

### H7: Overfitting Risk in "Optimized" Parameters
**File**: `config_optimized.py`
**Severity**: HIGH

The optimized config claims "11.39% return in March 2025 test period" based on specific parameters. There's no evidence of:
1. Walk-forward validation
2. Out-of-sample testing
3. Parameter stability analysis
4. Multiple time period testing

The parameters (gamma=0.1, kappa=2.5, vol_window=20, MIN_SPREAD=0.004) were likely found by testing on the same data used to report results.

**Impact**: Parameters may be overfit to a specific month's BTC price action. Expected live performance is likely much worse than the 11.39% reported.

---

## 3. Medium-Risk Issues (should fix but not blocking)

### M1: ADX Implementation Differs from Standard
**File**: `regime.py:62-112`
**Severity**: MEDIUM

The ADX calculation uses EWM (exponential weighted moving average) instead of Wilder's smoothing method (which uses a different alpha). Standard ADX uses `alpha = 1/period` for Wilder's smoothing, while EWM uses `alpha = 2/(span+1)`.

**Impact**: ADX values will differ from standard implementations (TA-Lib, TradingView). Threshold of 25 was calibrated for standard ADX and may not be appropriate for this EWM-based version.

### M2: Volatility Window Too Small
**File**: `config_optimized.py:40`
**Severity**: MEDIUM

`VOLATILITY_WINDOW = 20` with hourly data = 20 hours of lookback. BTC volatility can change dramatically in 20 hours.

**Impact**: The model reacts too slowly to volatility regime changes, and too fast to temporary spikes. Consider using multiple timeframes or a larger window (50-100 periods).

### M3: Cost Basis Tracking Edge Case in Long-to-Short Transition
**File**: `order_manager.py:281-303`
**Severity**: MEDIUM

```python
if prev_inventory > 1e-10:  # Had a long position before sell
    # ...
    if quantity > prev_inventory:
        short_quantity = quantity - prev_inventory
        self._total_cost_basis = -short_quantity * price
```

The transition from long to short in a single fill is handled, but:
- Uses `1e-10` threshold which could miss very small positions
- The realized P&L calculation during transition only accounts for the long-closing portion, not the short-opening portion correctly
- `_total_cost_basis` can become negative (for short positions), making `average_entry_price` property potentially return negative values or divide-by-zero when inventory passes through zero

### M4: Live Trader Fill Tracking is Brittle
**File**: `live_trader.py:314-339`
**Severity**: MEDIUM

```python
orders = self.client.get_order_history(self.symbol, limit=10)
for order in orders:
    if order.get("orderStatus") == "Filled":
```

**Problems**:
- No deduplication: if the same filled order appears in consecutive polls, it's counted twice
- `limit=10` could miss fills during high-activity periods
- No reconciliation between local state and exchange state

### M5: Cash Check Doesn't Account for Pending Orders
**File**: `order_manager.py:149-152`
**Severity**: MEDIUM

```python
required_cash = price * quantity
if required_cash > self.cash:
    return None
```

Cash check doesn't consider cash reserved for existing open buy orders. This could lead to overcommitting cash - if you have $10k and place two buy orders each for $6k, the first succeeds and the second fails the check only because the first hasn't filled yet. But if both filled, you'd need $12k.

### M6: Regime Detection Operates on Growing Arrays
**File**: `simulator.py:128-131`
**Severity**: MEDIUM

```python
high = pd.Series(self.high_history)
low = pd.Series(self.low_history)
close = pd.Series(self.close_history)
```

These arrays grow unbounded during backtest, and a new `pd.Series` is created from the full history every step. For a 1-year hourly backtest (8760 candles), by the end you're creating 3 Series of length 8760 on every step, plus running the full ADX calculation on all of them.

**Impact**: Performance degrades quadratically. Also, the ADX is calculated on the entire history, not just the last N periods, which means early data has a lingering (but diminishing) effect.

---

## 4. Low-Risk Issues (nice to have)

### L1: Trade History Timestamp Uses Local Time
**File**: `order_manager.py:258`
```python
'timestamp': datetime.now(),
```
Uses local system time, not the candle timestamp. In backtesting, all trades appear to happen "now" rather than at historical times.

### L2: HFT Config MIN_SPREAD Below Fee Threshold
**File**: `config_hft.py:40`
```python
MIN_SPREAD = 0.0003  # 0.03%
```
Round-trip fees are 0.2% (2 x 0.1% maker fee). A 0.03% minimum spread guarantees a loss on every trade.

### L3: Bybit Signature Generation May Be Incorrect
**File**: `bybit_client.py:60-70`

The signature concatenation includes `"5000"` (recv_window) but doesn't include the parameter body for POST requests correctly - it sorts parameters but for POST with JSON body, Bybit requires the raw JSON string in the signature, not sorted key-value pairs.

### L4: WebSocket Has No Reconnection Logic
**File**: `bybit_client.py:308-326`
No automatic reconnection on disconnect. In production, WebSocket disconnections happen regularly (every few hours). Without reconnection, the live trader would stop receiving data silently.

---

## 5. Live vs Backtest Discrepancy Summary

| Aspect | Backtester | Live Trader | Impact |
|--------|-----------|-------------|--------|
| Time remaining | Daily cycle (0→1→0) | Hardcoded 0.5 | Different spread behavior |
| Fill model | Instant at limit price | Exchange matching | Dramatically fewer fills live |
| Fill detection | Candle high/low | Exchange fill reports | Backtest overfills |
| Stop loss | None | None | Both at risk, but backtest hides it |
| Fee model | 0.1% maker only | Unknown effective rate | Fees may be higher live |
| Slippage | Zero | Real market impact | Backtest overstates profit |
| Latency | Zero | Network + processing | Stale quotes, missed fills |
| Queue position | Front of queue | Back of queue | Much lower fill rate live |
| Both sides fill | Always if range allows | Rarely both in same period | Major profit overstatement |
| Order tracking | Perfect | Polling-based, no dedup | State drift live |

---

## 6. Code Fix Recommendations

### Priority 1: Fix the fill model (C1 + C2)
```python
# In simulator.py check_fills():
# 1. Add fill probability based on volume and distance through level
# 2. Only allow one side to fill per candle
# 3. Add slippage model
def check_fills(self, high, low, volume=None):
    fills = []
    filled_one_side = False  # Prevent double fills

    for order_id, order in list(self.order_manager.open_orders.items()):
        if filled_one_side:
            break  # Conservative: only one fill per candle

        if order.side == OrderSide.BUY:
            if low < order.price:  # Strict less than (not <=)
                penetration = (order.price - low) / order.price
                fill_prob = min(1.0, penetration * 10)  # Scale by penetration
                if random.random() < fill_prob:
                    slippage = random.uniform(0, 0.0001) * order.price
                    fill_price = order.price - slippage  # Could be better than limit
                    # ... fill logic
                    filled_one_side = True
```

### Priority 2: Fix the A-S formula (C3 + C4)
Either use the paper's exact formulation (with absolute adjustments) or properly document and parameterize the percentage-based variant. Re-tune all parameters after the fix.

### Priority 3: Add stop-losses (C5)
```python
# In simulator.py step():
# Check inventory exposure and enforce stop-loss
if abs(self.order_manager.inventory) > 0:
    entry_price = self.order_manager.average_entry_price
    if self.order_manager.inventory > 0:  # Long
        if close < entry_price * (1 - STOP_LOSS_PCT):
            # Force close at market
            self._close_position_at_market(close)
```

### Priority 4: Fix metrics (H1 + H2)
- Implement proper round-trip tracking with inventory-aware matching
- Calculate Sharpe using only active trading period returns
- Add fee-adjusted metrics

### Priority 5: Walk-forward validation (H7)
- Split data into train/test periods
- Optimize parameters on training data only
- Report performance on out-of-sample test data
- Test across multiple market regimes

---

## 7. Testing Recommendations

### Missing Test Categories

1. **Stress tests**: Test with flash crash data (>5% moves in one candle), zero-volume periods, and extreme spreads
2. **Fee sensitivity tests**: Run backtests at 0.05%, 0.1%, 0.15%, and 0.2% fee levels to understand margin of safety
3. **Slippage sensitivity tests**: Add 0.01%, 0.02%, 0.05% slippage and measure performance impact
4. **Fill rate sensitivity**: Reduce fill rate to 50%, 30%, 10% of current and measure impact
5. **Parameter stability tests**: Perturb each parameter by +/-20% and ensure performance doesn't collapse
6. **Regime transition tests**: Specifically test behavior when market transitions from ranging to trending mid-position
7. **Inventory accumulation tests**: Test what happens when the strategy accumulates max inventory and market moves against it
8. **Multi-month tests**: Run on 6+ months of data across different market conditions
9. **Walk-forward tests**: Optimize on month N, test on month N+1, repeat
10. **Monte Carlo tests**: Randomize fill order within candles and measure performance distribution

### Specific Test Fixes

- `test_both_sides_can_fill_in_volatile_candle` should be marked as testing a known-bias behavior, not a feature
- Add tests for the cost basis long-to-short transition edge case with specific numeric assertions
- Add tests that verify the Sharpe ratio against a known analytical result
- Add integration tests that compare backtest results to expected P&L from manual calculation on 5-10 candles

---

## 8. Conclusion

The strategy implementation has foundational issues that would make any backtest results unreliable for predicting live performance. The three most impactful issues are:

1. **Fill model assumes perfect execution** (C1 + C2): This alone likely accounts for >80% of the reported profitability
2. **A-S formula is incorrectly implemented** (C3 + C4): The model isn't actually doing what the paper describes
3. **No stop-loss protection** (C5): Tail risk is unmanaged

**Recommendation**: Do not trade real money until at minimum C1-C5 are resolved and the strategy is re-validated with walk-forward testing. After fixes, expect the backtest to show dramatically worse results (possibly negative). If the strategy is still profitable after realistic fill modeling, it may have genuine edge. But the current results cannot be trusted.

The good news: the code is well-structured, well-tested for its current logic, and the infrastructure (exchange client, risk manager, regime detection) provides a solid foundation. The issues are fixable. But they must be fixed before capital is at risk.

---
---

# Live Paper Trading Audit — 2026-02-15

**Date**: 2026-02-15
**Scope**: Deep investigation into why the GLFT model fails to profit in live (dry-run) paper trading on Bybit Futures
**Data**: 4 paper trading sessions totaling ~12+ hours, 46 limit fills, 22 round-trips
**Team**: 4 specialized agents (researcher, model-auditor, log-analyst, fill-auditor)

---

## Executive Summary

After extensive paper trading on Bybit Futures (BTC/USDT:USDT), the strategy consistently loses money. Net realized PnL across all sessions: **-$0.29** over 22 round-trips. The strategy captures ~$0.01/RT in spread but loses ~$0.045/RT to adverse selection, netting **-$0.035 per round-trip**. Six fundamental issues explain the unprofitability.

---

## 1. The Six Root Causes

### RC1: Kappa (κ=10.0) is ~235× Too High
**Severity**: CRITICAL — Single biggest parameter error

The order book liquidity parameter κ controls the "adverse selection" term in the GLFT spread formula:

```
δ* = (1/κ)·ln(1+κ/γ) + √(e·σ²·γ/(2Aκ))
```

With κ=10.0, the `(1/κ)·ln(1+κ/γ)` term compresses to near-zero, producing spreads of ~5.4 bps (the minimum floor). Academic implementations and hftbacktest calibrations use κ≈0.03–0.05 for BTC, derived from fitting `λ(δ) = A·exp(-κδ)` to actual trade flow data.

**Impact**: Spreads are ~5× too tight. The model quotes inside the natural bid-ask spread, guaranteeing adverse selection on every fill.

**Evidence**: Every paper trading session showed 5.4 bps spreads (the minimum floor), meaning the model's spread calculation was always hitting MIN_SPREAD — the sophisticated GLFT optimization was completely bypassed.

### RC2: No Maker Rebate — Fee Structure is Backwards
**Severity**: CRITICAL — Structural viability issue

The strategy was originally designed around MEXC spot (0% maker fee). On Bybit Futures VIP0, the actual maker fee is **0.02%** (2 bps). This means:

- Every filled limit order **costs** 2 bps in fees
- A round-trip costs **4 bps** in fees
- With 5.4 bps gross spread, net capture is only **1.4 bps** before adverse selection

The hftbacktest research that inspired this implementation achieved Sharpe ~10 using a **-0.005% maker rebate** (negative fee = exchange pays you). That rebate provided ~1 bps/side of profit; without it, the strategy fundamentally changes from "capture spread + collect rebate" to "capture spread – pay fees".

**Impact**: The business model is inverted. Profitable A-S implementations on Bybit require either VIP3+ (maker rebate) or significantly wider spreads to absorb fee drag.

### RC3: Dynamic Gamma is Broken (VOLATILITY_REFERENCE 50× Too High)
**Severity**: HIGH — Phase 2 feature actively hurts performance

Dynamic gamma scales risk aversion based on realized volatility:

```python
VOLATILITY_REFERENCE = 0.005  # 0.5% — reference for gamma scaling
```

At 1s quote intervals, per-tick volatility is ~0.0001 (0.01%), not 0.005 (0.5%). Since realized vol is always far below the reference, the gamma multiplier bottoms out at `GAMMA_MIN_MULT=0.5`, **permanently halving gamma**.

**Perverse effect**: Lower gamma → tighter spreads → more fills → more adverse selection. During high volatility (when you want wider spreads for protection), gamma goes toward 1.0× (normal). During low volatility (safe to quote tight), gamma stays at 0.5× (too tight). This is exactly backwards.

### RC4: "Widening Ratchet" — Phase 2 Features Only Widen, Never Tighten
**Severity**: HIGH — Systematic spread inflation

Three Phase 2 features (displacement guard, asymmetric spreads, fill imbalance) all apply multiplicative widening:

| Feature | Multiplier | Direction |
|---------|-----------|-----------|
| Displacement guard | 1.0×–3.0× | Widen both sides |
| Asymmetric spreads | 1.2× | Widen unfavorable side |
| Fill imbalance | 1.3× | Widen imbalanced side |

None of these ever **tighten** below baseline. Combined, they can widen spreads up to 3.0 × 1.2 × 1.3 = **4.7×** baseline. Log analysis shows displacement guard firing 15+ times per session, asymmetric spreads toggling every 1–2 minutes. The net effect is quotes that are frequently too wide to fill, explaining the low fill rate (4 RT/hour vs needed 18 RT/hour).

### RC5: Paper Trading Fill Simulation is Fundamentally Flawed
**Severity**: HIGH — Results are unreliable in both directions

The `DryRunFuturesClient.check_fills()` has multiple compounding bugs:

1. **Uses last-traded price, not bid/ask**: Compares limit orders against the last trade price, not the current best bid/ask. A limit buy at $68,741 triggers when last trade ≤ $68,741, even if the best ask is $68,745.
2. **Fills at current price, not limit price**: When triggered, fills execute at `current_price` rather than the order's limit price. This creates phantom price improvement (or phantom slippage) that doesn't reflect reality.
3. **No queue position modeling**: Assumes front-of-queue execution. Real Bybit has thousands of orders ahead.
4. **1s polling misses touches**: A price that briefly touches the limit level between polls goes undetected.
5. **FILL_AGGRESSIVENESS has zero effect**: The config parameter exists but is never used in the futures paper trading path.

**Impact**: Biases partially cancel (too optimistic on some fills, too pessimistic on others), making PnL results unreliable as either optimistic or pessimistic estimates. The paper trading is essentially random noise around the true fill behavior.

### RC6: No Alpha Signal — Pure Spread Capture Doesn't Work at These Fees
**Severity**: MEDIUM — Strategic gap

The current implementation is a pure market-making strategy with no predictive signal. It relies entirely on capturing the bid-ask spread. At 4 bps round-trip fees, the strategy needs either:

- Significantly wider spreads (but then fills are too rare)
- A directional signal to reduce adverse selection (e.g., order book imbalance, trade flow prediction)
- Maker rebates to subsidize the spread capture

Without alpha, the strategy is a negative-expectation coin flip at current fee levels.

---

## 2. What the Strategy Gets Right

Despite the issues, several components are well-implemented:

1. **GLFT math is correct**: The core reservation price and optimal spread formulas are properly implemented (minor √e deviation is negligible)
2. **Inventory management works**: The soft/hard limit system, time-based decay, and loss threshold all function correctly
3. **Safety controls are sound**: Tick filter, displacement guard logic (if not the parameters), cooldown timers
4. **Infrastructure is solid**: Exchange client, SOCKS5 proxy, order management, PnL tracking (after fixes)
5. **Logging and monitoring**: Comprehensive session summaries, fill tracking, error reporting

---

## 3. Log Analysis: Quantified Performance

| Metric | Value |
|--------|-------|
| Total sessions | 4 (12+ hours) |
| Limit fills | 46 |
| Round-trips | 22 |
| Net realized PnL | -$0.29 |
| Gross spread capture | ~$0.01/RT |
| Adverse selection cost | ~$0.045/RT |
| Net per round-trip | -$0.035 |
| Fill rate | ~4 RT/hour |
| Break-even fill rate | ~18 RT/hour |
| Spread (observed) | 5.4 bps (always at minimum) |
| Inventory reductions | 2 (both at losses) |
| Revenue split | 38% spread capture, 62% directional exposure |

---

## 4. Ranked Recommendations

### Tier 1: Must Fix (Strategy is non-viable without these)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | **Calibrate κ from live order book** | Medium | Correct spreads from 5 bps → ~25-50 bps |
| 2 | **Switch to MEXC spot (0% maker)** or target Bybit VIP3+ | Low | Eliminate 4 bps/RT fee drag |
| 3 | **Fix VOLATILITY_REFERENCE** to match tick interval | Trivial | Fix dynamic gamma direction |
| 4 | **Fix fill simulation** to use bid/ask + limit prices | Medium | Make paper trading results trustworthy |

### Tier 2: Should Fix (Significant improvement expected)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 5 | Add spread **tightening** to Phase 2 features | Low | Break the widening ratchet |
| 6 | Add **order book imbalance** as alpha signal | Medium | Reduce adverse selection |
| 7 | Implement **live κ calibration** from trade flow | High | Adaptive spread sizing |
| 8 | Add **queue position modeling** to paper trading | Medium | Realistic fill expectations |

### Tier 3: Nice to Have (Polish and optimization)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 9 | Tune MOMENTUM_THRESHOLD for 1s intervals | Low | Better asymmetric behavior |
| 10 | Add fill-rate tracking metric | Low | Better performance monitoring |
| 11 | Implement partial fills in simulation | Medium | More realistic testing |
| 12 | Walk-forward parameter validation | High | Confidence in parameter stability |

---

## 5. Recommended Next Steps

1. **Quick wins** (can do now):
   - Fix VOLATILITY_REFERENCE to ~0.0001 for 1s ticks
   - Set κ=0.05 (literature value) as starting point
   - Add spread tightening to displacement guard (allow < 1.0× multiplier)

2. **Exchange decision** (strategic):
   - If staying on Bybit: Need VIP3+ for maker rebate, or accept wider spreads
   - If switching to MEXC: Re-enable spot mode, 0% maker fee makes strategy viable at tighter spreads

3. **Live κ calibration** (medium-term):
   - Collect trade-and-quote data for 24h
   - Fit λ(δ) = A·exp(-κδ) to observed fill rates at various distances
   - Use calibrated κ for spread calculation

4. **Alpha integration** (longer-term):
   - Add order book imbalance signal
   - Use trade flow momentum for directional bias
   - Consider microstructure features (trade size clustering, sweep detection)
