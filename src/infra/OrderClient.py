"""Order client for managing MT5 orders and order operations."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Mapping, Tuple, Union, Literal
from datetime import datetime
import polars as pl

from .OrderData import OrderData
from .mtBase import mtBase
from .mt_helper import get_orders_helper

import logging
logger = logging.getLogger(__name__)

class OrderClient:
    """High-level client for managing MT5 orders and order operations."""

    def __init__(self, base: mtBase) -> None:
        self._base = base
        self._orders: List[OrderData] = []
        self._orders_df: Optional[pl.DataFrame] = None

    @property
    def base(self) -> mtBase:
        if self._base is None:
            raise RuntimeError("mtBase instance is required for MT5 operations.")
        return self._base

    @base.setter
    def base(self, value: mtBase) -> None:
        self._base = value

    def to_request_dict(self, order: OrderData) -> Dict:
        """Convert an OrderData object to a dictionary suitable for MT5 order functions."""
        import MetaTrader5 as mt5
        
        # Build the basic request dictionary with required fields
        request = {
            "symbol": order.symbol,
            "volume": float(order.volume),
            "type": order.type,
            "price": order.price,
            "magic": int(order.magic)
        }
        
        # Add action - use provided action or derive from order type
        if order.action is not None:
            request["action"] = order.action
        else:
            if order.type in [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL]:
                request["action"] = mt5.TRADE_ACTION_DEAL
            else:
                request["action"] = mt5.TRADE_ACTION_PENDING
        
        # Add time type - use provided or default to GTC
        if order.type_time is not None:
            request["type_time"] = order.type_time
        else:
            request["type_time"] = mt5.ORDER_TIME_GTC
        
        # Add filling type - use provided or default to appropriate type
        if order.type_filling is not None:
            request["type_filling"] = order.type_filling
        else:
            # Market orders typically use different filling than pending orders
            if order.type in [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL]:
                request["type_filling"] = mt5.ORDER_FILLING_FOK
            else:
                request["type_filling"] = mt5.ORDER_FILLING_RETURN
        
        # Add optional fields if they exist
        if order.sl is not None:
            request["sl"] = order.sl
            
        if order.tp is not None:
            request["tp"] = order.tp
            
        if order.comment is not None:
            request["comment"] = order.comment
        else:
            request["comment"] = f"darwinexclient order {order.symbol}"
            
        if order.deviation is not None:
            request["deviation"] = int(order.deviation)
        
        return request

    def get_orders(
        self,
        symbol: Optional[str] = None,
        magic: Optional[int] = None
    ) -> List[OrderData]:
        """Get all pending orders, optionally filtered by symbol and/or magic number."""
        orders = self._orders
        if symbol is not None:
            orders = [o for o in orders if o.symbol == symbol]
        if magic is not None:
            orders = [o for o in orders if o.magic == magic]
        return orders

    def get_orders_by_symbol(self, symbol: str) -> List[OrderData]:
        """Get all pending orders for a specific symbol."""
        return self.get_orders(symbol=symbol)

    def get_orders_by_magic(self, magic: int) -> List[OrderData]:
        """Get all pending orders with a specific magic number."""
        return self.get_orders(magic=magic)

    def get_orders_dataframe(self) -> Optional[pl.DataFrame]:
        """Get current orders as a Polars DataFrame."""
        return self._orders_df

    def count_orders(self, symbol: Optional[str] = None, magic: Optional[int] = None) -> int:
        """Count pending orders, optionally filtered by symbol and/or magic number."""
        orders = self.get_orders(symbol=symbol, magic=magic)
        return len(orders)

    def has_orders(self, symbol: Optional[str] = None, magic: Optional[int] = None) -> bool:
        """Check if there are any pending orders, optionally filtered by symbol and/or magic number."""
        return self.count_orders(symbol=symbol, magic=magic) > 0

    def to_order_data(self, row: Dict) -> OrderData:
        """Convert a DataFrame row to OrderData object."""
        return OrderData(
            type=row["type"],
            volume=row["volume_initial"],  # Use initial volume as the volume
            price=row["price_open"],       # Use open price as the price
            symbol=row["symbol"],
            magic=row["magic"],
            ticket=row["ticket"],
            time_setup=row.get("time_dt"),  # Converted datetime
            sl=row.get("sl", 0.0) if row.get("sl", 0.0) != 0.0 else None,
            tp=row.get("tp", 0.0) if row.get("tp", 0.0) != 0.0 else None,
            comment=row.get("comment")
        )

    def log_orders(self, orders: List[OrderData] | OrderData, indent: int = 2) -> None:
        indent_str = ' ' * indent
        if orders is None or (isinstance(orders, (list, tuple)) and not orders):
            logger.info("No orders to log.")
            return
        if not isinstance(orders, (list, tuple)):
            orders = [orders]

        logger.info(f"{indent_str}Loaded {len(orders)} orders:")
        for i, o in enumerate(orders, 1):
            tkt = getattr(o, "ticket", None);         tkt_s = "" if tkt is None else str(tkt)
            ts  = getattr(o, "time_setup", None)
            ts_s = "" if not ts else (ts.strftime("%d-%b-%Y %H:%M:%S") if isinstance(ts, (datetime.date, datetime.datetime)) else str(ts))
            typ = getattr(o, "type", None);           typ_s = "" if typ is None else str(typ)
            vol = getattr(o, "volume", None);         vol_s = "" if vol is None else f"{vol:.2f}"
            prc = getattr(o, "price", None);          prc_s = "" if prc is None else f"{prc:.4f}"
            sl  = getattr(o, "sl", None);             sl_s  = "" if sl  is None else f"{sl:.4f}"
            tp  = getattr(o, "tp", None);             tp_s  = "" if tp  is None else f"{tp:.4f}"
            sym = getattr(o, "symbol", None) or ""
            cmt = getattr(o, "comment", None) or ""
            mag = getattr(o, "magic", None);          mag_s = "" if mag is None else str(mag)
            act = getattr(o, "action", None);         act_s = "" if act is None else str(act)
            ttm = getattr(o, "type_time", None);      ttm_s = "" if ttm is None else str(ttm)
            tfl = getattr(o, "type_filling", None);   tfl_s = "" if tfl is None else str(tfl)
            dev = getattr(o, "deviation", None);      dev_s = "" if dev is None else str(dev)

            logger.info((
                f"\n{indent_str}Order {i}:"
                f"\n{indent_str}  Ticket: {tkt_s}"
                f"\n{indent_str}  Time setup: {ts_s}"
                f"\n{indent_str}  Type: {typ_s}"
                f"\n{indent_str}  Volume: {vol_s}"
                f"\n{indent_str}  Price: {prc_s}"
                f"\n{indent_str}  SL: {sl_s}"
                f"\n{indent_str}  TP: {tp_s}"
                f"\n{indent_str}  Symbol: {sym}"
                f"\n{indent_str}  Comment: {cmt}"
                f"\n{indent_str}  Magic: {mag_s}"
                f"\n{indent_str}  Action: {act_s}"
                f"\n{indent_str}  Time type: {ttm_s}"
                f"\n{indent_str}  Filling: {tfl_s}"
                f"\n{indent_str}  Deviation: {dev_s}"
            ).strip())