#!/usr/bin/env python3
"""Run market making paper trader on Bybit testnet.

Usage:
    python scripts/run_paper_trader.py                        # GLFT with live kappa
    python scripts/run_paper_trader.py --model=as             # A-S model
    python scripts/run_paper_trader.py --fee-tier=vip1        # VIP1 fees
    python scripts/run_paper_trader.py --kappa=constant       # Fixed kappa

Environment variables:
    BYBIT_API_KEY - Your Bybit testnet API key
    BYBIT_API_SECRET - Your Bybit testnet API secret

To get testnet API keys:
    1. Go to https://testnet.bybit.com
    2. Create an account (separate from mainnet)
    3. Go to API Management
    4. Create a new API key with trading permissions
    5. Set environment variables or create a .env file
"""

import argparse
import os
import sys
import signal

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.avellaneda_stoikov.glft_model import GLFTModel
from strategies.avellaneda_stoikov.model import AvellanedaStoikov
from strategies.avellaneda_stoikov.fee_model import FeeModel, FeeTier
from strategies.avellaneda_stoikov.kappa_provider import ConstantKappaProvider
from strategies.avellaneda_stoikov.live_trader import LiveTrader


FEE_TIER_MAP = {
    "regular": FeeTier.REGULAR,
    "vip1": FeeTier.VIP1,
    "vip2": FeeTier.VIP2,
    "market_maker": FeeTier.MARKET_MAKER,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run market making paper trader on Bybit testnet.",
    )
    parser.add_argument(
        "--model",
        choices=["glft", "as"],
        default="glft",
        help="Market making model: glft (default) or as (Avellaneda-Stoikov)",
    )
    parser.add_argument(
        "--fee-tier",
        choices=list(FEE_TIER_MAP.keys()),
        default="regular",
        help="Bybit fee tier (default: regular)",
    )
    parser.add_argument(
        "--kappa",
        choices=["live", "constant"],
        default="live",
        help="Kappa calibration mode: live (default) or constant",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1000.0,
        help="Initial capital in USDT (default: 1000)",
    )
    parser.add_argument(
        "--order-size",
        type=float,
        default=0.003,
        help="Order size in BTC (default: 0.003)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Quote update interval in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--no-regime-filter",
        action="store_true",
        help="Disable regime detection filter",
    )
    return parser.parse_args()


def build_model(model_name: str):
    """Create the market making model."""
    if model_name == "glft":
        return GLFTModel()
    return AvellanedaStoikov()


def main():
    """Run the paper trader."""
    load_dotenv()
    args = parse_args()

    api_key = os.getenv("BYBIT_API_KEY")
    api_secret = os.getenv("BYBIT_API_SECRET")

    if not api_key or not api_secret:
        print("=" * 60)
        print("ERROR: Missing API credentials")
        print("=" * 60)
        print()
        print("Please set environment variables:")
        print("  export BYBIT_API_KEY='your-testnet-api-key'")
        print("  export BYBIT_API_SECRET='your-testnet-api-secret'")
        print()
        print("Or create a .env file in the project root:")
        print("  BYBIT_API_KEY=your-testnet-api-key")
        print("  BYBIT_API_SECRET=your-testnet-api-secret")
        print()
        print("To get testnet API keys:")
        print("  1. Go to https://testnet.bybit.com")
        print("  2. Create an account (separate from mainnet)")
        print("  3. Go to API Management")
        print("  4. Create a new API key with trading permissions")
        print("=" * 60)
        sys.exit(1)

    model = build_model(args.model)
    fee_model = FeeModel(FEE_TIER_MAP[args.fee_tier])

    # For constant kappa, pass an explicit provider; for live mode,
    # LiveTrader creates a LiveKappaProvider backed by its internal collector
    kappa_provider = ConstantKappaProvider() if args.kappa == "constant" else None

    # Create trader
    trader = LiveTrader(
        api_key=api_key,
        api_secret=api_secret,
        testnet=True,  # Always use testnet for paper trading
        symbol="BTCUSDT",
        initial_capital=args.capital,
        order_size=args.order_size,
        use_regime_filter=not args.no_regime_filter,
        quote_interval=args.interval,
        model=model,
        fee_model=fee_model,
        kappa_provider=kappa_provider,
    )

    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\nReceived interrupt signal...")
        trader.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start trading
    try:
        trader.start()

        # Keep running until interrupted
        while trader.state.is_running:
            signal.pause()

    except KeyboardInterrupt:
        trader.stop()
    except Exception as e:
        print(f"Error: {e}")
        trader.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
