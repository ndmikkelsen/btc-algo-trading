"""BDD step implementations for mean-reversion-signals.feature.

Tests the MeanReversionBB model signal generation using pytest-bdd
with Gherkin scenarios defined in mean-reversion-signals.feature.
"""

import numpy as np
import pandas as pd
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from strategies.mean_reversion_bb.model import MeanReversionBB

# Load all scenarios
scenarios("trading/mean-reversion-signals.feature")


# ---------------------------------------------------------------------------
# Helpers: synthetic OHLCV generators
# ---------------------------------------------------------------------------
# Each generator is empirically calibrated to produce specific indicator
# conditions (RSI, BB position, VWAP deviation, squeeze state). The
# calibration values were verified against MeanReversionBB.calculate_signals.
# ---------------------------------------------------------------------------

def _make_ohlcv_from_close(
    close: np.ndarray,
    *,
    close_noise: float = 10.0,
    hl_noise: float = 50.0,
    seed: int = 99,
) -> pd.DataFrame:
    """Build valid OHLCV from a close-price array.

    OHLC relationships guaranteed: high >= max(open, close), low <= min(open, close).
    """
    n = len(close)
    rng = np.random.RandomState(seed)
    open_ = close + rng.normal(0, close_noise, n)
    high = np.maximum(open_, close) + np.abs(rng.normal(hl_noise, hl_noise * 0.4, n))
    low = np.minimum(open_, close) - np.abs(rng.normal(hl_noise, hl_noise * 0.4, n))
    volume = np.abs(rng.normal(1000, 200, n))
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}
    )


def _make_lower_bb_touch(oversold: bool = True) -> pd.DataFrame:
    """OHLCV where last candle breaches the lower Bollinger Band.

    Calibrated to produce:
      oversold=True:  signal=long, RSI<30, bb_pos<0, vwap_dev<0.02
      oversold=False: signal=none, RSI~38, bb_pos<0 (RSI blocks signal)
    """
    n = 200
    rng = np.random.RandomState(42)
    close = np.empty(n)

    if oversold:
        # Phase 1: 180 candles oscillating (establishes VWAP near 49200)
        for i in range(180):
            close[i] = 49200 + rng.normal(0, 200)
        # Phase 2: 19 small consistent drops (drives RSI below 30)
        base = close[179]
        for i in range(180, 199):
            close[i] = base - (i - 179) * 10
        # Phase 3: single big drop breaches lower BB
        close[199] = close[198] - 600
    else:
        # Single big drop at the end: below BB but RSI stays neutral (~38)
        for i in range(199):
            close[i] = 49200 + rng.normal(0, 200)
        close[199] = close[198] - 800

    return _make_ohlcv_from_close(close)


def _make_upper_bb_touch(overbought: bool = True) -> pd.DataFrame:
    """OHLCV where last candle breaches the upper Bollinger Band.

    Calibrated to produce:
      overbought=True:  signal=short, RSI>70, bb_pos>1, vwap_dev<0.02
      overbought=False: signal=none, RSI~63, bb_pos>1 (RSI blocks signal)
    """
    n = 200
    rng = np.random.RandomState(42)
    close = np.empty(n)

    if overbought:
        for i in range(180):
            close[i] = 50800 + rng.normal(0, 200)
        base = close[179]
        for i in range(180, 199):
            close[i] = base + (i - 179) * 10
        close[199] = close[198] + 500
    else:
        for i in range(199):
            close[i] = 50800 + rng.normal(0, 200)
        close[199] = close[198] + 800

    return _make_ohlcv_from_close(close)


def _make_squeeze_data() -> pd.DataFrame:
    """OHLCV in an active Bollinger Band squeeze.

    Tight close-to-close moves (BB narrows) with wide high-low range
    (ATR stays large, KC stays wide). BB inside KC = squeeze.

    Final candles decline to push RSI toward oversold and close near
    the (very narrow) lower BB.
    """
    n = 200
    rng = np.random.RandomState(42)
    close = np.empty(n)

    # Tight close oscillation (std ~3)
    for i in range(186):
        close[i] = 50000 + rng.normal(0, 3)

    # Small consistent drops for RSI oversold
    base = close[185]
    for i in range(186, 200):
        close[i] = base - (i - 185) * 2

    # Build OHLCV: tight closes but WIDE high-low (large ATR → KC >> BB)
    rng2 = np.random.RandomState(99)
    open_ = close + rng2.normal(0, 1, n)
    high = np.maximum(open_, close) + np.abs(rng2.normal(200, 50, n))
    low = np.minimum(open_, close) - np.abs(rng2.normal(200, 50, n))
    volume = np.abs(rng2.normal(1000, 200, n))
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}
    )


