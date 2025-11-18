"""
Prediction finalization module for trading system.

This module provides functions to process, filter, and finalize trading predictions
before order placement. It handles deduplication of predictions, budget calculations,
volume filtering, and volume divisor calculations to ensure trading constraints are met.

Key functions:
- Combine and deduplicate predictions
- Filter predictions based on volume constraints
- Calculate budget allocations
- Determine volume divisors for position sizing

Dependencies:
- MetaTrader 5 integration for symbol information
- Budget management for capital allocation
- Prediction data structures for trade signals
"""

from typing import Counter, List, Tuple
import math

from .infra import mtBase
from .infra.BudgetMgmt import BudgetMgmt
from .infra.PredictionData import PredictionData
from .infra.PredictionClient import PredictionClient

import logging
logger = logging.getLogger(__name__)

def _combine_predictions(predictions: List[PredictionData]) -> Tuple[List[PredictionData], List[int]]:
    """
    Combine and deduplicate predictions based on unique trading characteristics.
    
    This function removes duplicate predictions that share the same symbol, last training day,
    and number of trading days. Each unique prediction is retained with a weight indicating
    how many duplicates were combined.
    
    Args:
        predictions: List of PredictionData instances to process
        
    Returns:
        Tuple containing:
            - unique_predictions: List of unique PredictionData (preserves order of first appearance)
            - weights: List of integers indicating count of each unique prediction
            
    Note:
        Empty input returns empty lists for both predictions and weights.
    """
    if not predictions:
        return [], []

    # Create unique key function for prediction characteristics
    make_key = lambda p: (p.symbol, p.last_training_day, p.n_trading_days)
    
    # Count occurrences of each unique prediction combination
    counts = Counter(make_key(p) for p in predictions)

    # Track seen keys to maintain order and avoid duplicates
    seen = set()
    unique_predictions: List[PredictionData] = []
    weights: List[int] = []

    # Process predictions in order, keeping first occurrence of each unique key
    for p in predictions:
        k = make_key(p)
        if k not in seen:
            seen.add(k)
            unique_predictions.append(p)
            weights.append(counts[k])

    return unique_predictions, weights



