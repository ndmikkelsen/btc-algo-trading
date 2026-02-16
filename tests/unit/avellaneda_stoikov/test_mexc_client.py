"""Unit tests for the MEXC exchange client."""

import pytest
from unittest.mock import MagicMock, patch

from strategies.avellaneda_stoikov.mexc_client import (
    MexcClient,
    MexcConfig,
    DryRunClient,
    SimulatedOrder,
    MexcMarketPoller,
)
from strategies.avellaneda_stoikov.orderbook import OrderBookCollector


# ===========================================================================
# Symbol / Side Conversion
# ===========================================================================


class TestSymbolConversion:
    """Test symbol format conversion."""

    def test_btcusdt(self):
        assert MexcClient._to_ccxt_symbol("BTCUSDT") == "BTC/USDT"

    def test_ethusdt(self):
        assert MexcClient._to_ccxt_symbol("ETHUSDT") == "ETH/USDT"

    def test_ethbtc(self):
        assert MexcClient._to_ccxt_symbol("ETHBTC") == "ETH/BTC"

    def test_solusdt(self):
        assert MexcClient._to_ccxt_symbol("SOLUSDT") == "SOL/USDT"

    def test_already_formatted(self):
        # If no known quote currency suffix, return as-is
        assert MexcClient._to_ccxt_symbol("BTC/USDT") == "BTC/USDT"


class TestSideConversion:
    """Test side format conversion."""

    def test_buy(self):
        assert MexcClient._to_ccxt_side("Buy") == "buy"

    def test_sell(self):
        assert MexcClient._to_ccxt_side("Sell") == "sell"


# ===========================================================================
# MexcClient (mocked ccxt)
# ===========================================================================


class TestMexcClient:
    """Test MexcClient with mocked ccxt exchange."""

    @pytest.fixture
    def client(self):
        config = MexcConfig(api_key="test-key", api_secret="test-secret")
        c = MexcClient(config)
        c.exchange = MagicMock()
        return c

    def test_get_ticker(self, client):
        client.exchange.fetch_ticker.return_value = {
            'last': 100000.0,
            'bid': 99999.0,
            'ask': 100001.0,
            'baseVolume': 1234.5,
        }
        result = client.get_ticker("BTCUSDT")
        assert result['lastPrice'] == '100000.0'
        assert result['bid1Price'] == '99999.0'
        assert result['ask1Price'] == '100001.0'
        client.exchange.fetch_ticker.assert_called_with("BTC/USDT")

    def test_get_orderbook(self, client):
        client.exchange.fetch_order_book.return_value = {
            'bids': [[99999.0, 1.5], [99998.0, 2.0]],
            'asks': [[100001.0, 0.5], [100002.0, 1.0]],
            'timestamp': 1700000000000,
        }
        result = client.get_orderbook("BTCUSDT", limit=10)
        assert len(result['b']) == 2
        assert result['b'][0] == ['99999.0', '1.5']
        assert len(result['a']) == 2
        assert result['a'][0] == ['100001.0', '0.5']
        assert result['ts'] == '1700000000000'

    def test_get_klines(self, client):
        client.exchange.fetch_ohlcv.return_value = [
            [1700000000000, 100000, 100500, 99500, 100200, 50.0],
        ]
        result = client.get_klines("BTCUSDT", interval="5", limit=100)
        assert len(result) == 1
        client.exchange.fetch_ohlcv.assert_called_with(
            "BTC/USDT", timeframe="5m", limit=100,
        )

    def test_get_recent_trades(self, client):
        client.exchange.fetch_trades.return_value = [
            {'price': 100000.0, 'amount': 0.1, 'timestamp': 1700000000000, 'side': 'buy'},
            {'price': 99999.0, 'amount': 0.2, 'timestamp': 1700000001000, 'side': 'sell'},
        ]
        result = client.get_recent_trades("BTCUSDT", limit=10)
        assert len(result) == 2
        assert result[0]['side'] == 'Buy'
        assert result[1]['side'] == 'Sell'
        assert result[0]['price'] == '100000.0'

    def test_place_order(self, client):
        client.exchange.create_order.return_value = {
            'id': 'order-123',
            'status': 'open',
        }
        result = client.place_order(
            symbol="BTCUSDT", side="Buy", order_type="Limit",
            qty="0.001", price="99000",
        )
        assert result['orderId'] == 'order-123'
        assert result['side'] == 'Buy'
        client.exchange.create_order.assert_called_with(
            symbol="BTC/USDT", type="limit", side="buy",
            amount=0.001, price=99000.0,
        )

    def test_place_maker_order(self, client):
        client.exchange.create_order.return_value = {
            'id': 'order-456',
            'status': 'open',
        }
        result = client.place_maker_order(
            symbol="BTCUSDT", side="Sell", qty="0.001", price="101000",
        )
        assert result['orderId'] == 'order-456'
        assert result['orderType'] == 'LIMIT_MAKER'
        client.exchange.create_order.assert_called_with(
            symbol="BTC/USDT", type="LIMIT_MAKER", side="sell",
            amount=0.001, price=101000.0,
        )

    def test_cancel_order(self, client):
        client.exchange.cancel_order.return_value = {}
        result = client.cancel_order("BTCUSDT", "order-123")
        assert result['orderId'] == 'order-123'
        assert result['status'] == 'cancelled'

    def test_cancel_all_orders(self, client):
        client.exchange.fetch_open_orders.return_value = [
            {'id': 'o1'}, {'id': 'o2'},
        ]
        client.exchange.cancel_order.return_value = {}
        result = client.cancel_all_orders("BTCUSDT")
        assert result['count'] == 2
        assert 'o1' in result['cancelled']
        assert 'o2' in result['cancelled']

    def test_get_wallet_balance(self, client):
        client.exchange.fetch_balance.return_value = {
            'USDT': {'free': 1000.0, 'used': 50.0, 'total': 1050.0},
        }
        result = client.get_wallet_balance("USDT")
        assert result['coin'] == 'USDT'
        assert result['free'] == '1000.0'
        assert result['total'] == '1050.0'

    def test_get_open_orders(self, client):
        client.exchange.fetch_open_orders.return_value = [
            {
                'id': 'o1', 'side': 'buy', 'type': 'limit',
                'amount': 0.001, 'price': 99000.0, 'status': 'open',
            },
        ]
        result = client.get_open_orders("BTCUSDT")
        assert len(result) == 1
        assert result[0]['orderId'] == 'o1'
        assert result[0]['side'] == 'Buy'

    def test_get_order_history(self, client):
        client.exchange.fetch_closed_orders.return_value = [
            {
                'id': 'o1', 'side': 'buy', 'type': 'limit',
                'amount': 0.001, 'price': 99000.0, 'average': 99000.0,
                'status': 'closed',
            },
        ]
        result = client.get_order_history("BTCUSDT")
        assert len(result) == 1
        assert result[0]['orderStatus'] == 'Filled'
        assert result[0]['avgPrice'] == '99000.0'