def _make_squeeze_then_expansion() -> pd.DataFrame:
    """OHLCV where squeeze ends, then price drops to lower BB.

    Phase 1 (120 candles): tight closes + wide H-L → squeeze active.
    Phase 2 (100 candles): large close noise + tight H-L → BB expands
      past KC, ending the squeeze. Oscillation around 49200.
    Phase 3 (30 candles): 29 consistent drops + 1 big drop → RSI < 30,
      close below lower BB, VWAP deviation < 2%.
    """
    n = 250
    rng = np.random.RandomState(42)
    close = np.empty(n)

    # Phase 1: tight squeeze
    for i in range(120):
        close[i] = 50000 + rng.normal(0, 3)

    # Phase 2: expansion (large close-to-close, VWAP establishes near 49200)
    for i in range(120, 220):
        close[i] = 49200 + rng.normal(0, 300)

    # Phase 3: 29 small drops + 1 big drop
    base = close[219]
    for i in range(220, 249):
        close[i] = base - (i - 219) * 20
    close[249] = close[248] - 500

    # Tight H-L for low ATR in expansion phase (so BB > KC → no squeeze)
    return _make_ohlcv_from_close(close, close_noise=10, hl_noise=30)


# ---------------------------------------------------------------------------
# Shared context
# ---------------------------------------------------------------------------

class SignalContext:
    """Mutable container for passing data between steps."""

    def __init__(self):
        self.model: MeanReversionBB | None = None
        self.ohlcv: pd.DataFrame | None = None
        self.signal: dict | None = None
        self.orders: list | None = None


@pytest.fixture
def ctx():
    return SignalContext()


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------

@given("a default MeanReversionBB model", target_fixture="ctx")
def given_default_mrbb(ctx):
    # Disable regime filter so BDD tests exercise signal logic
    # independent of ADX-based filtering (tested separately in unit tests)
    ctx.model = MeanReversionBB(bb_std_dev=2.0, use_regime_filter=False)
    return ctx


@given("OHLCV data where price drops to the lower Bollinger Band")
def given_lower_bb_data(ctx):
    ctx.ohlcv = _make_lower_bb_touch(oversold=True)


@given("the RSI is oversold")
def given_rsi_oversold(ctx):
    if ctx.ohlcv is None:
        ctx.ohlcv = _make_lower_bb_touch(oversold=True)


@given("the RSI is neutral")
def given_rsi_neutral(ctx):
    if ctx.ohlcv is not None and ctx.signal is None:
        last = ctx.ohlcv["close"].iloc[-1]
        mean_price = ctx.ohlcv["close"].iloc[:150].mean()
        if last < mean_price:
            ctx.ohlcv = _make_lower_bb_touch(oversold=False)
        else:
            ctx.ohlcv = _make_upper_bb_touch(overbought=False)


@given("the market is not in a squeeze")
def given_no_squeeze(ctx):
    pass  # Default data produces no squeeze


@given("OHLCV data where price rises to the upper Bollinger Band")
def given_upper_bb_data(ctx):
    ctx.ohlcv = _make_upper_bb_touch(overbought=True)


@given("the RSI is overbought")
def given_rsi_overbought(ctx):
    if ctx.ohlcv is None:
        ctx.ohlcv = _make_upper_bb_touch(overbought=True)


@given("OHLCV data with a volatility squeeze")
def given_squeeze_data(ctx):
    ctx.ohlcv = _make_squeeze_data()


@given("the price is at the lower Bollinger Band")
def given_price_at_lower_bb(ctx):
    pass  # Squeeze data already positions price near lower BB


@given("OHLCV data where a squeeze ends with expansion")
def given_squeeze_ends(ctx):
    ctx.ohlcv = _make_squeeze_then_expansion()


@given("the price drops to the lower Bollinger Band")
def given_price_drops_lower(ctx):
    pass  # Squeeze-then-expansion data already has final drop


@given(parsers.parse("ranging OHLCV data with {n:d} candles"))
def given_ranging_data(ctx, n):
    rng = np.random.RandomState(42)
    close = np.empty(n)
    close[0] = 50000.0
    for i in range(1, n):
        reversion = 0.05 * (50000 - close[i - 1])
        close[i] = close[i - 1] + reversion + rng.normal(0, 80)
    ctx.ohlcv = _make_ohlcv_from_close(close)


