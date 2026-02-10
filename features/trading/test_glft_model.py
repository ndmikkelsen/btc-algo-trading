"""BDD step implementations for glft-model.feature.

Tests the GLFT infinite-horizon market making model using pytest-bdd
with Gherkin scenarios defined in glft-model.feature.
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from strategies.avellaneda_stoikov.glft_model import GLFTModel

# Load all scenarios from the .feature file
scenarios("trading/glft-model.feature")


# --- Shared context ---

class GLFTContext:
    """Mutable container for passing data between GLFT steps."""

    def __init__(self):
        self.mid_price = None
        self.model = None
        self.inventory = None
        self.volatility = None
        self.spread = None
        self.spread_2 = None
        self.spread_t1 = None
        self.spread_t2 = None
        self.bid = None
        self.ask = None
        self.neutral_bid = None
        self.neutral_ask = None
        self.inv_bid = None
        self.inv_ask = None
        self.fill_rate_shallow = None
        self.fill_rate_deep = None


@pytest.fixture
def ctx():
    return GLFTContext()


# --- Given steps ---

@given("a BTC mid price of 100000", target_fixture="ctx")
def given_mid_price_100k(ctx):
    ctx.mid_price = 100000.0
    return ctx


@given("a default GLFT model")
def given_default_glft_model(ctx):
    ctx.model = GLFTModel()


@given(parsers.parse("a GLFT volatility of {volatility:g}"))
def given_glft_volatility(ctx, volatility):
    ctx.volatility = volatility


@given(parsers.parse("a GLFT inventory of {inventory:d}"))
def given_glft_inventory(ctx, inventory):
    ctx.inventory = float(inventory)


@given("a GLFT model with uncapped spread")
def given_glft_uncapped(ctx):
    ctx.model = GLFTModel(max_spread_dollar=1e12)


@given("a GLFT model with tight max spread")
def given_glft_tight_max(ctx):
    ctx.model = GLFTModel(max_spread_dollar=100.0)


# --- When steps ---

@when("I calculate the GLFT optimal spread")
def when_calculate_glft_spread(ctx):
    ctx.spread = ctx.model.calculate_optimal_spread(
        ctx.volatility, 0.5, mid_price=ctx.mid_price,
    )


@when(parsers.parse("I calculate the GLFT spread with time remaining {t:g}"))
def when_calculate_glft_spread_time(ctx, t):
    spread = ctx.model.calculate_optimal_spread(
        ctx.volatility, t, mid_price=ctx.mid_price,
    )
    if ctx.spread_t1 is None:
        ctx.spread_t1 = spread
    else:
        ctx.spread_t2 = spread


@when("I calculate the GLFT spread at low volatility")
def when_calculate_glft_spread_low_vol(ctx):
    ctx.spread = ctx.model.calculate_optimal_spread(
        ctx.volatility, 0.5, mid_price=ctx.mid_price,
    )


@when(parsers.parse("I recalculate the GLFT spread at volatility {volatility:g}"))
def when_recalculate_glft_spread(ctx, volatility):
    ctx.spread_2 = ctx.model.calculate_optimal_spread(
        volatility, 0.5, mid_price=ctx.mid_price,
    )


@when("I calculate the GLFT quotes")
def when_calculate_glft_quotes(ctx):
    inv = ctx.inventory if ctx.inventory is not None else 0
    ctx.bid, ctx.ask = ctx.model.calculate_quotes(
        ctx.mid_price, inv, ctx.volatility, 0.5,
    )


@when(parsers.parse("I calculate GLFT quotes with inventory {inventory:d}"))
def when_calculate_glft_quotes_inventory(ctx, inventory):
    bid, ask = ctx.model.calculate_quotes(
        ctx.mid_price, float(inventory), ctx.volatility, 0.5,
    )
    if inventory == 0:
        ctx.neutral_bid = bid
        ctx.neutral_ask = ask
    else:
        ctx.inv_bid = bid
        ctx.inv_ask = ask


@when(parsers.parse("I calculate the GLFT fill rate at depth {depth:g}"))
def when_calculate_fill_rate(ctx, depth):
    rate = ctx.model.fill_rate(depth)
    if ctx.fill_rate_shallow is None:
        ctx.fill_rate_shallow = rate
    else:
        ctx.fill_rate_deep = rate


# --- Then steps ---

@then("the GLFT spread should be positive")
def then_glft_spread_positive(ctx):
    assert ctx.spread > 0


@then("both GLFT spreads should be equal")
def then_glft_spreads_equal(ctx):
    assert ctx.spread_t1 == pytest.approx(ctx.spread_t2, rel=1e-12)


@then("the second GLFT spread should be wider")
def then_second_glft_spread_wider(ctx):
    assert ctx.spread_2 > ctx.spread


@then("the GLFT bid and ask should be symmetric around mid")
def then_glft_symmetric(ctx):
    bid_dist = ctx.mid_price - ctx.bid
    ask_dist = ctx.ask - ctx.mid_price
    assert bid_dist == pytest.approx(ask_dist, rel=1e-9)


@then("the long-inventory GLFT bid should be lower")
def then_long_glft_bid_lower(ctx):
    assert ctx.inv_bid < ctx.neutral_bid


@then("the long-inventory GLFT ask should be lower")
def then_long_glft_ask_lower(ctx):
    assert ctx.inv_ask < ctx.neutral_ask


@then("the short-inventory GLFT bid should be higher")
def then_short_glft_bid_higher(ctx):
    assert ctx.inv_bid > ctx.neutral_bid


@then("the short-inventory GLFT ask should be higher")
def then_short_glft_ask_higher(ctx):
    assert ctx.inv_ask > ctx.neutral_ask


@then("the deeper fill rate should be lower")
def then_deeper_fill_rate_lower(ctx):
    assert ctx.fill_rate_deep < ctx.fill_rate_shallow


@then("the GLFT dollar spread should be at least the minimum")
def then_glft_spread_at_least_min(ctx):
    dollar_spread = ctx.ask - ctx.bid
    assert dollar_spread >= ctx.model.min_spread_dollar - 1e-9


@then("the GLFT dollar spread should be at most the maximum")
def then_glft_spread_at_most_max(ctx):
    dollar_spread = ctx.ask - ctx.bid
    assert dollar_spread <= ctx.model.max_spread_dollar + 1e-9
