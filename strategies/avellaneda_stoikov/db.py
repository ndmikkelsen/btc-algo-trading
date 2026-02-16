"""PostgreSQL instance tracking for paper trading runs.

Buffers fills and round-trips in memory during trading, then writes
everything in a single transaction at shutdown via finalize_instance().

Fully optional: if DATABASE_URL is not set, all methods silently no-op.

Requires: sqlalchemy, psycopg2-binary
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import UUID


metadata = MetaData()

trading_instances = Table(
    "trading_instances",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    # Model parameters
    Column("gamma", Float),
    Column("kappa", Float),
    Column("arrival_rate", Float),
    Column("min_spread", Float),
    Column("max_spread", Float),
    Column("quote_interval", Float),
    Column("fee_tier", String(32)),
    Column("leverage", Integer),
    Column("use_regime_filter", Boolean),
    Column("capital", Float),
    Column("order_pct", Float),
    Column("symbol", String(32)),
    Column("exchange", String(32)),
    Column("is_dry_run", Boolean),
    # Session results
    Column("start_time", DateTime(timezone=True)),
    Column("end_time", DateTime(timezone=True)),
    Column("duration_seconds", Float),
    Column("final_price", Float),
    Column("final_inventory", Float),
    Column("final_cash", Float),
    Column("total_pnl", Float),
    Column("realized_pnl", Float),
    Column("total_fees", Float),
    Column("trades_count", Integer),
    Column("closed_trades", Integer),
    Column("tick_rejections", Integer),
    Column("error_count", Integer),
    Column("log_file", String(512)),
)

fills = Table(
    "fills",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column(
        "instance_id",
        UUID(as_uuid=True),
        ForeignKey("trading_instances.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("order_id", String(128)),
    Column("side", String(8)),
    Column("qty", Float),
    Column("price", Float),
    Column("fee", Float),
    Column("inventory_after", Float),
    Column("filled_at", DateTime(timezone=True)),
)

round_trips = Table(
    "round_trips",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column(
        "instance_id",
        UUID(as_uuid=True),
        ForeignKey("trading_instances.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("entry_side", String(8)),
    Column("entry_price", Float),
    Column("exit_price", Float),
    Column("qty", Float),
    Column("pnl", Float),
    Column("hold_time_seconds", Float),
    Column("closed_at", DateTime(timezone=True)),
)


class TradingDB:
    """Buffer fills/round-trips in memory, flush to PostgreSQL on finalize.

    If DATABASE_URL is not set, every method is a silent no-op so the trader
    works identically to before this module existed.
    """

    def __init__(self) -> None:
        self._engine = None
        self._fill_buffer: List[Dict] = []
        self._rt_buffer: List[Dict] = []

        url = os.getenv("DATABASE_URL")
        if not url:
            return

        try:
            self._engine = create_engine(url, pool_pre_ping=True)
            metadata.create_all(self._engine)
        except Exception as exc:
            print(f"[TradingDB] Could not connect to database: {exc}")
            self._engine = None

    @property
    def enabled(self) -> bool:
        return self._engine is not None

    def add_fill(
        self,
        order_id: str,
        side: str,
        qty: float,
        price: float,
        fee: float,
        inventory_after: float,
    ) -> None:
        """Buffer a fill event (written on finalize)."""
        if not self.enabled:
            return
        self._fill_buffer.append(
            {
                "id": uuid.uuid4(),
                "order_id": order_id,
                "side": side,
                "qty": qty,
                "price": price,
                "fee": fee,
                "inventory_after": inventory_after,
                "filled_at": datetime.now(timezone.utc),
            }
        )

    def add_round_trip(
        self,
        entry_side: str,
        entry_price: float,
        exit_price: float,
        qty: float,
        pnl: float,
        hold_time_seconds: float,
    ) -> None:
        """Buffer a round-trip close event (written on finalize)."""
        if not self.enabled:
            return
        self._rt_buffer.append(
            {
                "id": uuid.uuid4(),
                "entry_side": entry_side,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "qty": qty,
                "pnl": pnl,
                "hold_time_seconds": hold_time_seconds,
                "closed_at": datetime.now(timezone.utc),
            }
        )

    def finalize_instance(self, data: Dict) -> Optional[uuid.UUID]:
        """Write instance row + all buffered fills/round-trips in one transaction.

        Returns the instance UUID on success, None if DB is disabled or write fails.
        """
        if not self.enabled:
            return None

        instance_id = uuid.uuid4()
        data["id"] = instance_id

        try:
            with self._engine.begin() as conn:
                conn.execute(trading_instances.insert().values(data))

                if self._fill_buffer:
                    for f in self._fill_buffer:
                        f["instance_id"] = instance_id
                    conn.execute(fills.insert(), self._fill_buffer)

                if self._rt_buffer:
                    for rt in self._rt_buffer:
                        rt["instance_id"] = instance_id
                    conn.execute(round_trips.insert(), self._rt_buffer)

            fill_count = len(self._fill_buffer)
            rt_count = len(self._rt_buffer)
            self._fill_buffer.clear()
            self._rt_buffer.clear()

            print(
                f"[TradingDB] Saved instance {instance_id} "
                f"({fill_count} fills, {rt_count} round-trips)"
            )
            return instance_id

        except Exception as exc:
            print(f"[TradingDB] Failed to save instance: {exc}")
            return None
