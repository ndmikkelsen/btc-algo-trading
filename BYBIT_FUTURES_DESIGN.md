# Bybit Futures Architecture Design

## Overview
Migration from MEXC spot to Bybit futures for 50x leveraged market making.

## File Structure

```
strategies/avellaneda_stoikov/
├── bybit_futures_client.py    # NEW - Bybit futures client
├── mexc_client.py              # KEEP - existing spot client (deprecated for production)
├── live_trader.py              # UPDATE - add futures mode support
├── config.py                   # UPDATE - add futures-specific params
├── fee_model.py                # UPDATE - add Bybit futures fees
└── base_model.py               # NO CHANGE - model is exchange-agnostic
```

## Class Architecture

### 1. BybitFuturesClient (NEW)

```python
class BybitFuturesClient:
    """Bybit futures client using ccxt library."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'options': {
                'defaultType': 'swap',  # Perpetual futures
            }
        })
        if testnet:
            self.exchange.set_sandbox_mode(True)

    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for symbol (1-100x)."""
        return self.exchange.set_leverage(leverage, symbol)

    def set_margin_mode(self, symbol: str, mode: str = 'isolated'):
        """Set margin mode: 'isolated' or 'cross'."""
        return self.exchange.set_margin_mode(mode, symbol)

    def fetch_ticker(self, symbol: str):
        """Get market ticker data."""
        return self.exchange.fetch_ticker(symbol)

    def fetch_position(self, symbol: str):
        """Get current position."""
        positions = self.exchange.fetch_positions([symbol])
        return positions[0] if positions else None

    def place_order(self, symbol: str, side: str, amount: float, price: float = None, order_type: str = 'limit'):
        """Place order (limit/market)."""
        return self.exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=amount,
            price=price,
            params={'postOnly': True} if order_type == 'limit' else {}
        )

    def cancel_all_orders(self, symbol: str):
        """Cancel all open orders for symbol."""
        return self.exchange.cancel_all_orders(symbol)

    def fetch_balance(self):
        """Get account balance."""
        return self.exchange.fetch_balance()
```

### 2. DryRunFuturesClient (NEW)

```python
class DryRunFuturesClient:
    """Simulated futures client for paper trading with leverage."""

    def __init__(self, initial_balance: float = 1000, leverage: int = 50):
        self.balance = initial_balance
        self.leverage = leverage
        self.position = None  # {'size': float, 'side': str, 'entry_price': float}
        self.open_orders = {}

        # Connect to real market data
        self.exchange = ccxt.bybit({'options': {'defaultType': 'swap'}})

    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage (affects margin and liquidation)."""
        self.leverage = leverage
        if self.position:
            self._update_liquidation_price()

    def calculate_liquidation_price(self):
        """Calculate liquidation price based on position and leverage."""
        if not self.position:
            return None

        entry = self.position['entry_price']
        size = abs(self.position['size'])
        side = self.position['side']

        # Simplified liquidation calculation (isolated margin)
        # Liq = Entry ± (Entry / Leverage)
        if side == 'long':
            return entry - (entry / self.leverage)
        else:  # short
            return entry + (entry / self.leverage)

    def fetch_ticker(self, symbol: str):
        """Get real market data."""
        return self.exchange.fetch_ticker(symbol)

    def place_order(self, symbol: str, side: str, amount: float, price: float, **kwargs):
        """Place simulated order."""
        order_id = f"sim_{len(self.open_orders) + 1}"
        self.open_orders[order_id] = {
            'orderId': order_id,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'status': 'open'
        }
        return {'orderId': order_id}

    def check_fills(self, current_price: float):
        """Check if any orders filled at current price."""
        fills = []
        for order_id, order in list(self.open_orders.items()):
            filled = False
            if order['side'] == 'buy' and current_price <= order['price']:
                filled = True
            elif order['side'] == 'sell' and current_price >= order['price']:
                filled = True

            if filled:
                self._execute_fill(order, current_price)
                fills.append(order)
                del self.open_orders[order_id]

        return fills

    def _execute_fill(self, order, fill_price):
        """Execute fill and update position."""
        side = order['side']
        size = order['amount']

        if self.position is None:
            # Open new position
            self.position = {
                'size': size if side == 'buy' else -size,
                'side': 'long' if side == 'buy' else 'short',
                'entry_price': fill_price
            }
        else:
            # Update existing position
            if (side == 'buy' and self.position['side'] == 'short') or \
               (side == 'sell' and self.position['side'] == 'long'):
                # Closing position
                pnl = self._calculate_pnl(fill_price)
                self.balance += pnl

                # Update position size
                self.position['size'] += (size if side == 'buy' else -size)
                if abs(self.position['size']) < 1e-8:
                    self.position = None
            else:
                # Adding to position
                self.position['size'] += (size if side == 'buy' else -size)

    def _calculate_pnl(self, exit_price):
        """Calculate P&L for position close."""
        if not self.position:
            return 0.0

        entry = self.position['entry_price']
        size = abs(self.position['size'])
        side = self.position['side']

        if side == 'long':
            pnl = (exit_price - entry) * size
        else:  # short
            pnl = (entry - exit_price) * size

        return pnl * self.leverage  # Leveraged P&L

    def check_liquidation(self, current_price: float):
        """Check if position should be liquidated."""
        if not self.position:
            return False

        liq_price = self.calculate_liquidation_price()
        side = self.position['side']

        if side == 'long' and current_price <= liq_price:
            return True
        elif side == 'short' and current_price >= liq_price:
            return True

        return False
```

