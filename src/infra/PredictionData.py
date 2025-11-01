"""
Prediction data container for trading predictions.

This module provides the PredictionData class for storing trading prediction data.
"""
from typing import Dict, Any, Optional
from datetime import date


class PredictionData:
    """
    Container for prediction data from JSON files.
    
    Attributes:
        symbol (str): Trading pair symbol.
            Example: "NVDA", "MU", "AUDUSD"
        
        last_training_day (date): The last day used in model training.
            Example: date(2025, 10, 14) for October 14th, 2025
        
        last_close_price (float): The closing price on the last training day.
            Example: 1.0845 for EUR/USD at $1.0845
        
        n_trading_days (int): Number of trading days for the prediction horizon.
            Example: 5 (predicting 5 days ahead)
        
        score (float): Score, typically positive.
            Example: 0.73
        
        magic (int): Magic number derived from symbol, date, and trading days.
            Unique identifier for this prediction instance.
        
        sl_pct (float, optional): Stop loss percentage as a positive decimal.
            Example: 0.1 (10% stop loss), defaults to None if not provided
        
        tp_pct (float, optional): Take profit percentage as a positive decimal.
            Example: 0.1 (10% take profit), defaults to None if not provided
        
        source (str, optional): Source file name for this prediction.
            Example: "prediction_debug_14oct2025_002.json", defaults to None if not provided
    """
    
    def __init__(
        self,
        symbol: str,
        last_training_day: date,
        last_close_price: float,
        n_trading_days: int,
        score: float,
        magic: int,
        sl_pct: Optional[float] = None,
        tp_pct: Optional[float] = None,
        source: Optional[str] = None
    ):
        self.symbol = symbol
        self.last_training_day = last_training_day
        self.last_close_price = last_close_price
        self.n_trading_days = n_trading_days
        self.score = score
        self.magic = magic
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
        self.source = source
    
    def __repr__(self) -> str:
        return (f"PredictionData(symbol='{self.symbol}', "
                f"last_training_day='{self.last_training_day}', "
                f"last_close_price={self.last_close_price}, "
                f"n_trading_days={self.n_trading_days}, "
                f"score={self.score}, "
                f"magic={self.magic}, "
                f"sl_pct={self.sl_pct}, "
                f"tp_pct={self.tp_pct}, "
                f"source={self.source})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            'symbol': self.symbol,
            'last_training_day': self.last_training_day.isoformat(),
            'last_close_price': self.last_close_price,
            'n_trading_days': self.n_trading_days,
            'score': self.score,
            'magic': self.magic
        }
        
        # Only include sl_pct and tp_pct if they are not None
        if self.sl_pct is not None:
            result['sl_pct'] = self.sl_pct
        if self.tp_pct is not None:
            result['tp_pct'] = self.tp_pct
        if self.source is not None:
            result['source'] = self.source
            
        return result