# ===========================================================================
# DryRunClient
# ===========================================================================


class TestDryRunClient:
    """Test DryRunClient simulated order management."""

    @pytest.fixture
    def dry_client(self):
        config = MexcConfig(api_key="test", api_secret="test")
        client = DryRunClient(
            config, initial_usdt=1000.0, initial_btc=0.0,
        )
        # Mock the market client to avoid real API calls
        client._market_client = MagicMock()
        client._market_client.get_ticker.return_value = {
            'lastPrice': '100000.0',
            'bid1Price': '99999.0',
            'ask1Price': '100001.0',
            'volume24h': '1000',
        }
        return client

    def test_place_order_stores_in_open(self, dry_client):
        result = dry_client.place_order(
            "BTCUSDT", "Buy", "Limit", "0.001", "99000",
        )
        assert result['orderId'].startswith('dry-')
        assert len(dry_client._open_orders) == 1

    def test_check_fills_buy_on_price_drop(self, dry_client):
        dry_client.place_order("BTCUSDT", "Buy", "Limit", "0.001", "99000")
        fills = dry_client.check_fills(98999.0)
        assert len(fills) == 1
        assert fills[0]['orderStatus'] == 'Filled'
        assert fills[0]['side'] == 'Buy'

    def test_check_fills_sell_on_price_rise(self, dry_client):
        dry_client._last_price = 100000.0
        dry_client.place_order("BTCUSDT", "Sell", "Limit", "0.001", "101000")
        fills = dry_client.check_fills(101001.0)
        assert len(fills) == 1
        assert fills[0]['side'] == 'Sell'

    def test_no_fill_when_price_not_crossed(self, dry_client):
        dry_client.place_order("BTCUSDT", "Buy", "Limit", "0.001", "99000")
        fills = dry_client.check_fills(99500.0)
        assert len(fills) == 0

    def test_balance_updates_on_buy_fill(self, dry_client):
        dry_client.place_order("BTCUSDT", "Buy", "Limit", "0.001", "99000")
        dry_client.check_fills(98999.0)
        # USDT should decrease by 0.001 * 99000 = 99
        assert dry_client._balance['USDT'] == pytest.approx(1000.0 - 99.0)
        assert dry_client._balance['BTC'] == pytest.approx(0.001)

    def test_balance_updates_on_sell_fill(self, dry_client):
        dry_client._balance['BTC'] = 0.01
        dry_client._last_price = 100000.0
        dry_client.place_order("BTCUSDT", "Sell", "Limit", "0.001", "101000")
        dry_client.check_fills(101001.0)
        assert dry_client._balance['USDT'] == pytest.approx(1000.0 + 101.0)
        assert dry_client._balance['BTC'] == pytest.approx(0.009)

    def test_cancel_order(self, dry_client):
        result = dry_client.place_order(
            "BTCUSDT", "Buy", "Limit", "0.001", "99000",
        )
        order_id = result['orderId']
        dry_client.cancel_order("BTCUSDT", order_id)
        assert len(dry_client._open_orders) == 0

    def test_cancel_all_orders(self, dry_client):
        dry_client.place_order("BTCUSDT", "Buy", "Limit", "0.001", "99000")
        dry_client.place_order("BTCUSDT", "Sell", "Limit", "0.001", "101000")
        result = dry_client.cancel_all_orders("BTCUSDT")
        assert result['count'] == 2
        assert len(dry_client._open_orders) == 0

    def test_maker_order_rejects_crossing_buy(self, dry_client):
        dry_client._last_price = 100000.0
        result = dry_client.place_maker_order(
            "BTCUSDT", "Buy", "0.001", "100001",
        )
        assert result['status'] == 'rejected'
        assert len(dry_client._open_orders) == 0

    def test_maker_order_rejects_crossing_sell(self, dry_client):
        dry_client._last_price = 100000.0
        result = dry_client.place_maker_order(
            "BTCUSDT", "Sell", "0.001", "99999",
        )
        assert result['status'] == 'rejected'

    def test_maker_order_accepts_non_crossing(self, dry_client):
        dry_client._last_price = 100000.0
        result = dry_client.place_maker_order(
            "BTCUSDT", "Buy", "0.001", "99000",
        )
        assert result['orderId'].startswith('dry-')
        assert len(dry_client._open_orders) == 1

    def test_get_order_history(self, dry_client):
        dry_client.place_order("BTCUSDT", "Buy", "Limit", "0.001", "99000")
        dry_client.check_fills(98000.0)  # fill it
        history = dry_client.get_order_history("BTCUSDT")
        assert len(history) == 1
        assert history[0]['orderStatus'] == 'Filled'

    def test_get_open_orders(self, dry_client):
        dry_client.place_order("BTCUSDT", "Buy", "Limit", "0.001", "99000")
        open_orders = dry_client.get_open_orders("BTCUSDT")
        assert len(open_orders) == 1
        assert open_orders[0]['status'] == 'open'

    def test_get_wallet_balance(self, dry_client):
        result = dry_client.get_wallet_balance("USDT")
        assert result['coin'] == 'USDT'
        assert float(result['free']) == 1000.0

    def test_market_data_passes_through(self, dry_client):
        dry_client._market_client.get_orderbook.return_value = {
            'b': [['99999', '1']], 'a': [['100001', '1']], 'ts': '1700000000000',
        }
        result = dry_client.get_orderbook("BTCUSDT")
        assert 'b' in result
        dry_client._market_client.get_orderbook.assert_called_once()


