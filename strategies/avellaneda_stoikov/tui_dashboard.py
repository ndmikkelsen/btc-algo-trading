"""Real-time TUI dashboard for the market making live trader.

Uses Rich library to render a live-updating terminal UI showing:
- Market data (price, spread, regime)
- Inventory and PnL
- Open orders
- Recent fills and fill rate
- Safety control status
"""

import time
import threading
from datetime import datetime
from typing import TYPE_CHECKING

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from strategies.avellaneda_stoikov.live_trader import LiveTrader


def _format_dollar(value: float, sign: bool = False) -> str:
    """Format a dollar value with commas."""
    if sign:
        prefix = "+" if value >= 0 else ""
        return f"{prefix}${value:,.2f}"
    return f"${value:,.2f}"


def _format_btc(value: float) -> str:
    """Format a BTC quantity."""
    return f"{value:.6f}"


def _pnl_style(value: float) -> str:
    """Return Rich style string for PnL coloring."""
    if value > 0:
        return "bold green"
    elif value < 0:
        return "bold red"
    return "dim"


def _build_header(trader: "LiveTrader") -> Panel:
    """Build the header panel with mode and model info."""
    mode = "DRY-RUN" if trader.dry_run else "LIVE"
    mode_style = "yellow" if trader.dry_run else "bold red"
    exchange = "Bybit Futures" if trader.use_futures else "MEXC Spot"
    model_name = type(trader.model).__name__

    header = Text()
    header.append("Market Maker ", style="bold white")
    header.append(f"[{mode}]", style=mode_style)
    header.append(f"  {exchange}", style="cyan")
    header.append(f"  {model_name}", style="magenta")
    header.append(f"  {trader.symbol}", style="white")
    if trader.use_futures:
        header.append(f"  {trader.leverage}x", style="yellow")

    ts = trader.state.last_update
    if ts:
        header.append(f"  {ts.strftime('%H:%M:%S')}", style="dim")

    return Panel(header, style="blue")


def _build_market_panel(trader: "LiveTrader") -> Panel:
    """Build the market data panel."""
    s = trader.state
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("label", style="dim", width=12)
    table.add_column("value", style="bold")

    table.add_row("Mid Price", _format_dollar(s.current_price))

    if s.bid_price and s.ask_price:
        spread_dollar = s.ask_price - s.bid_price
        spread_bps = spread_dollar / s.current_price * 10000 if s.current_price > 0 else 0
        table.add_row("Bid", _format_dollar(s.bid_price))
        table.add_row("Ask", _format_dollar(s.ask_price))
        table.add_row("Spread", f"${spread_dollar:.2f} ({spread_bps:.1f} bps)")
    else:
        table.add_row("Bid", "--")
        table.add_row("Ask", "--")
        table.add_row("Spread", "--")

    regime = s.current_regime or "n/a"
    table.add_row("Regime", regime)

    # Volatility from price history
    if len(trader.price_history) >= 10:
        vol = trader._calculate_volatility()
        table.add_row("Volatility", f"{vol:.4%}")

    return Panel(table, title="Market", border_style="cyan")


def _build_inventory_panel(trader: "LiveTrader") -> Panel:
    """Build the inventory and PnL panel."""
    s = trader.state
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("label", style="dim", width=14)
    table.add_column("value")

    # Inventory
    inv_style = "bold yellow" if abs(s.inventory) > 0 else "green"
    table.add_row("Inventory", Text(_format_btc(s.inventory) + " BTC", style=inv_style))

    # Inventory value
    inv_value = s.inventory * s.current_price
    table.add_row("Inv Value", _format_dollar(inv_value))

    # Cash
    table.add_row("Cash", _format_dollar(s.cash))

    # PnL breakdown
    realized_pnl = s.cash - trader.initial_capital
    unrealized_pnl = inv_value
    total_pnl = s.total_pnl

    table.add_row("Realized PnL", Text(_format_dollar(realized_pnl, sign=True), style=_pnl_style(realized_pnl)))
    table.add_row("Unrealized PnL", Text(_format_dollar(unrealized_pnl, sign=True), style=_pnl_style(unrealized_pnl)))
    table.add_row("Total PnL", Text(_format_dollar(total_pnl, sign=True), style=_pnl_style(total_pnl)))

    # Fees
    table.add_row("Total Fees", _format_dollar(s.total_fees))

    # ROI
    roi = (total_pnl / trader.initial_capital * 100) if trader.initial_capital > 0 else 0
    roi_text = f"{roi:+.4f}%"
    table.add_row("ROI", Text(roi_text, style=_pnl_style(total_pnl)))

    return Panel(table, title="Position & PnL", border_style="green")


