"""
Prediction file parser for extracting trading data from JSON files.

This module provides functionality to parse prediction JSON files and extract
variables that can be used with the place_market_order_helper function.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import json
import glob
from datetime import datetime, timezone, date
import polars as pl


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
        
        sl_pct (float, optional): Stop loss percentage as a positive decimal.
            Example: 0.1 (10% stop loss), defaults to None if not provided
        
        tp_pct (float, optional): Take profit percentage as a positive decimal.
            Example: 0.1 (10% take profit), defaults to None if not provided
    """
    
    def __init__(
        self,
        symbol: str,
        last_training_day: date,
        last_close_price: float,
        n_trading_days: int,
        score: float,
        sl_pct: Optional[float] = None,
        tp_pct: Optional[float] = None
    ):
        self.symbol = symbol
        self.last_training_day = last_training_day
        self.last_close_price = last_close_price
        self.n_trading_days = n_trading_days
        self.score = score
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
    
    def __repr__(self) -> str:
        return (f"PredictionData(symbol='{self.symbol}', "
                f"last_training_day='{self.last_training_day}', "
                f"last_close_price={self.last_close_price}, "
                f"n_trading_days={self.n_trading_days}, "
                f"score={self.score}, "
                f"sl_pct={self.sl_pct}, "
                f"tp_pct={self.tp_pct})")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            'symbol': self.symbol,
            'last_training_day': self.last_training_day.isoformat(),
            'last_close_price': self.last_close_price,
            'n_trading_days': self.n_trading_days,
            'score': self.score
        }
        
        # Only include sl_pct and tp_pct if they are not None
        if self.sl_pct is not None:
            result['sl_pct'] = self.sl_pct
        if self.tp_pct is not None:
            result['tp_pct'] = self.tp_pct
            
        return result


class PredictionParser:
    """Parser for prediction JSON files."""
    
    def __init__(self, predictions_dir: Union[str, Path] = "predictions"):
        """
        Initialize the parser.
        
        Args:
            predictions_dir: Directory containing prediction JSON files.
        """
        self.predictions_dir = Path(predictions_dir)
    
    @staticmethod
    def _parse_iso_date(date_str: str) -> date:
        """
        Parse an ISO 8601 datetime string (e.g., '2025-10-14T00:00:00Z')
        and return the calendar date (normalized to UTC).

        Raises:
            ValueError: if parsing fails or the timezone is missing.
        """
        s = (date_str or "").strip()
        try:
            # Python 3.11+ handles 'Z'; fall back for older versions
            try:
                dt = datetime.fromisoformat(s)
            except ValueError:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))

            if dt.tzinfo is None:
                raise ValueError("Timezone offset or 'Z' is required.")

            return dt.astimezone(timezone.utc).date()
        except Exception as e:
            raise ValueError(f"Failed to parse ISO 8601 date '{date_str}': {e}")
    
    def find_prediction_files(self, group: Optional[str] = None) -> List[Path]:
        """
        Find prediction JSON files matching the pattern.
        
        Args:
            group: Optional group name to filter files (e.g., 'debug').
                  If None, returns all prediction files.
        
        Returns:
            List of Path objects for matching prediction files.
        """
        if group:
            pattern = f"prediction_{group}_*.json"
        else:
            pattern = "prediction_*.json"
        
        search_path = self.predictions_dir / pattern
        files = glob.glob(str(search_path))
        return [Path(f) for f in sorted(files)]
    
    def parse_json_file(self, file_path: Union[str, Path]) -> List[PredictionData]:
        """
        Parse a single JSON prediction file.
        
        Args:
            file_path: Path to the JSON file.
        
        Returns:
            List of PredictionData objects.
        
        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the JSON is invalid.
            ValueError: If required fields are missing.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Prediction file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both single dict and list of dicts
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            raise ValueError(f"JSON data must be a dict or list of dicts, got {type(data)}")
        
        predictions = []
        for item in data:
            if not isinstance(item, dict):
                raise ValueError(f"Each prediction must be a dict, got {type(item)}")
            
            # Validate required fields
            required_fields = ['symbol', 'last_training_day', 'last_close_price', 'n_trading_days', 'score']
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Extract optional fields with defaults
            sl_pct = item.get('sl_pct')
            tp_pct = item.get('tp_pct')
            
            # Convert to float if present and not None
            if sl_pct is not None:
                sl_pct = float(sl_pct)
            if tp_pct is not None:
                tp_pct = float(tp_pct)
            
            pred = PredictionData(
                symbol=str(item['symbol']),
                last_training_day=self._parse_iso_date(str(item['last_training_day'])),
                last_close_price=float(item['last_close_price']),
                n_trading_days=int(item['n_trading_days']),
                score=float(item['score']),
                sl_pct=sl_pct,
                tp_pct=tp_pct
            )
            predictions.append(pred)
        
        return predictions