#!/usr/bin/env python3
"""Real-time data quality monitor across multiple exchanges.

Connects to 2-3 exchanges simultaneously, compares BTC prices in real-time,
and alerts on significant cross-exchange divergence.

Usage:
    python scripts/monitor_data_quality.py
    python scripts/monitor_data_quality.py --exchanges okx kucoin bitfinex --duration 3600
    python scripts/monitor_data_quality.py --threshold 0.5
"""

import argparse
import csv
import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import numpy as np

# Exchange configs
EXCHANGE_SYMBOLS = {
    "okx": "BTC/USDT",
    "kraken": "BTC/USD",
    "bitfinex": "BTC/USDT",
    "kucoin": "BTC/USDT",
    "bitstamp": "BTC/USD",
}


def create_exchange(exchange_id: str) -> ccxt.Exchange:
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


class DataQualityMonitor:
    """Monitor cross-exchange price consistency in real-time."""

    def __init__(
        self,
        exchange_ids: list[str],
        alert_threshold_pct: float = 0.5,
        output_dir: str = "data/data_quality",
    ):
        self.exchange_ids = exchange_ids
        self.alert_threshold = alert_threshold_pct / 100  # Convert to decimal
        self.output_dir = Path(output_dir)

        # Create exchange instances
        self.exchanges: dict[str, ccxt.Exchange] = {}
        for eid in exchange_ids:
            self.exchanges[eid] = create_exchange(eid)

        self.running = False
        self.tick_log: list[dict] = []
        self.alerts: list[dict] = []
        self.divergence_history: list[float] = []

    def _fetch_prices(self) -> dict[str, float | None]:
        """Fetch latest price from each exchange."""
        prices = {}
        for eid, exchange in self.exchanges.items():
            symbol = EXCHANGE_SYMBOLS[eid]
            try:
                ticker = exchange.fetch_ticker(symbol)
                prices[eid] = ticker["last"]
            except Exception as e:
                prices[eid] = None
        return prices

    def _calculate_divergence(self, prices: dict[str, float | None]) -> dict:
        """Calculate cross-exchange price divergence statistics."""
        valid = {k: v for k, v in prices.items() if v is not None}
        if len(valid) < 2:
            return {"valid_exchanges": len(valid)}

        values = list(valid.values())
        median_price = np.median(values)
        mean_price = np.mean(values)

        deviations = {}
        for eid, price in valid.items():
            dev_pct = (price - median_price) / median_price * 100
            deviations[eid] = dev_pct

        max_spread = (max(values) - min(values)) / median_price * 100
        self.divergence_history.append(max_spread)

        # Find the most divergent pair
        exchanges = list(valid.keys())
        max_pair_spread = 0
        max_pair = ("", "")
        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                spread = abs(valid[exchanges[i]] - valid[exchanges[j]]) / median_price * 100
                if spread > max_pair_spread:
                    max_pair_spread = spread
                    max_pair = (exchanges[i], exchanges[j])

        return {
            "valid_exchanges": len(valid),
            "median_price": median_price,
            "mean_price": mean_price,
            "max_spread_pct": max_spread,
            "deviations": deviations,
            "max_pair": max_pair,
            "max_pair_spread_pct": max_pair_spread,
        }

    def run(self, duration_seconds: int = 0, poll_interval: float = 10.0):
        """Run the monitor.

        Args:
            duration_seconds: Run for this many seconds (0 = forever).
            poll_interval: Seconds between polls.
        """
        self.running = True
        start_time = time.time()

        # Prepare output
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        csv_path = self.output_dir / f"quality_{ts}.csv"
        json_path = self.output_dir / f"quality_{ts}_summary.json"

        exch_names = ", ".join(self.exchange_ids)
        print(f"\n{'='*70}")
        print(f"  DATA QUALITY MONITOR")
        print(f"  Exchanges: {exch_names}")
        print(f"  Alert threshold: {self.alert_threshold * 100:.2f}%")
        dur_str = f"{duration_seconds}s" if duration_seconds else "until Ctrl+C"
        print(f"  Duration: {dur_str}")
        print(f"  Output: {csv_path}")
        print(f"{'='*70}\n")

        # CSV header
        fieldnames = ["timestamp", "median_price", "max_spread_pct", "alert"]
        for eid in self.exchange_ids:
            fieldnames.extend([f"{eid}_price", f"{eid}_dev_pct"])
        fieldnames.append("max_pair")

        csv_file = open(csv_path, "w", newline="")
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        tick_count = 0

        try:
            while self.running:
                if duration_seconds > 0 and (time.time() - start_time) >= duration_seconds:
                    print("\n  Duration limit reached.")
                    break

                prices = self._fetch_prices()
                div = self._calculate_divergence(prices)

                now = datetime.now(timezone.utc).isoformat()
                is_alert = div.get("max_spread_pct", 0) > self.alert_threshold * 100

                if is_alert:
                    alert_info = {
                        "timestamp": now,
                        "spread_pct": div["max_spread_pct"],
                        "pair": div.get("max_pair", ("?", "?")),
                        "prices": {k: v for k, v in prices.items() if v is not None},
                    }
                    self.alerts.append(alert_info)

                # Build CSV row
                row = {
                    "timestamp": now,
                    "median_price": round(div.get("median_price", 0), 2),
                    "max_spread_pct": round(div.get("max_spread_pct", 0), 4),
                    "alert": is_alert,
                    "max_pair": f"{div.get('max_pair', ('', ''))[0]}-{div.get('max_pair', ('', ''))[1]}",
                }
                devs = div.get("deviations", {})
                for eid in self.exchange_ids:
                    row[f"{eid}_price"] = round(prices.get(eid, 0) or 0, 2)
                    row[f"{eid}_dev_pct"] = round(devs.get(eid, 0), 4)

                writer.writerow(row)
                csv_file.flush()
                self.tick_log.append(row)
                tick_count += 1

                # Console output
                alert_str = " *** ALERT ***" if is_alert else ""
                price_strs = []
                for eid in self.exchange_ids:
                    p = prices.get(eid)
                    d = devs.get(eid, 0)
                    if p is not None:
                        price_strs.append(f"{eid}:{p:.2f}({d:+.3f}%)")
                    else:
                        price_strs.append(f"{eid}:ERROR")

                spread = div.get("max_spread_pct", 0)
                print(
                    f"  [{tick_count:>4}] {' | '.join(price_strs)} "
                    f"| Spread:{spread:.4f}%{alert_str}"
                )

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\n\n  Ctrl+C received, shutting down...")

        finally:
            csv_file.close()
            self._write_summary(json_path, tick_count, start_time)

    def _write_summary(self, json_path: Path, tick_count: int, start_time: float):
        """Write session summary."""
        elapsed = time.time() - start_time
        divs = self.divergence_history

        summary = {
            "exchanges": self.exchange_ids,
            "alert_threshold_pct": self.alert_threshold * 100,
            "duration_seconds": round(elapsed, 1),
            "ticks": tick_count,
            "alerts": len(self.alerts),
            "divergence_stats": {
                "mean_max_spread_pct": np.mean(divs) if divs else 0,
                "median_max_spread_pct": np.median(divs) if divs else 0,
                "max_spread_pct": max(divs) if divs else 0,
                "min_spread_pct": min(divs) if divs else 0,
                "std_spread_pct": np.std(divs) if divs else 0,
                "p95_spread_pct": np.percentile(divs, 95) if divs else 0,
                "p99_spread_pct": np.percentile(divs, 99) if divs else 0,
            },
            "alert_details": self.alerts[:20],  # First 20 alerts
        }

        json_path.write_text(json.dumps(summary, indent=2, default=str))

        print(f"\n{'='*70}")
        print(f"  DATA QUALITY SUMMARY")
        print(f"{'='*70}")
        print(f"  Duration:          {elapsed:.0f}s ({elapsed/60:.1f} min)")
        print(f"  Ticks:             {tick_count}")
        print(f"  Alerts:            {len(self.alerts)}")
        if divs:
            ds = summary["divergence_stats"]
            print(f"  Mean spread:       {ds['mean_max_spread_pct']:.4f}%")
            print(f"  Median spread:     {ds['median_max_spread_pct']:.4f}%")
            print(f"  Max spread:        {ds['max_spread_pct']:.4f}%")
            print(f"  95th pctl spread:  {ds['p95_spread_pct']:.4f}%")
        print(f"  Saved:             {json_path}")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Monitor cross-exchange data quality")
    parser.add_argument(
        "--exchanges", nargs="+",
        default=["okx", "kucoin", "bitfinex"],
        choices=list(EXCHANGE_SYMBOLS),
    )
    parser.add_argument("--threshold", type=float, default=0.5, help="Alert threshold %%")
    parser.add_argument("--duration", type=int, default=0, help="Seconds to run (0=forever)")
    parser.add_argument("--interval", type=float, default=10.0, help="Poll interval (seconds)")
    parser.add_argument("--output", default="data/data_quality")
    args = parser.parse_args()

    monitor = DataQualityMonitor(
        exchange_ids=args.exchanges,
        alert_threshold_pct=args.threshold,
        output_dir=args.output,
    )

    def handler(sig, frame):
        monitor.running = False
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    monitor.run(duration_seconds=args.duration, poll_interval=args.interval)


if __name__ == "__main__":
    main()