def _build_orders_table(trader: "LiveTrader") -> Panel:
    """Build the open orders table."""
    s = trader.state
    table = Table(box=None, padding=(0, 1))
    table.add_column("Side", width=6)
    table.add_column("Price", width=14)
    table.add_column("Size", width=12)
    table.add_column("Order ID", width=16)

    if s.bid_order_id:
        table.add_row(
            Text("BID", style="green"),
            _format_dollar(s.bid_price) if s.bid_price else "--",
            str(trader.order_size),
            s.bid_order_id[:16] if s.bid_order_id else "--",
        )
    if s.ask_order_id:
        table.add_row(
            Text("ASK", style="red"),
            _format_dollar(s.ask_price) if s.ask_price else "--",
            str(trader.order_size),
            s.ask_order_id[:16] if s.ask_order_id else "--",
        )

    if not s.bid_order_id and not s.ask_order_id:
        table.add_row(Text("No open orders", style="dim"), "", "", "")

    return Panel(table, title="Open Orders", border_style="yellow")


def _build_fills_panel(trader: "LiveTrader") -> Panel:
    """Build the fills and fill rate panel."""
    s = trader.state
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("label", style="dim", width=14)
    table.add_column("value")

    table.add_row("Total Fills", str(s.trades_count))

    # Fill rate (fills per minute)
    if s.trades_count > 0 and s.last_update:
        # Use the trader's internal fill tracking
        recent = trader._recent_fills[-20:] if trader._recent_fills else []
        buys = sum(1 for f in recent if f == "buy")
        sells = sum(1 for f in recent if f == "sell")
        table.add_row("Recent Buys", str(buys))
        table.add_row("Recent Sells", str(sells))

        # Fill imbalance
        if recent:
            imbalance = abs(buys - sells) / len(recent)
            imb_style = "yellow" if imbalance > 0.5 else "green"
            table.add_row("Imbalance", Text(f"{imbalance:.0%}", style=imb_style))
    else:
        table.add_row("Recent Buys", "0")
        table.add_row("Recent Sells", "0")

    # Last fill time
    if trader._last_fill_time > 0:
        ago = time.time() - trader._last_fill_time
        if ago < 60:
            table.add_row("Last Fill", f"{ago:.0f}s ago")
        else:
            table.add_row("Last Fill", f"{ago / 60:.1f}m ago")
    else:
        table.add_row("Last Fill", "--")

    return Panel(table, title="Fills", border_style="magenta")