# ===========================================================================
# MexcMarketPoller
# ===========================================================================


class TestMexcMarketPoller:
    """Test MexcMarketPoller collector feeding."""

    @pytest.fixture
    def poller(self):
        client = MagicMock()
        client.get_ticker.return_value = {
            'lastPrice': '100000.0',
            'bid1Price': '99999.0',
            'ask1Price': '100001.0',
            'volume24h': '1000',
        }
        client.get_orderbook.return_value = {
            'b': [['99999.0', '1.5'], ['99998.0', '2.0']],
            'a': [['100001.0', '0.5'], ['100002.0', '1.0']],
            'ts': '1700000000000',
        }
        client.get_recent_trades.return_value = [
            {'price': '100000.0', 'qty': '0.1', 'timestamp': 1700000001000, 'side': 'Buy'},
            {'price': '99999.0', 'qty': '0.2', 'timestamp': 1700000002000, 'side': 'Sell'},
        ]
        collector = OrderBookCollector()
        return MexcMarketPoller(client, collector, symbol="BTCUSDT")

    def test_poll_feeds_orderbook_snapshot(self, poller):
        poller.poll()
        assert poller.collector.snapshot_count == 1

    def test_poll_feeds_trade_records(self, poller):
        poller.poll()
        assert poller.collector.trade_count == 2

    def test_poll_returns_ticker(self, poller):
        result = poller.poll()
        assert result is not None
        assert result['lastPrice'] == '100000.0'

    def test_get_mid_price(self, poller):
        poller.poll()
        mid = poller.get_mid_price()
        assert mid == pytest.approx(100000.0)

    def test_get_mid_price_no_data(self, poller):
        assert poller.get_mid_price() is None

    def test_poll_deduplicates_trades(self, poller):
        poller.poll()
        poller.poll()  # second poll should not add duplicate trades
        # Trades have same timestamps, so second poll should add 0
        assert poller.collector.trade_count == 2

    def test_poll_handles_error(self, poller):
        poller.client.get_ticker.side_effect = Exception("network error")
        result = poller.poll()
        assert result is None
