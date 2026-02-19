#!/usr/bin/env python3
"""Run Mean Reversion Bollinger Band directional trader on Bybit futures.

Usage:
    python scripts/run_mrbb_trader.py                          # Dry-run (default)
    python scripts/run_mrbb_trader.py --live                   # Live trading
    python scripts/run_mrbb_trader.py --leverage=10 --capital=2000
    python scripts/run_mrbb_trader.py --bb-period=30 --rsi-period=21
    python scripts/run_mrbb_trader.py --timeframe=15m --interval=60

Environment variables:
    BYBIT_API_KEY    - Your Bybit API key
    BYBIT_API_SECRET - Your Bybit API secret

To get Bybit API keys:
    1. Go to https://www.bybit.com -> API Management
    2. Create a new API key with contract trading permissions
    3. Enable "Contract" and "Read-Write" permissions
    4. Set environment variables or create a .env file
"""

import argparse
import os
import re
import sys
import signal
import time
from datetime import datetime

from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.mean_reversion_bb.model import MeanReversionBB
from strategies.mean_reversion_bb.directional_trader import DirectionalTrader
from strategies.mean_reversion_bb.config import (
    BB_PERIOD,
    BB_STD_DEV,
    BB_INNER_STD_DEV,
    VWAP_PERIOD,
    VWAP_CONFIRMATION_PCT,
    KC_PERIOD,
    KC_ATR_MULTIPLIER,
    MIN_SQUEEZE_DURATION,
    RSI_PERIOD,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    ADX_PERIOD,
    ADX_THRESHOLD,
    REVERSION_TARGET,
    MAX_HOLDING_BARS,
    RISK_PER_TRADE,
    MAX_POSITION_PCT,
    STOP_ATR_MULTIPLIER,
    TIMEFRAME,
    QUOTE_REFRESH_INTERVAL,
)


class TeeStream:
    """Write to both a file and the original stream (stdout/stderr)."""

    _ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

    def __init__(self, stream, log_file):
        self.stream = stream
        self.log_file = log_file

    def write(self, data):
        self.stream.write(data)
        self.log_file.write(self._ANSI_RE.sub('', data))
        self.log_file.flush()

    def flush(self):
        self.stream.flush()
        self.log_file.flush()

    def fileno(self):
        return self.stream.fileno()

    def isatty(self):
        return self.stream.isatty()


