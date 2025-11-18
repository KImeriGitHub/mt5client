import logging
from datetime import date, timedelta
from typing import Dict, List
from src.infra.BudgetMgmt import BudgetMgmt
from src.infra.PositionData import PositionData
from src.infra.PredictionData import PredictionData
from src.common import calculate_trading_day

logger = logging.getLogger(__name__)


def _create_prediction_lookup(predictions: list[PredictionData]) -> Dict[int, PredictionData]:
    """Create a mapping from magic number to prediction data for quick lookup."""
    return {pred.magic: pred for pred in predictions}


def _is_position_expired(position: PositionData, prediction: PredictionData | None, today: date, n_expiry_tdays: int = 0) -> bool:
    """
    Check if a position has expired based on its prediction data.
    
    A position is considered expired when today is on or after the last day of the 
    training period + n_trading_days. This means when today reaches the final day
    of the prediction window, the position is thought of as expired.
    
    Args:
        position: The position to check
        prediction: The corresponding prediction data (or None if not found)
        today: Current date
        n_expiry_tdays: Additional trading days to consider for expiry (0 denotes no expiry)
        
    Returns:
        True if the position has expired, False otherwise
    """
    buy_date = position.time.date()
    n_forward_days = n_expiry_tdays

    if prediction is not None:
        n_trading_days = prediction.n_trading_days
        if n_trading_days is None or n_trading_days <= 0:
            raise ValueError(f"Invalid n_trading_days ({n_trading_days}) for prediction with magic {prediction.magic}")
        
        buy_date = prediction.last_training_day
        n_forward_days = n_trading_days

    try:
        expiration_date = calculate_trading_day(
            buy_date,
            n_forward_days
        )
        return today >= expiration_date
    except Exception as e:
        raise RuntimeError(f"Error calculating expiration date for position {position.ticket} "
                           f"with prediction magic {prediction.magic}: {e}") from e


def _find_expired_positions(
        positions: list[PositionData], 
        prediction_by_magic: Dict[int, PredictionData],
        today: date,
        n_expiry_tdays: int = 0
    ) -> list[PositionData]:
    """
    Find all positions that have expired based on their prediction data.
    
    Args:
        positions: List of all positions
        prediction_by_magic: Mapping from magic number to prediction data
        today: Current date
        n_expiry_tdays: Additional trading days to consider for expiry (0 denotes no expiry)
        
    Returns:
        List of expired positions
    """
    expired_positions = []
    
    for position in positions:
        # Skip positions without magic numbers (not from our prediction system)
        if not position.magic:
            logger.warning(f"Position {position.ticket} has no magic number - skipping.")
            continue
            
        # Find corresponding prediction data by magic number
        prediction = prediction_by_magic.get(position.magic)
            
        # Check if position has expired
        if _is_position_expired(position, prediction, today, n_expiry_tdays):
            logger.info(f"Position {position.ticket} for symbol {position.symbol} has expired")
            expired_positions.append(position)
        else:
            logger.debug(f"Position {position.ticket} for symbol {position.symbol} is still active")
    
    return expired_positions


def _calculate_positions_value(positions: list[PositionData]) -> float:
    """Calculate the total value of a list of positions."""
    return sum(abs(pos.price_current * pos.volume) for pos in positions)


def _get_oldest_positions(positions: list[PositionData], exclude: list[PositionData]) -> list[PositionData]:
    """
    Get positions sorted by age (oldest first), excluding specified positions.
    
    Args:
        positions: All positions to consider
        exclude: Positions to exclude from the result
        
    Returns:
        List of positions sorted by age, oldest first
    """
    exclude_set = set(exclude)
    non_excluded_positions = [
        pos for pos in positions 
            if pos.magic and pos not in exclude_set
    ]
    return sorted(non_excluded_positions, key=lambda pos: pos.time)


def _add_positions_until_budget_met(
        expired_positions: list[PositionData],
        available_positions: list[PositionData],
        available_free_margin: float,
        required_budget: float
    ) -> list[PositionData]:
    """
    Add positions from available_positions until the budget requirement is met.
    
    Args:
        expired_positions: Already identified positions to close
        available_positions: Additional positions that can be closed (sorted by priority)
        available_free_margin: Current available free margin
        required_budget: Target budget requirement
        
    Returns:
        Combined list of positions to close
    """
    # Validate that available_positions are sorted by age (oldest first)
    if len(available_positions) > 1:
        for i in range(1, len(available_positions)):
            if available_positions[i].time < available_positions[i-1].time:
                logger.warning("Available positions are not sorted by age - sorting now")
                available_positions = sorted(available_positions, key=lambda pos: pos.time)
                break
    
    positions_to_close = expired_positions.copy()
    current_value = _calculate_positions_value(expired_positions)
    
    for position in available_positions:
        position_value = abs(position.price_current * position.volume)
        current_value += position_value
        positions_to_close.append(position)
        
        total_with_current = available_free_margin + current_value
        if total_with_current >= required_budget:
            logger.info(f"Added position {position.ticket} - now have sufficient budget: {total_with_current:.2f}")
            break
    
    return positions_to_close


def get_positions_to_close(
        positions: list[PositionData], 
        predictions: list[PredictionData], 
        budget_mgmt: BudgetMgmt,
        n_expiry_tdays: int,
        budget_threshold: float = 0.03
    ) -> list[PositionData]:
    """
    Identify positions that should be closed based on the criteria:
    1. Positions whose corresponding PredictionData has expired (based on n_trading_days and last_training_day)
    2. If free margin + value of expired positions is below daily budget (+ threshold), close oldest positions until threshold is met
    
    Args:
        positions: List of PositionData objects
        predictions: List of latest PredictionData objects
        budget_mgmt: BudgetMgmt object for budget calculations
        n_expiry_tdays: Number of trading days for position expiry
        budget_threshold: Threshold percentage to add to daily budget (default: 0.05 = 5%)
        
    Returns:
        List of PositionData objects to close
    """
    # Get budget information
    daily_budget = budget_mgmt.calc_daily_budget()
    available_free_margin = budget_mgmt.free_margin
    required_budget = daily_budget * (1 + budget_threshold)
    
    # Create prediction lookup and find expired positions
    prediction_by_magic: Dict[int, PredictionData] = _create_prediction_lookup(predictions)
    today = date.today()
    expired_positions: List[PositionData] = _find_expired_positions(positions, prediction_by_magic, today, n_expiry_tdays)
    
    # Calculate value of expired positions
    expired_positions_value = _calculate_positions_value(expired_positions)
    total_available = available_free_margin + expired_positions_value
    
    # Check if expired positions alone meet budget requirement
    if total_available >= required_budget:
        logger.info(f"Available margin ({available_free_margin:.2f}) + expired positions value ({expired_positions_value:.2f}) "
                   f"= {total_available:.2f} meets required budget {required_budget:.2f}")
        return expired_positions
    
    # Need to close additional positions to meet budget requirements
    logger.info(f"Need additional budget: {required_budget - total_available:.2f}")
    
    # Get oldest non-expired positions and add them until budget is met
    timesorted_nonexpired_positions = _get_oldest_positions(positions, expired_positions)

    positions_to_close = _add_positions_until_budget_met(
        expired_positions,
        timesorted_nonexpired_positions,
        available_free_margin,
        required_budget
    )
    
    return positions_to_close