def rm_small_volume_predictions(
        predictions: List[PredictionData],
        weights: List[int],
        budget_all: float,
        base: mtBase,
        max_budget_discrepancy: float
    ) -> Tuple[List[PredictionData], List[int]]:
    """
    Filter out predictions that cannot meet minimum volume or budget requirements.
    
    This function performs comprehensive filtering to remove predictions that:
    1. Have insufficient budget to meet the symbol's minimum volume requirements
    2. Result in normalized volumes below the minimum after vol_step adjustments
    3. Have volume discrepancies exceeding the maximum allowed budget variance
    
    The filtering process:
    - Calculates affordable volume based on allocated budget and symbol pricing
    - Validates against minimum volume requirements from MetaTrader 5
    - Normalizes volume to valid step increments
    - Checks final volume discrepancy against budget tolerance
    
    Args:
        predictions: List of PredictionData instances to filter
        weights: List of weights corresponding to each prediction (must match length)
        budget_all: Total budget available for all predictions
        base: mtBase instance for MetaTrader 5 operations and symbol information
        max_budget_discrepancy: Maximum allowed relative discrepancy between 
                               allocated budget and effective trade value
        
    Returns:
        Tuple containing:
            - Filtered list of PredictionData instances that meet all requirements
            - Corresponding list of weights for the filtered predictions
            
    Raises:
        ValueError: If predictions and weights lists have different lengths
        
    Note:
        Predictions with missing or invalid symbol information are automatically filtered out.
    """
    if not predictions or not weights:
        return [], []
    
    if len(predictions) != len(weights):
        raise ValueError("predictions and weights must have the same length")
    
    filtered_predictions = []
    filtered_weights = []
    
    # Calculate budget allocation per unit weight
    budget_per_unit = budget_all / sum(weights)
    
    # Process each prediction-weight pair for volume feasibility
    for pred, weight in zip(predictions, weights):
        budget = weight * budget_per_unit
        
        # Retrieve symbol specifications from MetaTrader 5
        symbol_info = base.get_symbol_info(pred.symbol, wait_sec=0.5)
        symbol_tick = base.get_symbol_price(pred.symbol, wait_sec=0.5)
        bid_price = symbol_tick.get("bid") if symbol_tick is not None else None
        
        # Extract critical trading parameters
        vol_min = symbol_info.get("volume_min")
        vol_step = symbol_info.get("volume_step")
        trade_contract_size = symbol_info.get("trade_contract_size")
        price = (bid_price if bid_price is not None and bid_price > 1e-5
                 else pred.last_close_price)
        
        # Calculate maximum volume affordable with allocated budget
        affordable_volume = budget / (price * trade_contract_size + 1e-9)  # Small epsilon to prevent division by zero
        
        # First filter: Check if we can meet minimum volume requirements
        if affordable_volume < vol_min:
            logger.info(f"Filtering out {pred.symbol}: affordable volume {affordable_volume:.6f} < vol_min {vol_min}")
            continue
        
        # Normalize volume to valid trading increments (must be multiple of vol_step)
        normalized_volume = (affordable_volume // vol_step) * vol_step
        
        # Second filter: Verify normalized volume still meets minimum after step adjustment
        if normalized_volume < vol_min:
            logger.info(f"Filtering out {pred.symbol}: normalized volume {normalized_volume:.6f} < vol_min {vol_min}")
            continue
        
        # Calculate actual notional value of the normalized trade
        effective_price_volume = normalized_volume * price * trade_contract_size
        
        # Third filter: Ensure effective trade value is within budget tolerance
        volume_discrepancy = abs(effective_price_volume - budget) / budget
        
        if volume_discrepancy > max_budget_discrepancy:
            logger.info(f"Filtering out {pred.symbol}: volume discrepancy {volume_discrepancy:.3f} > max allowed {max_budget_discrepancy}")
            continue
        
        # Prediction meets all volume and budget constraints
        filtered_predictions.append(pred)
        filtered_weights.append(weight)
    
    logger.info(f"Filtered predictions: {len(predictions)} -> {len(filtered_predictions)}")
    return filtered_predictions, filtered_weights

def divisors_for_max_volume(
        predictions: List[PredictionData], 
        budget_list: List[float], 
        base: mtBase,
        buffer_factor: float = 1.10) -> List[int]:
    """
    # NOTE! Only for equities for now!

    Calculate volume divisors to respect maximum volume constraints for each symbol.
    
    This function determines scaling factors (divisors) that ensure trading volumes
    don't exceed the broker's maximum allowed volume per symbol. When a prediction's
    affordable volume would exceed the maximum, the divisor scales down the position size.
    
    The calculation process:
    1. Calculate how much volume the budget could afford
    2. Apply a buffer factor to provide safety margin
    3. If buffered volume exceeds maximum, calculate required divisor
    4. Return divisor that brings volume within acceptable limits
    
    Args:
        predictions: List of PredictionData instances to process
        budget_list: List of budget allocations corresponding to each prediction
        base: mtBase instance for MetaTrader 5 operations and symbol information
        buffer_factor: Safety multiplier applied to volume calculations (default 1.10 = 10% buffer)
        
    Returns:
        List of integer divisors corresponding to each prediction:
            - 1 = no scaling needed (volume within limits)
            - >1 = position size should be divided by this factor
            
    Raises:
        ValueError: If predictions and budget_list have different lengths
        RuntimeError: If symbol information or prediction data is invalid
        
    Note:
        Buffer factor helps prevent edge cases where volume calculations are close to limits.
        Divisors are always >= 1 to ensure valid scaling.
    """

    if len(predictions) != len(budget_list):
        raise ValueError("predictions and budget_list must have the same length")

    divisors: List[int] = []
    
    # Process each prediction-budget pair to determine volume scaling
    for pred, budget in zip(predictions, budget_list):
        # Retrieve symbol specifications from MetaTrader 5
        info = base.get_symbol_info(pred.symbol, wait_sec=0.5) or {}
        max_vol = info.get("volume_max")
        trade_contract_size = info.get("trade_contract_size")
        symbol_tick = base.get_symbol_price(pred.symbol, wait_sec=0.5)
        bid_price = symbol_tick.get("bid") if symbol_tick is not None else None
        price = (bid_price if bid_price is not None and bid_price > 1e-5
                 else pred.last_close_price)
        
        # Calculate volume that could be purchased with full budget allocation
        affordable_vol = budget / (price * trade_contract_size)

        # Check if volume with buffer is within maximum limits (no scaling needed)
        if affordable_vol * buffer_factor <= max_vol:
            divisors.append(1)
            continue

        # Calculate required divisor to bring volume within limits
        # Use ceiling to ensure we stay under the maximum even after rounding
        div = math.ceil((affordable_vol * buffer_factor) / max_vol)
        divisors.append(max(div, 1))  # Ensure divisor is at least 1

    return divisors

def finalize_predictions(
        preds: list[PredictionData],
        budget_mgmt: BudgetMgmt,
        pred_client: PredictionClient,
        base: mtBase,
    ) -> Tuple[List[PredictionData], List[float], List[int]]:
    """
    Complete prediction processing pipeline for trading system.
    
    This is the main orchestration function that processes raw predictions through
    multiple filtering and optimization stages to produce trade-ready signals with
    appropriate budget allocations and position sizing.
    
    Processing pipeline:
    1. Calculate total available trading budget
    2. Filter to latest predictions only
    3. Combine and deduplicate predictions with weights
    4. Remove predictions with insufficient volume or budget mismatches
    5. Recalculate budget allocations for filtered predictions
    6. Determine volume divisors to respect maximum volume constraints
    
    Args:
        preds: List of raw PredictionData instances containing trade signals
        budget_mgmt: BudgetMgmt instance for capital allocation and risk management
        pred_client: PredictionClient instance for prediction filtering operations
        base: mtBase instance for MetaTrader 5 operations and symbol information
        
    Returns:
        Tuple containing three synchronized lists:
            - filtered_predictions: PredictionData instances ready for trading
            - budget_list: Budget allocation for each prediction (in account currency)
            - volume_divisor_list: Position sizing divisors for each prediction
            
    Note:
        All three returned lists have the same length and corresponding indices.
        Empty input or complete filtering results in empty lists for all outputs.
    """
    # Handle empty input gracefully
    if not preds:
        return [], [], []
    
    # Step 1: Calculate total available trading budget
    budget_all = budget_mgmt.calc_daily_budget()

    # Step 2: Filter to most recent predictions only
    preds_latest = pred_client.latest_predictions(preds)

    # Step 3: Combine duplicate predictions and calculate weights
    preds_unique, weights = _combine_predictions(preds_latest)

    # Step 4: Filter out predictions with volume or budget constraints
    preds_wo_small_vol, weights_wo_small_vol = rm_small_volume_predictions(
        preds_unique, weights, budget_all, base, budget_mgmt.max_budget_discrepancy
    )

    if not preds_wo_small_vol or not weights_wo_small_vol:
        return [], [], []

    # Step 5: Recalculate budget allocations based on filtered predictions
    budget_per_unit = budget_all / sum(weights_wo_small_vol) - 1e-9
    budget_list = [weight * budget_per_unit for weight in weights_wo_small_vol]

    # Step 6: Calculate volume divisors to respect maximum volume constraints
    volumedivisor_list = divisors_for_max_volume(preds_wo_small_vol, budget_list, base)

    return preds_wo_small_vol, budget_list, volumedivisor_list