"""
Prediction file parser for extracting trading data from JSON files.

This module provides functionality to parse prediction JSON files and extract
variables that can be used with the placing orders function.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import json
import glob
from datetime import datetime, timezone, date
import polars as pl

from .PredictionData import PredictionData
from ..common import magic_from


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
            
            # Create a temporary instance to calculate magic
            temp_pred = PredictionData(
                symbol=str(item['symbol']),
                last_training_day=self._parse_iso_date(str(item['last_training_day'])),
                last_close_price=float(item['last_close_price']),
                n_trading_days=int(item['n_trading_days']),
                score=float(item['score']),
                magic=0,  # Temporary value
                sl_pct=sl_pct,
                tp_pct=tp_pct
            )
            
            # Calculate magic and create final instance
            magic = magic_from(temp_pred)
            pred = PredictionData(
                symbol=temp_pred.symbol,
                last_training_day=temp_pred.last_training_day,
                last_close_price=temp_pred.last_close_price,
                n_trading_days=temp_pred.n_trading_days,
                score=temp_pred.score,
                magic=magic,
                sl_pct=sl_pct,
                tp_pct=tp_pct,
                source=file_path.name
            )
            predictions.append(pred)
        
        return predictions