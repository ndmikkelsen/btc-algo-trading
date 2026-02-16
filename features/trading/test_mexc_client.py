"""BDD step implementations for mexc-client.feature."""

import pytest
from unittest.mock import MagicMock
from pytest_bdd import scenarios, given, when, then, parsers

from strategies.avellaneda_stoikov.mexc_client import (
    MexcClient,
    MexcConfig,
    DryRunClient,
    MexcMarketPoller,
)
from strategies.avellaneda_stoikov.orderbook import OrderBookCollector

scenarios("trading/mexc-client.feature")


# --- Shared context ---

class MexcContext:
    """Mutable container for passing data between steps."""

    def __init__(self):
        self.client = None
        self.dry_client = None
        self.poller = None
        self.collector = None
        self.order_result = None
        self.fills = None


@pytest.fixture
def mctx():
    return MexcContext()


# --- Given steps ---

@given(
    "a MEXC client configured for BTCUSDT",
    target_fixture="mctx",
)
def given_mexc_client(mctx):
    config = MexcConfig(api_key="test", api_secret="test")
    mctx.client = MexcClient(config)
    mctx.client.exchange = MagicMock()
    mctx.client.exchange.create_order.return_value = {
        'id': 'order-bdd-001',
        'status': 'open',
    }
    return mctx


@given(
    parsers.parse("a dry-run client with {usdt:d} USDT"),
    target_fixture="mctx",
)
def given_dry_run_client(mctx, usdt):
    config = MexcConfig(api_key="test", api_secret="test")
    mctx.dry_client = DryRunClient(
        config, initial_usdt=float(usdt), initial_btc=0.0,
    )
    mctx.dry_client._market_client = MagicMock()
    return mctx


@given(
    parsers.parse("a dry-run client with current price at {price:d}"),
    target_fixture="mctx",
)
def given_dry_run_at_price(mctx, price):
    config = MexcConfig(api_key="test", api_secret="test")
    mctx.dry_client = DryRunClient(config)
    mctx.dry_client._market_client = MagicMock()
    mctx.dry_client._last_price = float(price)
    return mctx


@given(
    "a market poller connected to MEXC",
    target_fixture="mctx",
)
def given_poller(mctx):
    mock_client = MagicMock()
    mock_client.get_ticker.return_value = {
        'lastPrice': '100000.0',
        'bid1Price': '99999.0',
        'ask1Price': '100001.0',
        'volume24h': '1000',
    }
    mock_client.get_orderbook.return_value = {
        'b': [['99999.0', '1.5']],
        'a': [['100001.0', '0.5']],
        'ts': '1700000000000',
    }
    mock_client.get_recent_trades.return_value = [
        {'price': '100000.0', 'qty': '0.1', 'timestamp': 1700000001000, 'side': 'Buy'},
    ]
    mctx.collector = OrderBookCollector()
    mctx.poller = MexcMarketPoller(mock_client, mctx.collector)
    return mctx


# --- When steps ---

@when(parsers.parse("I place a LIMIT_MAKER buy order at {price:d} for {qty:g} BTC"))
def when_place_maker_order(mctx, price, qty):
    if mctx.client:
        mctx.order_result = mctx.client.place_maker_order(
            symbol="BTCUSDT", side="Buy", qty=str(qty), price=str(price),
        )
    elif mctx.dry_client:
        mctx.order_result = mctx.dry_client.place_maker_order(
            symbol="BTCUSDT", side="Buy", qty=str(qty), price=str(price),
        )


@when(parsers.parse("I place a buy order at {price:d} for {qty:g} BTC"))
def when_place_buy_order(mctx, price, qty):
    mctx.order_result = mctx.dry_client.place_order(
        symbol="BTCUSDT", side="Buy", order_type="Limit",
        qty=str(qty), price=str(price),
    )


@when(parsers.parse("the price drops to {price:d}"))
def when_price_drops(mctx, price):
    mctx.fills = mctx.dry_client.check_fills(float(price))


@when(parsers.parse("I place a LIMIT_MAKER buy order at {price:d}"))
def when_place_maker_order_no_qty(mctx, price):
    mctx.order_result = mctx.dry_client.place_maker_order(
        symbol="BTCUSDT", side="Buy", qty="0.001", price=str(price),
    )


@when("I poll for market data")
def when_poll(mctx):
    mctx.poller.poll()


# --- Then steps ---

@then("the order type should be LIMIT_MAKER")
def then_order_type_limit_maker(mctx):
    assert mctx.order_result['orderType'] == 'LIMIT_MAKER'


@then("the order should be accepted")
def then_order_accepted(mctx):
    assert mctx.order_result['orderId'] != ''
    assert mctx.order_result.get('status') != 'rejected'


@then("the order should be filled")
def then_order_filled(mctx):
    assert len(mctx.fills) == 1
    assert mctx.fills[0]['orderStatus'] == 'Filled'


@then(parsers.parse("my BTC balance should increase by {qty:g}"))
def then_btc_balance(mctx, qty):
    assert mctx.dry_client._balance['BTC'] == pytest.approx(qty)


@then("the order should be rejected")
def then_order_rejected(mctx):
    assert mctx.order_result['status'] == 'rejected'


@then("the collector should have snapshots")
def then_collector_has_snapshots(mctx):
    assert mctx.collector.snapshot_count > 0


@then("the collector should have trades")
def then_collector_has_trades(mctx):
    assert mctx.collector.trade_count > 0
