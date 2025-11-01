from typing import List

from .infra.PositionData import PositionData
from .infra.PredictionData import PredictionData


class Checks:
    def __init__(self):
        pass

    @staticmethod
    def preds_in_positions(predictions: List[PredictionData], positions: List[PositionData]) -> bool:
        """Check if any prediction magic numbers are already in open positions."""
        magics_pred = {pred.magic for pred in predictions}
        magics_pos = {pos.magic for pos in positions}

        return any(magic in magics_pos for magic in magics_pred)