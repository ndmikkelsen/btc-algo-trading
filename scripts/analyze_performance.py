#!/usr/bin/env python3
"""Analyze trading performance from log files.

Usage:
    python scripts/analyze_performance.py logs/trader_20260212.log
    python scripts/analyze_performance.py logs/trader_*.log
"""

import sys
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path


def parse_log_file(log_path):
    """Parse a log file and extract trading data."""
    trades = []
    fills = []
    errors = []
    safety_activations = defaultdict(int)

    with open(log_path, 'r') as f:
        for line in f:
            # Parse fills
            if 'FILL:' in line:
                match = re.search(r'FILL: (\w+) ([\d.]+) @ \$([\d.]+).*\[inv: ([-\d.]+)\]', line)
                if match:
                    side, qty, price, inventory = match.groups()
                    timestamp = re.search(r'\[([\d-]+ [\d:.]+)\]', line)
                    fills.append({
                        'timestamp': timestamp.group(1) if timestamp else None,
                        'side': side,
                        'qty': float(qty),
                        'price': float(price),
                        'inventory': float(inventory)
                    })

            # Parse safety activations
            if 'DISPLACEMENT GUARD:' in line:
                safety_activations['displacement_guard'] += 1
            elif 'ASYMMETRIC:' in line:
                safety_activations['asymmetric_spreads'] += 1
            elif 'FILL IMBALANCE:' in line:
                safety_activations['fill_imbalance'] += 1
            elif 'INV LIMIT:' in line:
                safety_activations['inventory_limit'] += 1
            elif 'LIQUIDATION:' in line or 'APPROACHING LIQUIDATION:' in line:
                safety_activations['liquidation_warning'] += 1

            # Parse errors
            if 'Error' in line or 'error' in line:
                errors.append(line.strip())

    return {
        'fills': fills,
        'safety_activations': safety_activations,
        'errors': errors
    }


def analyze_trades(fills):
    """Analyze trading performance from fills."""
    if not fills:
        return None

    # Pair up buy/sell to calculate P&L
    position = 0.0
    entry_prices = []
    realized_pnl = 0.0
    winning_trades = 0
    losing_trades = 0
    trade_pnls = []

    for fill in fills:
        qty = fill['qty']
        price = fill['price']

        if fill['side'] in ('Buy', 'buy'):
            # Opening long or closing short
            if position < 0:
                # Closing short
                close_qty = min(abs(position), qty)
                avg_entry = sum(entry_prices[:int(close_qty / fills[0]['qty'])]) / len(entry_prices[:int(close_qty / fills[0]['qty'])]) if entry_prices else price
                pnl = (avg_entry - price) * close_qty
                realized_pnl += pnl
                trade_pnls.append(pnl)
                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                position += close_qty
            else:
                # Opening long
                entry_prices.append(price)
                position += qty
        else:
            # Opening short or closing long
            if position > 0:
                # Closing long
                close_qty = min(position, qty)
                avg_entry = sum(entry_prices[:int(close_qty / fills[0]['qty'])]) / len(entry_prices[:int(close_qty / fills[0]['qty'])]) if entry_prices else price
                pnl = (price - avg_entry) * close_qty
                realized_pnl += pnl
                trade_pnls.append(pnl)
                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                position -= close_qty
            else:
                # Opening short
                entry_prices.append(price)
                position -= qty

    total_trades = winning_trades + losing_trades
    win_rate = winning_trades / total_trades if total_trades > 0 else 0

    avg_win = sum(p for p in trade_pnls if p > 0) / winning_trades if winning_trades > 0 else 0
    avg_loss = sum(p for p in trade_pnls if p < 0) / losing_trades if losing_trades > 0 else 0
    profit_factor = abs(sum(p for p in trade_pnls if p > 0) / sum(p for p in trade_pnls if p < 0)) if sum(p for p in trade_pnls if p < 0) != 0 else 0

    return {
        'total_fills': len(fills),
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'realized_pnl': realized_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'final_position': position
    }


def print_report(log_path, data):
    """Print performance report."""
    print("=" * 80)
    print(f"PERFORMANCE REPORT: {Path(log_path).name}")
    print("=" * 80)
    print()

    # Trading stats
    fills = data['fills']
    if fills:
        print("📊 TRADING ACTIVITY")
        print("-" * 80)
        print(f"Total Fills:        {len(fills)}")

        analysis = analyze_trades(fills)
        if analysis:
            print(f"Completed Trades:   {analysis['total_trades']}")
            print(f"Winning Trades:     {analysis['winning_trades']} ({analysis['win_rate']:.1%})")
            print(f"Losing Trades:      {analysis['losing_trades']}")
            print(f"Realized P&L:       ${analysis['realized_pnl']:.2f}")
            print(f"Avg Win:            ${analysis['avg_win']:.2f}")
            print(f"Avg Loss:           ${analysis['avg_loss']:.2f}")
            print(f"Profit Factor:      {analysis['profit_factor']:.2f}")
            print(f"Final Position:     {analysis['final_position']:.6f} BTC")
        print()
    else:
        print("❌ No fills found in log")
        print()

    # Safety activations
    safety = data['safety_activations']
    if safety:
        print("🛡️  SAFETY CONTROLS")
        print("-" * 80)
        for control, count in safety.items():
            print(f"{control.replace('_', ' ').title():20s} {count} activations")
        print()

    # Errors
    errors = data['errors']
    if errors:
        print("⚠️  ERRORS")
        print("-" * 80)
        for error in errors[:10]:  # Show first 10 errors
            print(f"  {error[:100]}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
        print()
    else:
        print("✅ No errors detected")
        print()

    print("=" * 80)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_performance.py <log_file>")
        sys.exit(1)

    log_path = sys.argv[1]

    if not Path(log_path).exists():
        print(f"Error: Log file not found: {log_path}")
        sys.exit(1)

    print(f"\nAnalyzing {log_path}...\n")

    data = parse_log_file(log_path)
    print_report(log_path, data)


if __name__ == "__main__":
    main()
