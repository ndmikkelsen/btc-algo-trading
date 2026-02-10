"""BDD step implementations for market-making.feature.

Tests the Avellaneda-Stoikov market making model using pytest-bdd
with Gherkin scenarios defined in market-making.feature.
"""

import numpy as np
import pandas as pd
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from strategies.avellaneda_stoikov.model import AvellanedaStoikov

# Load all scenarios from the .feature file
scenarios(".")


# --- Shared context ---

class QuoteContext:
    """Mutable container for passing data between steps."""

    def __init__(self):
        self.mid_price = None
        self.model = None
        self.inventory = None
        self.volatility = None
        self.time_remaining = None
        self.reservation_price = None
        self.spread = None
        self.spread_2 = None
        self.bid = None
        self.ask = None
        self.neutral_bid = None
        self.neutral_ask = None
        self.inv_bid = None
        self.inv_ask = None
        self.prices = None
        self.calculated_volatility = None


@pytest.fixture
def ctx():
    return QuoteContext()


# --- Given steps ---

@given("a BTC mid price of 50000", target_fixture="ctx")
def given_mid_price(ctx):
    ctx.mid_price = 50000.0
    return ctx


@given("a default Avellaneda-Stoikov model")
def given_default_model(ctx):
    ctx.model = AvellanedaStoikov()


@given(parsers.parse("an inventory of {inventory:d}"))
def given_inventory(ctx, inventory):
    ctx.inventory = float(inventory)


@given(parsers.parse("a volatility of {volatility:g}"))
def given_volatility(ctx, volatility):
    ctx.volatility = volatility


@given(parsers.parse("a time remaining of {time_remaining:g}"))
def given_time_remaining(ctx, time_remaining):
    ctx.time_remaining = time_remaining


@given("a model with high risk aversion and liquidity")
def given_high_gamma_model(ctx):
    ctx.model = AvellanedaStoikov(
        risk_aversion=1.0,
        order_book_liquidity=10.0,
        max_spread=0.5,
    )


@given(parsers.parse("a series of {count:d} BTC prices"))
def given_price_series(ctx, count):
    np.random.seed(42)
    if count < 3:
        ctx.prices = pd.Series([50000.0] * count)
    else:
        returns = np.random.normal(0.0001, 0.02, count)
        ctx.prices = pd.Series(50000 * np.cumprod(1 + returns))


# --- When steps ---

@when("I calculate the reservation price")
def when_calculate_reservation_price(ctx):
    ctx.reservation_price = ctx.model.calculate_reservation_price(
        ctx.mid_price, ctx.inventory, ctx.volatility, ctx.time_remaining,
    )


@when("I calculate the optimal spread at this volatility")
def when_calculate_spread(ctx):
    ctx.spread = ctx.model.calculate_optimal_spread(
        ctx.volatility, ctx.time_remaining,
    )


@when(parsers.parse("I recalculate with a volatility of {volatility:g}"))
def when_recalculate_spread(ctx, volatility):
    ctx.spread_2 = ctx.model.calculate_optimal_spread(
        volatility, ctx.time_remaining,
    )


@when("I calculate the quotes")
def when_calculate_quotes(ctx):
    ctx.bid, ctx.ask = ctx.model.calculate_quotes(
        ctx.mid_price, ctx.inventory, ctx.volatility, ctx.time_remaining,
    )
    ctx.reservation_price = ctx.model.calculate_reservation_price(
        ctx.mid_price, ctx.inventory, ctx.volatility, ctx.time_remaining,
    )


@when(parsers.parse("I calculate quotes with inventory {inventory:d}"))
def when_calculate_quotes_with_inventory(ctx, inventory):
    bid, ask = ctx.model.calculate_quotes(
        ctx.mid_price, float(inventory), ctx.volatility, ctx.time_remaining,
    )
    if inventory == 0:
        ctx.neutral_bid = bid
        ctx.neutral_ask = ask
    else:
        ctx.inv_bid = bid
        ctx.inv_ask = ask


@when("I calculate the volatility")
def when_calculate_volatility(ctx):
    ctx.calculated_volatility = ctx.model.calculate_volatility(ctx.prices)


# --- Then steps ---

@then("the reservation price should equal the mid price")
def then_reservation_equals_mid(ctx):
    assert ctx.reservation_price == pytest.approx(ctx.mid_price, rel=1e-9)


@then("the reservation price should be below the mid price")
def then_reservation_below_mid(ctx):
    assert ctx.reservation_price < ctx.mid_price


@then("the reservation price should be above the mid price")
def then_reservation_above_mid(ctx):
    assert ctx.reservation_price > ctx.mid_price


@then("the second spread should be wider than the first")
def then_second_spread_wider(ctx):
    assert ctx.spread_2 > ctx.spread


@then("the spread should be at least the minimum spread")
def then_spread_at_least_minimum(ctx):
    assert ctx.spread >= ctx.model.min_spread


@then("the spread should be at most the maximum spread")
def then_spread_at_most_maximum(ctx):
    assert ctx.spread <= ctx.model.max_spread


@then("the bid should be below the ask")
def then_bid_below_ask(ctx):
    assert ctx.bid < ctx.ask


@then("the bid should be below the reservation price")
def then_bid_below_reservation(ctx):
    assert ctx.bid < ctx.reservation_price


@then("the ask should be above the reservation price")
def then_ask_above_reservation(ctx):
    assert ctx.ask > ctx.reservation_price


@then("the long-inventory bid should be lower than the neutral bid")
def then_long_bid_lower(ctx):
    assert ctx.inv_bid < ctx.neutral_bid


@then("the long-inventory ask should be lower than the neutral ask")
def then_long_ask_lower(ctx):
    assert ctx.inv_ask < ctx.neutral_ask


@then("the short-inventory bid should be higher than the neutral bid")
def then_short_bid_higher(ctx):
    assert ctx.inv_bid > ctx.neutral_bid


@then("the short-inventory ask should be higher than the neutral ask")
def then_short_ask_higher(ctx):
    assert ctx.inv_ask > ctx.neutral_ask


@then("the volatility should be a positive number")
def then_volatility_positive(ctx):
    assert ctx.calculated_volatility > 0


@then(parsers.parse("the volatility should be the default {default:g}"))
def then_volatility_default(ctx, default):
    assert ctx.calculated_volatility == pytest.approx(default)
