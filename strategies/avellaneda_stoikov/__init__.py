"""Avellaneda-Stoikov Market Making Model.

Implementation of the optimal market making framework from:
"High-frequency trading in a limit order book" (Avellaneda & Stoikov, 2008)
"""

from strategies.avellaneda_stoikov.model import (
    AvellanedaStoikov,
    VolatilityEstimator,
    VolatilityEstimate,
)
from strategies.avellaneda_stoikov.order_manager import (
    Order,
    OrderSide,
    OrderStatus,
    OrderManager,
)
from strategies.avellaneda_stoikov.simulator import MarketSimulator
from strategies.avellaneda_stoikov.regime import RegimeDetector, MarketRegime
from strategies.avellaneda_stoikov.metrics import calculate_all_metrics
from strategies.avellaneda_stoikov.risk_manager import RiskManager, TradeSetup

__all__ = [
    "AvellanedaStoikov",
    "VolatilityEstimator",
    "VolatilityEstimate",
    "Order",
    "OrderSide",
    "OrderStatus",
    "OrderManager",
    "MarketSimulator",
    "RegimeDetector",
    "MarketRegime",
    "calculate_all_metrics",
    "RiskManager",
    "TradeSetup",
]
