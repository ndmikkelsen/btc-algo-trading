"""BDD step implementations for fee-sensitivity.feature.

Tests the fee model and break-even economics using pytest-bdd
with Gherkin scenarios defined in fee-sensitivity.feature.
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from strategies.avellaneda_stoikov.fee_model import FeeModel, FeeTier
from strategies.avellaneda_stoikov.economics import BreakEvenCalculator

# Load scenarios from our specific feature file
scenarios("risk/fee-sensitivity.feature")


# --- Shared context ---

class FeeContext:
    """Mutable container for passing data between steps."""

    def __init__(self):
        self.fee_model = None
        self.calculator = None
        self.min_spread_pct = None
        self.min_spread_dollar = None
        self.report = None


@pytest.fixture
def fctx():
    return FeeContext()


# --- Given steps ---

TIER_MAP = {
    "Regular": FeeTier.REGULAR,
    "VIP1": FeeTier.VIP1,
    "VIP2": FeeTier.VIP2,
    "Market Maker": FeeTier.MARKET_MAKER,
}


@given(
    parsers.parse("the {tier_name} fee tier at {price:d} BTC price"),
    target_fixture="fctx",
)
def given_fee_tier(fctx, tier_name, price):
    tier = TIER_MAP[tier_name]
    fctx.fee_model = FeeModel(tier=tier)
    fctx.calculator = BreakEvenCalculator(
        fee_model=fctx.fee_model, reference_price=float(price)
    )
    return fctx


# --- When steps ---

@when("I calculate the minimum profitable spread")
def when_calc_min_spread(fctx):
    fctx.min_spread_pct = fctx.calculator.min_profitable_spread()
    fctx.min_spread_dollar = fctx.calculator.min_profitable_spread_dollar()


@when(parsers.parse("I generate an economics report with BBO of {bbo:g} dollars"))
def when_generate_report(fctx, bbo):
    fctx.report = fctx.calculator.generate_report(typical_bbo_dollar=bbo)


# --- Then steps ---

@then(parsers.parse("the minimum spread should be {pct:g} percent"))
def then_min_spread_pct(fctx, pct):
    expected = pct / 100.0  # convert "0.04 percent" -> 0.0004
    assert fctx.min_spread_pct == pytest.approx(expected, rel=1e-6)


@then(parsers.parse("the minimum spread in dollars should be {dollars:g}"))
def then_min_spread_dollar(fctx, dollars):
    assert fctx.min_spread_dollar == pytest.approx(dollars, rel=1e-6)


@then("the strategy should be viable at typical BBO")
def then_viable(fctx):
    if fctx.report is not None:
        assert fctx.report.viable is True
    else:
        # When called after min_spread calc (no report), check dollar spread
        assert fctx.min_spread_dollar <= 0.30  # typical BBO


@then("the strategy should not be viable at typical BBO")
def then_not_viable(fctx):
    assert fctx.report.viable is False


@then(parsers.parse("the spread gap should be {gap:g} dollars"))
def then_spread_gap(fctx, gap):
    assert fctx.report.spread_gap_dollar == pytest.approx(gap, rel=1e-6)
