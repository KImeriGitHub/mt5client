"""Position client for managing MT5 positions and position operations."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import polars as pl
import MetaTrader5 as mt5

from .PositionData import PositionData
from .mtBase import mtBase

import logging
logger = logging.getLogger(__name__)


class PositionClient:
    """High-level client for managing MT5 positions and position operations."""

    def __init__(self, base: mtBase) -> None:
        self._base = base
        self._positions: List[PositionData] = []
        self._positions_df: Optional[pl.DataFrame] = None

    @property
    def base(self) -> mtBase:
        if self._base is None:
            raise RuntimeError("mtBase instance is required for MT5 operations.")
        return self._base

    @base.setter
    def base(self, value: mtBase) -> None:
        self._base = value

    def get_positions(self, symbol: Optional[str] = None, magic: Optional[int] = None) -> List[PositionData]:
        """
        Get current open positions, optionally filtered by symbol and/or magic number.
        
        Args:
            symbol: Optional symbol filter (e.g., "EURUSD")
            magic: Optional magic number filter
            
        Returns:
            List of PositionData objects representing current positions
        """
        positions_df = self.base.get_positions_df()
        
        if positions_df is None or positions_df.is_empty():
            self._positions = []
            self._positions_df = None
            return []

        # Apply filters
        if symbol is not None:
            positions_df = positions_df.filter(pl.col("symbol") == symbol)
        
        if magic is not None:
            positions_df = positions_df.filter(pl.col("magic") == magic)

        # Convert to PositionData objects
        positions = []
        for row in positions_df.iter_rows(named=True):
            position_data = self._row_to_position_data(row)
            positions.append(position_data)

        self._positions = positions
        self._positions_df = self._filter_noisy_columns(positions_df)
        return positions

    def get_positions_by_symbol(self, symbol: str) -> List[PositionData]:
        """Get all open positions for a specific symbol."""
        return self.get_positions(symbol=symbol)

    def get_positions_by_magic(self, magic: int) -> List[PositionData]:
        """Get all open positions with a specific magic number."""
        return self.get_positions(magic=magic)

    def get_position_by_ticket(self, ticket: int) -> Optional[PositionData]:
        """Get a specific position by ticket number."""
        positions = self.get_positions()
        for position in positions:
            if position.ticket == ticket:
                return position
        return None

    def close_position_request(self, pos: PositionData, deviation_pts: int = 10, magic: int = 0) -> Dict:
        """
        Close an open position by ticket number.
        
        Args:
            ticket: Position ticket number to close
            deviation_pts: Maximum execution deviation in points
            magic: Magic number to tag the closing order
            
        Returns:
            MT5 order result object from position closure
        """
        opp_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": opp_type,
            "position": pos.ticket,
            "deviation": deviation_pts,
            "magic": magic,
            "comment": f"Closing position {pos.ticket}",
            "type_filling": mt5.ORDER_FILLING_FOK,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        return request

    def modify_position(
        self,
        ticket: int,
        sl: Optional[float] = None,
        tp: Optional[float] = None
    ) -> Dict:
        """
        Modify stop loss and/or take profit for an existing position.
        
        Args:
            ticket: Position ticket number to modify
            sl: New stop loss price (None to remove)
            tp: New take profit price (None to remove)
            
        Returns:
            MT5 order result object from modification
        """
        import MetaTrader5 as mt5
        
        # Get position details
        position = self.get_position_by_ticket(ticket)
        if position is None:
            raise ValueError(f"Position with ticket {ticket} not found")
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": position.symbol,
        }
        
        if sl is not None:
            request["sl"] = sl
        if tp is not None:
            request["tp"] = tp
        
        result = mt5.order_send(request)
        return result

    def _filter_noisy_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Filter out noisy columns that are not needed for trading operations."""
        noisy_columns = ['time_update', 'time_msc', 'time_update_msc', 'external_id']
        columns_to_keep = [col for col in df.columns if col not in noisy_columns]
        return df.select(columns_to_keep)

    def log_positions(self, positions: List[PositionData] | PositionData, indent: int = 2) -> None:
        indent_str = ' ' * indent
        if positions is None or (isinstance(positions, (list, tuple)) and not positions):
            logger.info("No positions to log.")
            return
        if not isinstance(positions, (list, tuple)):
            positions = [positions]

        logger.info(f"{indent_str}Loaded {len(positions)} positions:")
        for i, pos in enumerate(positions, 1):
            tkt = getattr(pos, "ticket", None);          tkt_s = "" if tkt is None else str(tkt)
            t   = getattr(pos, "time", None)
            t_s = "" if not t else (t.strftime("%d-%b-%Y %H:%M:%S") if isinstance(t, (datetime)) else str(t))
            typ = getattr(pos, "type", None);            typ_s = "" if typ is None else ("LONG" if typ == 0 else "SHORT" if typ == 1 else str(typ))
            vol = getattr(pos, "volume", None);          vol_s = "" if vol is None else f"{vol:.2f}"
            po  = getattr(pos, "price_open", None);      po_s  = "" if po  is None else f"{po:.4f}"
            pc  = getattr(pos, "price_current", None);   pc_s  = "" if pc  is None else f"{pc:.4f}"
            pnl = getattr(pos, "profit", None);          pnl_s = "" if pnl is None else f"{pnl:.2f}"
            sl  = getattr(pos, "sl", None);              sl_s  = "" if sl  is None else f"{sl:.4f}"
            tp  = getattr(pos, "tp", None);              tp_s  = "" if tp  is None else f"{tp:.4f}"
            sym = getattr(pos, "symbol", None) or ""
            cmt = getattr(pos, "comment", None) or ""
            mag = getattr(pos, "magic", None);           mag_s = "" if mag is None else str(mag)

            logger.info((
                f"\n{indent_str}Position {i}:"
                f"\n{indent_str}  Ticket: {tkt_s}"
                f"\n{indent_str}  Time: {t_s}"
                f"\n{indent_str}  Type: {typ_s}"
                f"\n{indent_str}  Volume: {vol_s}"
                f"\n{indent_str}  Open Price: {po_s}"
                f"\n{indent_str}  Current Price: {pc_s}"
                f"\n{indent_str}  P&L: {pnl_s}"
                f"\n{indent_str}  SL: {sl_s}"
                f"\n{indent_str}  TP: {tp_s}"
                f"\n{indent_str}  Symbol: {sym}"
                f"\n{indent_str}  Comment: {cmt}"
                f"\n{indent_str}  Magic: {mag_s}"
            ).strip())

    def _row_to_position_data(self, row: Dict) -> PositionData:
        """Convert a DataFrame row to PositionData object."""
        return PositionData(
            ticket=row["ticket"],
            time=row.get("time_dt"),  # Converted datetime
            time_msc=row["time_msc"],
            type=row["type"],
            magic=row["magic"],
            reason=row.get("reason", 0),
            volume=row["volume"],
            price_open=row["price_open"],
            price_current=row.get("price_current", 0.0),
            profit=row.get("profit", 0.0),
            symbol=row["symbol"],
            sl=row.get("sl", 0.0) if row.get("sl", 0.0) != 0.0 else None,
            tp=row.get("tp", 0.0) if row.get("tp", 0.0) != 0.0 else None,
            comment=row.get("comment")
        )