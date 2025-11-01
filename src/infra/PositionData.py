"""
Position data container for MT5 trading positions.

This module provides the PositionData class for storing MT5 position information.
"""
from typing import Dict, Any, Optional
from datetime import datetime

class PositionData:
    """
    Container for MT5 position data.
    
    Attributes:
        ticket (int): Unique position ticket number from MT5.
        time (datetime): Position open timestamp.
        time_msc (int): Position open time in milliseconds.
        type (int): Position type (POSITION_TYPE_BUY=0 or POSITION_TYPE_SELL=1).
        magic (int): Magic number for position identification.
        reason (int): Position open reason.
        volume (float): Position volume in lots.
        price_open (float): Position open price.
        sl (float, optional): Stop loss price.
        tp (float, optional): Take profit price.
        price_current (float): Current market price for the symbol.
        profit (float): Current profit/loss in account currency.
        symbol (str): Trading symbol.
        comment (str, optional): Position comment.
    """
    
    def __init__(
        self,
        ticket: int,
        time: datetime,
        time_msc: int,
        type: int,
        magic: int,
        reason: int,
        volume: float,
        price_open: float,
        price_current: float,
        profit: float,
        symbol: str,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: Optional[str] = None
    ):
        self.ticket = ticket
        self.time = time
        self.time_msc = time_msc
        self.type = type
        self.magic = magic
        self.reason = reason
        self.volume = volume
        self.price_open = price_open
        self.sl = sl
        self.tp = tp
        self.price_current = price_current
        self.profit = profit
        self.symbol = symbol
        self.comment = comment
    
    def __repr__(self) -> str:
        return (f"PositionData(ticket={self.ticket}, "
                f"symbol='{self.symbol}', "
                f"type={self.type}, "
                f"volume={self.volume}, "
                f"price_open={self.price_open}, "
                f"price_current={self.price_current}, "
                f"profit={self.profit}, "
                f"sl={self.sl}, "
                f"tp={self.tp}, "
                f"magic={self.magic})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            'ticket': self.ticket,
            'time': self.time.isoformat() if self.time else None,
            'time_msc': self.time_msc,
            'type': self.type,
            'magic': self.magic,
            'reason': self.reason,
            'volume': self.volume,
            'price_open': self.price_open,
            'price_current': self.price_current,
            'profit': self.profit,
            'symbol': self.symbol
        }
        
        # Only include optional fields if they are not None
        if self.sl is not None:
            result['sl'] = self.sl
        if self.tp is not None:
            result['tp'] = self.tp
        if self.comment is not None:
            result['comment'] = self.comment
            
        return result
    
    @property
    def is_long(self) -> bool:
        """Check if this is a long (buy) position."""
        return self.type == 0  # POSITION_TYPE_BUY
    
    @property
    def is_short(self) -> bool:
        """Check if this is a short (sell) position."""
        return self.type == 1  # POSITION_TYPE_SELL
    
    @property
    def is_profitable(self) -> bool:
        """Check if the position is currently profitable."""
        return self.profit > 0
    
    @property
    def total_pnl(self) -> float:
        """Get total profit/loss."""
        return self.profit
    
    @property
    def unrealized_pips(self) -> float:
        """Calculate unrealized profit/loss in pips (basic calculation)."""
        if self.is_long:
            return self.price_current - self.price_open
        else:
            return self.price_open - self.price_current
    
    @property
    def has_sl(self) -> bool:
        """Check if position has stop loss set."""
        return self.sl is not None and self.sl > 0
    
    @property
    def has_tp(self) -> bool:
        """Check if position has take profit set."""
        return self.tp is not None and self.tp > 0