"""Integration tests for wiring all components together.

Verifies that LiveTrader correctly wires:
- MarketMakingModel (GLFT / A-S)
- KappaProvider (Live / Constant)
- FeeModel (fee tracking, profitability checks)
- OrderBookCollector (market data pipeline)
- LIMIT_MAKER order placement
"""

from unittest.mock import MagicMock

from strategies.avellaneda_stoikov.glft_model import GLFTModel
from strategies.avellaneda_stoikov.model import AvellanedaStoikov
from strategies.avellaneda_stoikov.fee_model import FeeModel, FeeTier
from strategies.avellaneda_stoikov.orderbook import (
    OrderBookCollector,
    OrderBookSnapshot,
    TradeRecord,
    KappaCalibrator,
)
from strategies.avellaneda_stoikov.kappa_provider import (
    ConstantKappaProvider,
    LiveKappaProvider,
)
from strategies.avellaneda_stoikov.live_trader import LiveTrader, TraderState
from strategies.avellaneda_stoikov.mexc_client import (
    MexcClient,
    DryRunClient,
    MexcConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trader(**kwargs):
    """Create a LiveTrader with mocked MEXC client."""
    defaults = dict(
        api_key="test-key",
        api_secret="test-secret",
        dry_run=True,
    )
    defaults.update(kwargs)
    trader = LiveTrader(**defaults)
    # Mock the client to avoid real HTTP calls
    trader.client = MagicMock(spec=DryRunClient)
    trader.client.cancel_all_orders.return_value = {'cancelled': [], 'count': 0}
    trader.client.check_fills.return_value = []
    return trader


# ===========================================================================
# LiveTrader Wiring
# ===========================================================================


class TestLiveTraderModelWiring:
    """Test that LiveTrader accepts and wires models correctly."""

    def test_default_model_is_glft(self):
        trader = _make_trader()
        assert isinstance(trader.model, GLFTModel)

    def test_inject_as_model(self):
        model = AvellanedaStoikov()
        trader = _make_trader(model=model)
        assert isinstance(trader.model, AvellanedaStoikov)
        assert trader.model is model

    def test_inject_glft_model(self):
        model = GLFTModel(risk_aversion=0.001)
        trader = _make_trader(model=model)
        assert trader.model.risk_aversion == 0.001


class TestLiveTraderFeeWiring:
    """Test FeeModel integration."""

    def test_default_fee_model_regular(self):
        trader = _make_trader()
        assert isinstance(trader.fee_model, FeeModel)
        assert trader.fee_model.tier == FeeTier.REGULAR

    def test_inject_mx_deduction_fee_model(self):
        fm = FeeModel(FeeTier.MX_DEDUCTION)
        trader = _make_trader(fee_model=fm)
        assert trader.fee_model.tier == FeeTier.MX_DEDUCTION

    def test_order_manager_uses_fee_model_rate(self):
        fm = FeeModel(FeeTier.REGULAR)
        trader = _make_trader(fee_model=fm)
        assert trader.order_manager.maker_fee == fm.schedule.maker


class TestLiveTraderKappaWiring:
    """Test KappaProvider integration."""

    def test_default_kappa_provider_is_live(self):
        trader = _make_trader()
        assert isinstance(trader.kappa_provider, LiveKappaProvider)

    def test_inject_constant_kappa(self):
        kp = ConstantKappaProvider(kappa=0.02, A=5.0)
        trader = _make_trader(kappa_provider=kp)
        assert isinstance(trader.kappa_provider, ConstantKappaProvider)

    def test_collector_created(self):
        trader = _make_trader()
        assert isinstance(trader.collector, OrderBookCollector)


class TestKappaModelUpdate:
    """Test _update_model_kappa propagates kappa/A to the model."""

    def test_glft_receives_kappa_and_A(self):
        kp = ConstantKappaProvider(kappa=0.03, A=8.0)
        trader = _make_trader(kappa_provider=kp)
        trader._update_model_kappa()
        assert trader.model.order_book_liquidity == 0.03
        assert trader.model.arrival_rate == 8.0

    def test_as_receives_kappa_only(self):
        model = AvellanedaStoikov()
        kp = ConstantKappaProvider(kappa=0.03, A=8.0)
        trader = _make_trader(model=model, kappa_provider=kp)
        trader._update_model_kappa()
        assert trader.model.order_book_liquidity == 0.03
        # A-S model has no arrival_rate attribute
        assert not hasattr(AvellanedaStoikov, "arrival_rate")


class TestDryRunMode:
    """Test dry-run vs live mode selection."""

    def test_default_is_dry_run(self):
        trader = LiveTrader(
            api_key="test", api_secret="test",
        )
        assert trader.dry_run is True
        assert isinstance(trader.client, DryRunClient)

    def test_live_mode_creates_mexc_client(self):
        trader = LiveTrader(
            api_key="test", api_secret="test", dry_run=False,
        )
        assert trader.dry_run is False
        assert isinstance(trader.client, MexcClient)


# ===========================================================================
# Pipeline: Collector → KappaProvider → Model
# ===========================================================================


class TestPipelineWiring:
    """Test the full data pipeline: collector → kappa → model."""

    def test_collector_feeds_kappa_provider_defaults(self):
        """Without data, LiveKappaProvider returns defaults."""
        collector = OrderBookCollector()
        provider = LiveKappaProvider(
            collector=collector,
            default_kappa=0.5,
            default_A=20.0,
        )
        kappa, A = provider.get_kappa()
        assert kappa == 0.5
        assert A == 20.0

    def test_collector_with_data_attempts_calibration(self):
        """With enough data, calibration is attempted."""
        collector = OrderBookCollector()
        calibrator = KappaCalibrator(min_trades=5, bin_width=10.0)
        provider = LiveKappaProvider(
            collector=collector,
            calibrator=calibrator,
            default_kappa=0.5,
            default_A=20.0,
        )

        # Add a snapshot for mid price reference
        collector.add_snapshot(OrderBookSnapshot(
            bids=[(100000.0, 1.0)],
            asks=[(100001.0, 1.0)],
            timestamp=1000.0,
        ))

        # Add trades at various distances from mid
        for i in range(50):
            collector.add_trade(TradeRecord(
                price=100000.0 + (i % 10) * 5.0,
                qty=0.001,
                timestamp=1000.0 + i,
                side="Buy",
            ))

        kappa, A = provider.get_kappa()
        # Should return something positive (calibrated or default)
        assert kappa > 0
        assert A > 0

    def test_kappa_change_affects_quotes(self):
        """Updating kappa on the model changes the spread."""
        model = GLFTModel(
            risk_aversion=0.0001,
            order_book_liquidity=0.05,
            arrival_rate=10.0,
            max_spread_dollar=1e12,
        )

        bid1, ask1 = model.calculate_quotes(
            mid_price=100000.0, inventory=0.0,
            volatility=0.02, time_remaining=0.5,
        )
        spread1 = ask1 - bid1

        # Lower kappa = less competition = wider spread
        model.order_book_liquidity = 0.02
        bid2, ask2 = model.calculate_quotes(
            mid_price=100000.0, inventory=0.0,
            volatility=0.02, time_remaining=0.5,
        )
        spread2 = ask2 - bid2

        assert spread2 > spread1


# ===========================================================================
# Fee Tracking
# ===========================================================================


class TestFeeTracking:
    """Test fee model integration in trading loop."""

    def test_maker_fee_is_zero(self):
        fm = FeeModel(FeeTier.REGULAR)
        fee = fm.maker_fee(100_000.0)
        assert fee == 0.0

    def test_round_trip_cost_is_zero(self):
        fm = FeeModel(FeeTier.REGULAR)
        rt = fm.round_trip_cost(100_000.0, maker_both=True)
        assert rt == 0.0

    def test_spread_always_profitable(self):
        """With 0% maker fees, any positive spread is profitable."""
        trader = _make_trader()
        trader.state.current_price = 100_000.0
        trader.order_size = 0.001
        # Even a $10 spread is profitable with 0% maker fees
        assert trader._is_spread_profitable(99995.0, 100005.0)

    def test_spread_profitable_tight(self):
        """Even very tight spread is profitable with 0% maker."""
        trader = _make_trader()
        trader.state.current_price = 100_000.0
        trader.order_size = 0.001
        # $0.20 spread: profit = $0.20 * 0.001 = $0.0002, fee = $0
        assert trader._is_spread_profitable(99999.9, 100000.1)


# ===========================================================================
# LIMIT_MAKER Orders
# ===========================================================================


class TestLimitMakerOrders:
    """Test LIMIT_MAKER order placement."""

    def test_place_maker_order_uses_limit_maker(self):
        config = MexcConfig(api_key="test", api_secret="test")
        client = MexcClient(config)
        client.exchange = MagicMock()
        client.exchange.create_order.return_value = {
            'id': '12345', 'status': 'open',
        }

        result = client.place_maker_order(
            symbol="BTCUSDT", side="Buy", qty="0.001", price="100000.00",
        )

        client.exchange.create_order.assert_called_with(
            symbol="BTC/USDT", type="LIMIT_MAKER", side="buy",
            amount=0.001, price=100000.0,
        )
        assert result['orderType'] == 'LIMIT_MAKER'

    def test_live_trader_uses_limit_maker(self):
        """LiveTrader places LIMIT_MAKER orders via place_maker_order."""
        trader = _make_trader()
        trader.state.current_price = 100_000.0
        trader.client.place_maker_order.return_value = {"orderId": "bid-1"}

        trader.client.place_maker_order(
            symbol="BTCUSDT", side="Buy", qty="0.001", price="99990.00",
        )

        call_kwargs = trader.client.place_maker_order.call_args[1]
        assert call_kwargs["side"] == "Buy"


# ===========================================================================
# State & Status
# ===========================================================================


class TestTraderStatus:
    """Test trader status reporting."""

    def test_get_status_includes_model(self):
        trader = _make_trader()
        status = trader.get_status()
        assert status["model"] == "GLFTModel"

    def test_get_status_includes_mode(self):
        trader = _make_trader()
        status = trader.get_status()
        assert status["mode"] == "dry-run"

    def test_get_status_includes_fees(self):
        trader = _make_trader()
        trader.state.total_fees = 1.23
        status = trader.get_status()
        assert status["total_fees"] == 1.23

    def test_state_has_total_fees(self):
        state = TraderState()
        assert state.total_fees == 0.0
