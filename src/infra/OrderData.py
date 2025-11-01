"""
Order data container for MT5 trading orders.

This module provides the OrderData class for storing MT5 order information.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import MetaTrader5 as mt5


class OrderData:
    """
    Container for MT5 order data.
    
    Attributes:
        ticket (int, optional): Unique order ticket number from MT5.
        time_setup (datetime, optional): Order setup timestamp.
        type (int): Order type. 
            Valid values: mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL, 
                mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT.
        volume (float): Order volume in lots (e.g., 0.1 for 0.1 lot, 1.0 for 1 lot).
        price (float): Order price in quote currency (e.g., 1.2345 for EUR/USD).
        sl (float, optional): Stop loss price in quote currency (e.g., 1.2300).
        tp (float, optional): Take profit price in quote currency (e.g., 1.2400).
        symbol (str): Trading symbol (e.g., "EURUSD", "GBPJPY").
        comment (str, optional): Order comment.
        magic (int): Magic number for order identification.
        action (int, optional): Order action type. 
            Valid values: mt5.TRADE_ACTION_DEAL, mt5.TRADE_ACTION_PENDING.
        type_time (int, optional): Order time type. 
            Valid values: mt5.ORDER_TIME_GTC.
        type_filling (int, optional): Order filling type. 
            Valid values: mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN.
        deviation (int, optional): Maximum price deviation in points (e.g., 10 for 10 points).
    """

    def __init__(
        self,
        type: int,
        volume: float,
        price: float,
        symbol: str,
        magic: int,
        ticket: Optional[int] = None,
        time_setup: Optional[datetime] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        comment: Optional[str] = None, # MAX 31 chars
        action: Optional[int] = None,
        type_time: Optional[int] = None,
        type_filling: Optional[int] = None,
        deviation: Optional[int] = None
    ):
        # Validate all MT5 parameters
        self._validate_parameters(type, action, type_time, type_filling, comment)
        
        self.ticket = ticket
        self.time_setup = time_setup
        self.type = type
        self.volume = volume
        self.price = price
        self.sl = sl
        self.tp = tp
        self.symbol = symbol
        self.comment = comment
        self.magic = magic
        self.action = action
        self.type_time = type_time
        self.type_filling = type_filling
        self.deviation = deviation
    
    def __repr__(self) -> str:
        return (f"OrderData(ticket={self.ticket}, "
                f"symbol='{self.symbol}', "
                f"type={self.type}, "
                f"volume={self.volume}, "
                f"price={self.price}, "
                f"sl={self.sl}, "
                f"tp={self.tp}, "
                f"magic={self.magic})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            'type': self.type,
            'volume': self.volume,
            'price': self.price,
            'symbol': self.symbol,
            'magic': self.magic
        }
        
        # Only include optional fields if they are not None
        if self.ticket is not None:
            result['ticket'] = self.ticket
        if self.time_setup is not None:
            result['time_setup'] = self.time_setup.isoformat()
        if self.sl is not None:
            result['sl'] = self.sl
        if self.tp is not None:
            result['tp'] = self.tp
        if self.comment is not None:
            result['comment'] = self.comment
        if self.action is not None:
            result['action'] = self.action
        if self.type_time is not None:
            result['type_time'] = self.type_time
        if self.type_filling is not None:
            result['type_filling'] = self.type_filling
        if self.deviation is not None:
            result['deviation'] = self.deviation
            
        return result
    
    def _validate_parameters(
        self,
        type: int,
        action: Optional[int] = None,
        type_time: Optional[int] = None,
        type_filling: Optional[int] = None,
        comment: Optional[str] = None
    ) -> None:
        """
        Validate MT5 order parameters.
        
        Args:
            type: Order type to validate
            action: Order action type to validate (optional)
            type_time: Order time type to validate (optional)
            type_filling: Order filling type to validate (optional)
            comment: Order comment to validate (optional)
            
        Raises:
            ValueError: If any parameter has an invalid value
        """
        # Validate order type
        valid_types = [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL, 
                      mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT]
        if type not in valid_types:
            raise ValueError(f"Invalid order type: {type}. Must be one of {valid_types}")
        
        # Validate action if provided
        if action is not None:
            valid_actions = [mt5.TRADE_ACTION_DEAL, mt5.TRADE_ACTION_PENDING]
            if action not in valid_actions:
                raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")
        
        # Validate type_time if provided
        if type_time is not None:
            valid_time_types = [mt5.ORDER_TIME_GTC, mt5.ORDER_TIME_DAY]
            if type_time not in valid_time_types:
                raise ValueError(f"Invalid type_time: {type_time}. Must be one of {valid_time_types}")
        
        # Validate type_filling if provided
        if type_filling is not None:
            valid_filling_types = [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, 
                                 mt5.ORDER_FILLING_RETURN]
            if type_filling not in valid_filling_types:
                raise ValueError(f"Invalid type_filling: {type_filling}. Must be one of {valid_filling_types}")
        
        # Validate comment length
        if comment is not None and len(comment) > 31:
            raise ValueError(f"Comment must be at most 31 characters, got {len(comment)}: '{comment}'")
    
    @property
    def is_buy_order(self) -> bool:
        """Check if this is a buy order (any buy type)."""
        # Assuming MT5 order type constants - adjust based on actual values
        buy_types = [0, 2, 4]  # ORDER_TYPE_BUY, ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_BUY_STOP
        return self.type in buy_types
    
    @property
    def is_sell_order(self) -> bool:
        """Check if this is a sell order (any sell type)."""
        # Assuming MT5 order type constants - adjust based on actual values
        sell_types = [1, 3, 5]  # ORDER_TYPE_SELL, ORDER_TYPE_SELL_LIMIT, ORDER_TYPE_SELL_STOP
        return self.type in sell_types
    
