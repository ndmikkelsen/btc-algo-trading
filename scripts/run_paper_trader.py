#!/usr/bin/env python3
"""Run Avellaneda-Stoikov paper trader on Bybit testnet.

Usage:
    python scripts/run_paper_trader.py

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

import os
import sys
import signal
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.avellaneda_stoikov.live_trader import LiveTrader


def main():
    """Run the paper trader."""
    # Load environment variables
    load_dotenv()

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

    # Create trader
    trader = LiveTrader(
        api_key=api_key,
        api_secret=api_secret,
        testnet=True,  # Always use testnet for paper trading
        symbol="BTCUSDT",
        initial_capital=1000.0,
        order_size=0.003,  # 0.003 BTC
        use_regime_filter=True,
        quote_interval=5.0,
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
