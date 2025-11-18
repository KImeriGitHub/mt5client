from typing import List
from datetime import date

from .infra.PositionData import PositionData
from .infra.PredictionData import PredictionData
from .common import calculate_trading_day


class Checks:
    def __init__(self):
        pass

    @staticmethod
    def preds_in_positions(predictions: List[PredictionData], positions: List[PositionData]) -> bool:
        """Check if any prediction magic numbers are already in open positions."""
        magics_pred = {pred.magic for pred in predictions}
        magics_pos = {pos.magic for pos in positions}

        return any(magic in magics_pos for magic in magics_pred)

    @staticmethod
    def all_predictions_valid(predictions: List[PredictionData], current_date: date = None) -> bool:
        """
        Check if all predictions are still valid (not expired) based on the current date.
        
        Args:
            predictions: List of PredictionData objects to check
            current_date: The date to check against. If None, uses today's date.
            
        Returns:
            True if ALL predictions are still valid (current_date < last_training_day + n_trading_days)
            False if ANY prediction has expired
        """
        if current_date is None:
            current_date = date.today()
        
        for prediction in predictions:
            # Calculate the target date (last_training_day + n_trading_days)
            target_date = calculate_trading_day(
                prediction.last_training_day, 
                prediction.n_trading_days, 
                market='NYSE'
            )
            
            # If current_date >= target_date, the prediction is expired
            if current_date >= target_date:
                return False
        
        return True