@given(parsers.parse('the signal is "{signal_name}"'))
def given_signal_is(ctx, signal_name):
    ctx.signal = {"signal": signal_name}


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when("I calculate signals")
def when_calculate_signals(ctx):
    df = ctx.ohlcv
    ctx.signal = ctx.model.calculate_signals(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        volume=df["volume"],
    )


@when(parsers.parse("I generate orders with equity {equity:d} and ATR {atr:d}"))
def when_generate_orders(ctx, equity, atr):
    if ctx.signal is None:
        df = ctx.ohlcv
        ctx.signal = ctx.model.calculate_signals(
            high=df["high"], low=df["low"],
            close=df["close"], volume=df["volume"],
        )
    current_price = float(ctx.ohlcv["close"].iloc[-1])
    ctx.orders = ctx.model.generate_orders(
        signal=ctx.signal,
        current_price=current_price,
        equity=float(equity),
        atr=float(atr),
    )


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------

@then(parsers.parse('the signal should be "{expected}"'))
def then_signal_is(ctx, expected):
    assert ctx.signal["signal"] == expected, (
        f"Expected signal '{expected}', got '{ctx.signal['signal']}'. "
        f"RSI={ctx.signal.get('rsi')}, bb_pos={ctx.signal.get('bb_position')}, "
        f"squeeze={ctx.signal.get('is_squeeze')}, "
        f"vwap_dev={ctx.signal.get('vwap_deviation')}"
    )


@then(parsers.parse("the RSI should be below {threshold:d}"))
def then_rsi_below(ctx, threshold):
    assert ctx.signal["rsi"] < threshold, (
        f"RSI {ctx.signal['rsi']:.1f} not below {threshold}"
    )


@then(parsers.parse("the RSI should be above {threshold:d}"))
def then_rsi_above(ctx, threshold):
    assert ctx.signal["rsi"] > threshold, (
        f"RSI {ctx.signal['rsi']:.1f} not above {threshold}"
    )


@then(parsers.parse("the BB position should be below {threshold:g}"))
def then_bb_below(ctx, threshold):
    assert ctx.signal["bb_position"] < threshold, (
        f"BB position {ctx.signal['bb_position']:.4f} not below {threshold}"
    )


@then(parsers.parse("the BB position should be above {threshold:g}"))
def then_bb_above(ctx, threshold):
    assert ctx.signal["bb_position"] > threshold, (
        f"BB position {ctx.signal['bb_position']:.4f} not above {threshold}"
    )


@then("the squeeze flag should be true")
def then_squeeze_true(ctx):
    assert ctx.signal["is_squeeze"] is True


@then("the squeeze flag should be false")
def then_squeeze_false(ctx):
    assert ctx.signal["is_squeeze"] is False


@then(parsers.parse("the BB position should be between {low:g} and {high:g}"))
def then_bb_between(ctx, low, high):
    pos = ctx.signal["bb_position"]
    assert low <= pos <= high, f"BB position {pos:.4f} not in [{low}, {high}]"


@then("the VWAP deviation should be a non-negative number")
def then_vwap_nonneg(ctx):
    assert ctx.signal["vwap_deviation"] >= 0


@then(parsers.parse("the bandwidth percentile should be between {low:g} and {high:g}"))
def then_bw_between(ctx, low, high):
    pct = ctx.signal["bandwidth_percentile"]
    assert low <= pct <= high, f"Bandwidth percentile {pct:.1f} not in [{low}, {high}]"


@then("an order should be generated")
def then_order_exists(ctx):
    assert ctx.orders and len(ctx.orders) > 0, "No orders generated"


@then("no orders should be generated")
def then_no_orders(ctx):
    assert ctx.orders is not None and len(ctx.orders) == 0


@then(parsers.parse('the order side should be "{side}"'))
def then_order_side(ctx, side):
    assert ctx.orders[0]["side"] == side


@then("the stop loss should be below the entry price")
def then_stop_below_entry(ctx):
    order = ctx.orders[0]
    assert order["stop_loss"] < order["entry_price"]


@then("the target should be above the entry price")
def then_target_above_entry(ctx):
    order = ctx.orders[0]
    assert order["target"] > order["entry_price"]