def setup_logging(mode: str, symbol: str, instance_id: str = "default") -> str:
    """Set up automatic file logging alongside stdout.

    Creates a timestamped log file in the project's logs/ directory.
    All stdout and stderr are tee'd to both the terminal and the file.

    Returns the log file path.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_symbol = symbol.replace("/", "-").replace(":", "-")
    log_filename = f"mrbb-{instance_id}-{safe_symbol}-{mode}-{timestamp}.log"
    log_path = os.path.join("/tmp", log_filename)

    log_file = open(log_path, "a")
    sys.stdout = TeeStream(sys.__stdout__, log_file)
    sys.stderr = TeeStream(sys.__stderr__, log_file)

    return log_path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Mean Reversion Bollinger Band trader on Bybit futures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # --- Preset ---
    parser.add_argument(
        "--preset", default=None,
        help="Named preset to load (CLI args override preset values)",
    )

    # --- Instance ID ---
    parser.add_argument(
        "--instance-id", default="default", dest="instance_id",
        help="Instance identifier for concurrent bot support",
    )

    # --- Execution mode ---
    mode = parser.add_argument_group("execution mode")
    mode.add_argument(
        "--live", action="store_true",
        help="Enable live trading (real orders). Default is dry-run.",
    )
    mode.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Paper trading with real market data (default).",
    )

    # --- Account / exchange ---
    account = parser.add_argument_group("account")
    account.add_argument(
        "--capital", type=float, default=1000.0,
        help="Initial capital in USDT",
    )
    account.add_argument(
        "--leverage", type=int, default=10,
        help="Futures leverage (1-100)",
    )
    account.add_argument(
        "--symbol", type=str, default="BTC/USDT:USDT",
        help="Trading symbol",
    )

    # --- Timing ---
    timing = parser.add_argument_group("timing")
    timing.add_argument(
        "--timeframe", type=str, default=TIMEFRAME,
        help="Candle timeframe (1m, 5m, 15m, 1h, etc.)",
    )
    timing.add_argument(
        "--interval", type=float, default=QUOTE_REFRESH_INTERVAL,
        help="Poll interval in seconds",
    )
    timing.add_argument(
        "--candles", type=int, default=100,
        help="Number of candles to fetch each poll",
    )

    # --- Bollinger Band parameters ---
    bb = parser.add_argument_group("bollinger bands")
    bb.add_argument(
        "--bb-period", type=int, default=BB_PERIOD,
        help="BB moving average period",
    )
    bb.add_argument(
        "--bb-std-dev", type=float, default=BB_STD_DEV,
        help="BB outer band std dev multiplier",
    )
    bb.add_argument(
        "--bb-inner-std-dev", type=float, default=BB_INNER_STD_DEV,
        help="BB inner band std dev multiplier",
    )

    # --- VWAP parameters ---
    vwap = parser.add_argument_group("VWAP")
    vwap.add_argument(
        "--vwap-period", type=int, default=VWAP_PERIOD,
        help="VWAP rolling period (candles)",
    )

    # --- Squeeze / Keltner Channel ---
    kc = parser.add_argument_group("keltner channel / squeeze")
    kc.add_argument(
        "--kc-period", type=int, default=KC_PERIOD,
        help="Keltner Channel EMA period",
    )
    kc.add_argument(
        "--kc-atr-mult", type=float, default=KC_ATR_MULTIPLIER,
        help="Keltner Channel ATR multiplier",
    )

    # --- RSI ---
    rsi = parser.add_argument_group("RSI")
    rsi.add_argument(
        "--rsi-period", type=int, default=RSI_PERIOD,
        help="RSI calculation period",
    )
    rsi.add_argument(
        "--rsi-oversold", type=int, default=RSI_OVERSOLD,
        help="RSI oversold threshold (long entry)",
    )
    rsi.add_argument(
        "--rsi-overbought", type=int, default=RSI_OVERBOUGHT,
        help="RSI overbought threshold (short entry)",
    )

    # --- ADX / Regime filter ---
    adx = parser.add_argument_group("ADX regime filter")
    adx.add_argument(
        "--adx-period", type=int, default=ADX_PERIOD,
        help="ADX calculation period",
    )
    adx.add_argument(
        "--adx-threshold", type=float, default=ADX_THRESHOLD,
        help="ADX threshold for ranging regime (below = ranging)",
    )
    adx.add_argument(
        "--no-regime-filter", action="store_true",
        help="Disable ADX regime filter",
    )

    # --- Signal parameters ---
    sig = parser.add_argument_group("signal parameters")
    sig.add_argument(
        "--reversion-target", type=float, default=REVERSION_TARGET,
        help="Mean reversion target (fraction of distance to center)",
    )
    sig.add_argument(
        "--max-holding-bars", type=int, default=MAX_HOLDING_BARS,
        help="Maximum bars to hold a position",
    )
    sig.add_argument(
        "--vwap-confirmation-pct", type=float, default=VWAP_CONFIRMATION_PCT,
        help="VWAP proximity threshold for confirmation",
    )

    # --- Risk parameters ---
    risk = parser.add_argument_group("risk management")
    risk.add_argument(
        "--risk-per-trade", type=float, default=RISK_PER_TRADE,
        help="Risk per trade as fraction of equity",
    )
    risk.add_argument(
        "--max-position-pct", type=float, default=MAX_POSITION_PCT,
        help="Max position as fraction of equity",
    )
    risk.add_argument(
        "--stop-atr-mult", type=float, default=STOP_ATR_MULTIPLIER,
        help="Stop loss ATR multiplier",
    )

    return parser.parse_args()


def main():
    """Run the MRBB directional trader."""
    load_dotenv()
    args = parse_args()

    # Load preset defaults (CLI args still take priority)
    if args.preset:
        from strategies.mean_reversion_bb.presets import PresetManager
        pm = PresetManager()
        preset = pm.load(args.preset)
        _PRESET_MAP = {
            "bb_period": "bb_period",
            "bb_std_dev": "bb_std_dev",
            "bb_inner_std_dev": "bb_inner_std_dev",
            "vwap_period": "vwap_period",
            "vwap_confirmation_pct": "vwap_confirmation_pct",
            "kc_period": "kc_period",
            "kc_atr_multiplier": "kc_atr_mult",
            "rsi_period": "rsi_period",
            "rsi_oversold": "rsi_oversold",
            "rsi_overbought": "rsi_overbought",
            "adx_period": "adx_period",
            "adx_threshold": "adx_threshold",
            "reversion_target": "reversion_target",
            "max_holding_bars": "max_holding_bars",
            "risk_per_trade": "risk_per_trade",
            "max_position_pct": "max_position_pct",
            "stop_atr_multiplier": "stop_atr_mult",
        }
        # We need access to the parser to check defaults — use a simple
        # sentinel check: apply preset value when arg still equals its
        # config-module default (i.e. user didn't override on CLI).
        from strategies.mean_reversion_bb import config as _cfg
        _CFG_DEFAULTS = {
            "bb_period": _cfg.BB_PERIOD,
            "bb_std_dev": _cfg.BB_STD_DEV,
            "bb_inner_std_dev": _cfg.BB_INNER_STD_DEV,
            "vwap_period": _cfg.VWAP_PERIOD,
            "vwap_confirmation_pct": _cfg.VWAP_CONFIRMATION_PCT,
            "kc_period": _cfg.KC_PERIOD,
            "kc_atr_multiplier": _cfg.KC_ATR_MULTIPLIER,
            "rsi_period": _cfg.RSI_PERIOD,
            "rsi_oversold": _cfg.RSI_OVERSOLD,
            "rsi_overbought": _cfg.RSI_OVERBOUGHT,
            "adx_period": _cfg.ADX_PERIOD,
            "adx_threshold": _cfg.ADX_THRESHOLD,
            "reversion_target": _cfg.REVERSION_TARGET,
            "max_holding_bars": _cfg.MAX_HOLDING_BARS,
            "risk_per_trade": _cfg.RISK_PER_TRADE,
            "max_position_pct": _cfg.MAX_POSITION_PCT,
            "stop_atr_multiplier": _cfg.STOP_ATR_MULTIPLIER,
        }
        for preset_key, arg_dest in _PRESET_MAP.items():
            if preset_key in preset:
                cfg_default = _CFG_DEFAULTS.get(preset_key)
                if cfg_default is not None and getattr(args, arg_dest) == cfg_default:
                    setattr(args, arg_dest, preset[preset_key])
        if preset.get("use_regime_filter") is False and not args.no_regime_filter:
            args.no_regime_filter = True
        print(f"Loaded preset: {args.preset}")

    dry_run = not args.live

    # --- API credentials ---
    api_key = os.getenv("BYBIT_API_KEY", "")
    api_secret = os.getenv("BYBIT_API_SECRET", "")

    if not dry_run and (not api_key or not api_secret):
        print("=" * 60)
        print("ERROR: Missing Bybit API credentials for live trading")
        print("=" * 60)
        print()
        print("Please set environment variables:")
        print("  export BYBIT_API_KEY='your-api-key'")
        print("  export BYBIT_API_SECRET='your-api-secret'")
        print()
        print("Or create a .env file in the project root.")
        print("=" * 60)
        sys.exit(1)

    if dry_run and not api_key:
        api_key = "dry-run-key"
        api_secret = "dry-run-secret"

    # --- Logging ---
    mode = "live" if not dry_run else "dry-run"
    log_path = setup_logging(mode, args.symbol, instance_id=args.instance_id)
    print(f"Logging to: {log_path}")

    # --- Build model ---
    model = MeanReversionBB(
        bb_period=args.bb_period,
        bb_std_dev=args.bb_std_dev,
        bb_inner_std_dev=args.bb_inner_std_dev,
        vwap_period=args.vwap_period,
        vwap_confirmation_pct=args.vwap_confirmation_pct,
        kc_period=args.kc_period,
        kc_atr_multiplier=args.kc_atr_mult,
        rsi_period=args.rsi_period,
        rsi_oversold=args.rsi_oversold,
        rsi_overbought=args.rsi_overbought,
        adx_period=args.adx_period,
        adx_threshold=args.adx_threshold,
        use_regime_filter=not args.no_regime_filter,
        reversion_target=args.reversion_target,
        max_holding_bars=args.max_holding_bars,
        risk_per_trade=args.risk_per_trade,
        max_position_pct=args.max_position_pct,
        stop_atr_multiplier=args.stop_atr_mult,
    )

    # --- Auto-calculate candle limit from indicator periods ---
    min_candles = max(
        args.bb_period * 2,      # BB needs full period + warmup
        args.vwap_period + 10,   # VWAP rolling window
        args.kc_period * 2,      # KC ATR needs warmup
        args.rsi_period * 3,     # RSI Wilder smoothing warmup
        args.adx_period * 3,     # ADX needs DI+ warmup
        100,                     # absolute minimum
    )
    candle_limit = args.candles if args.candles != 100 else max(args.candles, min_candles)

    # --- Build trader ---
    trader = DirectionalTrader(
        model=model,
        api_key=api_key,
        api_secret=api_secret,
        dry_run=dry_run,
        symbol=args.symbol,
        initial_capital=args.capital,
        leverage=args.leverage,
        timeframe=args.timeframe,
        poll_interval=args.interval,
        candle_limit=candle_limit,
        instance_id=args.instance_id,
    )

    # --- Signal handler for graceful shutdown ---
    def signal_handler(sig, frame):
        print("\nReceived interrupt signal...")
        trader.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # --- Start trading ---
    try:
        trader.start()
        while trader.state.is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        trader.stop()
    except Exception as e:
        print(f"Error: {e}")
        trader.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
