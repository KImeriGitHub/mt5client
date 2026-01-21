#!/usr/bin/env python3
"""Cancel positions for old predictions that are no longer in the latest prediction set."""

import argparse
import json
import datetime as dt
from pathlib import Path
from datetime import date
import time

from src.infra.BudgetMgmt import BudgetMgmt
from src.infra.PositionData import PositionData
from src.infra.PredictionData import PredictionData
from src.infra.PredictionClient import PredictionClient
from src.infra.PositionClient import PositionClient
from src.infra.mtBase import mtBase
from src.infra.TradingConfig import TradingConfig

from src.logging_utils import setup_console_and_file_logging
from src.place_order import place_order_req
from src.finalize_positions_to_close import get_positions_to_close

import logging

from src.time_scheduler import parse_and_sleep_until_time

# Global logger setup - will be reconfigured in main()
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cancel positions for old predictions that are no longer active."
    )
    parser.add_argument(
        "--account",
        required=True,
        help="Account key from the credentials YAML (e.g., 'mt5demo_acc_usd').",
    )
    parser.add_argument(
        "--group",
        default="mt5",
        help="Optional group filter (matches prediction_<group>_*.json).",
    )
    parser.add_argument(
        "--config",
        default="config/trading_config_prod.yaml",
        help="Path to trading configuration file.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="If specified, positions will be actually closed. By default, runs in dry-run mode.",
    )
    parser.add_argument(
        "--place_time",
        help="Time to start placing orders in HH:MM format (e.g., '14:30'). If not provided, orders are placed immediately.",
    )
    return parser.parse_args()


def main(args=None, dry_run_suffix="", setup_logs=True) -> list[dict]:
    if args is None:
        args = parse_args()
    
    config = TradingConfig(args.config)
    config.validate()

    # Set up logging based on configuration (only if requested)
    if setup_logs:
        log_file_path = setup_console_and_file_logging(
            log_dir=config.log_dir,
            log_level=config.log_level,
            log_format=config.log_format,
            log_datefmt=config.log_datefmt,
            script_name="cancel_old_positions"
        )

    predictions_dir = Path(config.predictions_dir)

    base = mtBase(args.account, config.credentials_path, config.mt5_config_path)
    logger.info("Initializing MetaTrader 5 connection...")
    base.mt5_init()
    # Wait for the user to press the Algo-Trading button
    wait_seconds = 5
    logger.info("="*20)
    logger.info(f"Waiting {wait_seconds} seconds for Algo-Trading to be enabled...")
    logger.info("="*20)
    time.sleep(wait_seconds)

    pred_client = PredictionClient(base=base, predictions_dir=predictions_dir)
    pos_client = PositionClient(base=base)
    balance_manager = BudgetMgmt(
        base, 
        per_day_divisor=config.per_day_divisor, 
        max_budget_discrepancy=config.max_budget_discrepancy
    )

    
    ########################
    ### LOAD DATA        ###
    ########################
    logger.info("Loading current positions...")
    all_positions: list[PositionData] = pos_client.get_positions()
    
    logger.info("Loading latest predictions...")
    all_predictions: list[PredictionData] = pred_client.load_predictions(args.group)

    # Get current date
    current_date = date.today()
    logger.info(f"Current date: {current_date}")
    
    ########################
    ### IDENTIFY TARGETS ###
    ########################
    logger.info("Identifying positions to close...")
    positions_to_close: list[PositionData] = get_positions_to_close(all_positions, all_predictions, balance_manager, config.n_expiry_tdays)
    pos_client.log_positions(positions_to_close)

    # Sanity checks
    if not positions_to_close or len(all_positions) == 0 or len(all_predictions) == 0:
        logger.error("Abort: No positions or predictions found - nothing to evaluate for closure")
        return []
    sum_pos_price = sum(pos.price_current for pos in positions_to_close)
    free_margin = balance_manager.free_margin
    daily_budget = balance_manager.calc_daily_budget()
    if sum_pos_price + free_margin < daily_budget:
        logger.error("Abort: Insufficient budget to close positions")
        return []
    
    # Log summary statistics
    positions_with_magic = [pos for pos in all_positions if pos.magic]
    logger.info(f"Total positions: {len(all_positions)}, "
               f"Positions with magic numbers: {len(positions_with_magic)}, "
               f"Total predictions: {len(all_predictions)}")

    logger.info(f"Found {len(positions_to_close)} positions to close:")
    pos_client.log_positions(positions_to_close)

    ##################################
    ### Waiting for placement time ###
    ##################################
    parse_and_sleep_until_time(args.place_time)
    
    #######################
    ### CLOSE POSITIONS ###
    #######################
    logger.info("Processing position closures...")
    
    start_time = dt.datetime.now(dt.timezone.utc)
    closed_positions: list[PositionData] = []
    
    for position in positions_to_close:
        if dt.datetime.now(dt.timezone.utc) - start_time > config.max_working_duration:
            logger.error("Max working duration exceeded. Stopping position closure.")
            break
        
        # Get the close position request
        close_request = pos_client.close_position_request(position)
        
        logger.info(f"Closing position {position.ticket} for symbol {position.symbol}")
        
        if args.apply:
            status, msg = place_order_req(close_request, base, is_dry_run=False)
            if status == 0:
                logger.info(msg)
                closed_positions.append(position)
            else:
                logger.warning(msg)
                _, le = base.last_error()
                logger.warning(f"MetaTrader5 error code: {le}")
        else:
            status, msg = place_order_req(close_request, base, is_dry_run=True)
            if status == 0:
                logger.info(msg)
                closed_positions.append(position)
            else:
                logger.warning(msg)
                _, le = base.last_error()
                logger.warning(f"MetaTrader5 error code: {le}")

    ################
    ### FINALIZE ###
    ################
    logger.info("Finalizing...")
    
    if not closed_positions:
        logger.info("No positions were closed.")
    else:
        logger.info(f"Processed {len(closed_positions)} position closures.")
        pos_client.log_positions(closed_positions)
    
    # Save results to JSON file
    formatted_date = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_prefix = "closed_positions" if args.apply else "dry_run_closures"
    suffix = f"_{dry_run_suffix}" if dry_run_suffix else ""

    results_path = Path(config.artifacts_dir) / f"{file_prefix}_{formatted_date}{suffix}.json"
    with results_path.open("w", encoding="utf-8") as f:
        json.dump([pos.to_dict() for pos in closed_positions], f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to {results_path}")
    
    # Log account information before and after refresh
    logger.info(f"Account info before refresh - Free margin: {balance_manager.free_margin:.2f}, Total capital: {balance_manager.total_capital:.2f}")
    balance_manager.refresh()
    logger.info(f"Account info after refresh - Free margin: {balance_manager.free_margin:.2f}, Total capital: {balance_manager.total_capital:.2f}")
    
    return closed_positions

if __name__ == "__main__":
    main()