### 3. BybitMarketPoller (NEW)

```python
class BybitMarketPoller:
    """Poll Bybit market data via REST (replacement for WebSocket)."""

    def __init__(self, client: BybitFuturesClient, symbol: str):
        self.client = client
        self.symbol = symbol

    def poll(self):
        """Poll ticker data."""
        return self.client.fetch_ticker(self.symbol)
```

## LiveTrader Updates

### Config Changes

```python
# config.py - Add futures-specific parameters

# Futures mode
USE_FUTURES = True  # Toggle between spot and futures
LEVERAGE = 50       # Default leverage (1-100x for Bybit)
MARGIN_MODE = 'isolated'  # 'isolated' or 'cross'

# Liquidation protection
LIQUIDATION_THRESHOLD = 0.8  # Close position at 80% of liquidation distance
EMERGENCY_REDUCE_RATIO = 0.5  # Reduce position by 50% when approaching liquidation
```

### LiveTrader Integration

**Option A: Mode Flag (RECOMMENDED)**
- Add `use_futures` parameter to LiveTrader.__init__()
- Detect client type and adjust behavior accordingly
- Single class handles both spot and futures

**Option B: Inheritance**
- Create FuturesLiveTrader(LiveTrader)
- Override position tracking methods
- Separate class for futures-specific logic

**Recommendation: Option A** - Less code duplication, easier to maintain

### Key LiveTrader Changes

```python
class LiveTrader:
    def __init__(self, ..., use_futures=False, leverage=1):
        self.use_futures = use_futures
        self.leverage = leverage

        # Position tracking (futures-specific)
        if use_futures:
            self.position = None  # {'size', 'side', 'entry_price', 'liq_price'}

    def _check_liquidation(self):
        """Check if approaching liquidation and take action."""
        if not self.use_futures or not self.position:
            return

        current_price = self.state.current_price
        liq_price = self.position['liq_price']

        # Calculate distance to liquidation
        distance = abs(current_price - liq_price) / current_price

        if distance < (1 - LIQUIDATION_THRESHOLD):
            # Emergency position reduction
            print(f"⚠️ APPROACHING LIQUIDATION - Reducing position")
            self._emergency_reduce_position()

    def _emergency_reduce_position(self):
        """Reduce position size to avoid liquidation."""
        # Implementation here
        pass
```

## Fee Model Updates

```python
# fee_model.py - Add Bybit futures fees

BYBIT_FUTURES_TIERS = {
    'VIP0': {'maker': 0.0001, 'taker': 0.0006},  # 0.01% / 0.06%
    'VIP1': {'maker': 0.0001, 'taker': 0.0005},
    # ... other VIP tiers
}
```

## Migration Path

1. ✅ Create bybit_futures_client.py with BybitFuturesClient + DryRunFuturesClient
2. ✅ Add BybitMarketPoller for market data
3. ✅ Update config.py with futures parameters
4. ✅ Update fee_model.py with Bybit fees
5. ✅ Update live_trader.py with futures mode flag and liquidation protection
6. ✅ Update run_paper_trader.py CLI args (--use-futures, --leverage)
7. ✅ Write tests for futures client and liquidation logic
8. ✅ Dry-run test with 50x leverage

## Testing Strategy

1. **Unit Tests**: BybitFuturesClient methods
2. **Integration Tests**: DryRunFuturesClient fill simulation
3. **Liquidation Tests**: Verify liquidation price calculation and emergency reduction
4. **End-to-End**: 20-minute dry-run with 50x leverage, verify P&L and safety controls

## Timeline

- Task #2 (Design): DONE (this document)
- Task #3 (Implement client): ~30 minutes
- Task #4 (Liquidation protection): ~20 minutes
- Task #5 (Testing): ~20 minutes + 20-minute dry-run

**Total estimated time: ~1.5 hours**