def _build_safety_panel(trader: "LiveTrader") -> Panel:
    """Build the safety controls status panel."""
    from strategies.avellaneda_stoikov.config import (
        BAD_TICK_THRESHOLD,
        DISPLACEMENT_THRESHOLD,
        INVENTORY_SOFT_LIMIT,
        INVENTORY_HARD_LIMIT,
        FILL_COOLDOWN_SECONDS,
        DYNAMIC_GAMMA_ENABLED,
        DUAL_TIMEFRAME_VOL_ENABLED,
        ASYMMETRIC_SPREADS_ENABLED,
        FILL_IMBALANCE_ENABLED,
    )

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("control", width=16)
    table.add_column("status", width=10)

    on = Text("ON", style="green")
    off = Text("OFF", style="dim")

    # Phase 1 controls — always on
    table.add_row(f"Tick Filter", Text(f"{BAD_TICK_THRESHOLD:.0%}", style="green"))
    table.add_row(f"Displacement", Text(f"{DISPLACEMENT_THRESHOLD:.1%}", style="green"))
    table.add_row(f"Inv Limit", Text(f"{INVENTORY_SOFT_LIMIT}/{INVENTORY_HARD_LIMIT}x", style="green"))
    table.add_row(f"Fill Cooldown", Text(f"{FILL_COOLDOWN_SECONDS}s", style="green"))

    # Phase 2 controls — configurable
    table.add_row("Dynamic Gamma", on if DYNAMIC_GAMMA_ENABLED else off)
    table.add_row("Dual-TF Vol", on if DUAL_TIMEFRAME_VOL_ENABLED else off)
    table.add_row("Asym Spreads", on if ASYMMETRIC_SPREADS_ENABLED else off)
    table.add_row("Fill Imbalance", on if FILL_IMBALANCE_ENABLED else off)

    # Regime filter
    regime_on = trader.regime_detector is not None
    table.add_row("Regime Filter", on if regime_on else off)

    # Live stats
    table.add_row("Ticks Rejected", str(trader._tick_rejection_count))
    table.add_row("Errors", str(len(trader.state.errors)))

    return Panel(table, title="Safety Controls", border_style="red")


def _build_errors_panel(trader: "LiveTrader") -> Panel:
    """Build the recent errors panel."""
    errors = trader.state.errors[-5:]  # Last 5 errors
    if not errors:
        content = Text("No errors", style="dim")
    else:
        content = Text()
        for err in errors:
            content.append(f"  {err}\n", style="red")

    return Panel(content, title="Recent Errors", border_style="red")


def build_dashboard(trader: "LiveTrader") -> Layout:
    """Build the full dashboard layout from trader state.

    Parameters
    ----------
    trader : LiveTrader
        The live trader instance to read state from.

    Returns
    -------
    Layout
        A Rich Layout ready for rendering.
    """
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=9),
    )

    # Header
    layout["header"].update(_build_header(trader))

    # Body: two columns
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )

    # Left column: market + orders
    layout["left"].split_column(
        Layout(name="market"),
        Layout(name="orders", size=8),
    )
    layout["market"].update(_build_market_panel(trader))
    layout["orders"].update(_build_orders_table(trader))

    # Right column: inventory + fills
    layout["right"].split_column(
        Layout(name="inventory"),
        Layout(name="fills"),
    )
    layout["inventory"].update(_build_inventory_panel(trader))
    layout["fills"].update(_build_fills_panel(trader))

    # Footer: safety controls + errors
    layout["footer"].split_row(
        Layout(name="safety"),
        Layout(name="errors"),
    )
    layout["safety"].update(_build_safety_panel(trader))
    layout["footer"]["errors"].update(_build_errors_panel(trader))

    return layout


def run_dashboard(trader: "LiveTrader", refresh_rate: float = 1.0) -> None:
    """Run the live TUI dashboard.

    Starts a Rich Live display that refreshes at the given rate,
    reading state from the trader instance. Blocks until Ctrl+C.

    Parameters
    ----------
    trader : LiveTrader
        The live trader instance (must already be started).
    refresh_rate : float
        Seconds between screen refreshes. Default 1.0.
    """
    console = Console()

    with Live(
        build_dashboard(trader),
        console=console,
        refresh_per_second=int(1 / refresh_rate),
        screen=True,
    ) as live:
        try:
            while trader.state.is_running:
                live.update(build_dashboard(trader))
                time.sleep(refresh_rate)
        except KeyboardInterrupt:
            pass


def start_dashboard_thread(trader: "LiveTrader", refresh_rate: float = 1.0) -> threading.Thread:
    """Start the dashboard in a background thread.

    Parameters
    ----------
    trader : LiveTrader
        The live trader instance.
    refresh_rate : float
        Seconds between refreshes.

    Returns
    -------
    threading.Thread
        The dashboard thread (already started, daemon=True).
    """
    t = threading.Thread(
        target=run_dashboard,
        args=(trader, refresh_rate),
        daemon=True,
    )
    t.start()
    return t
