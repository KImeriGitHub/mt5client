#!/usr/bin/env python3
"""Place market orders for the newest prediction set."""

import argparse
import json
import datetime as dt
from pathlib import Path
from collections import deque
import time

from src.infra.OrderClient import OrderClient
from src.infra.OrderData import OrderData
from src.infra.PredictionData import PredictionData
from src.infra.PredictionClient import PredictionClient
from src.infra.PositionClient import PositionClient
from src.infra.MarketAccess import MarketAccess
from src.infra.BudgetMgmt import BudgetMgmt
from src.infra.mtBase import mtBase
from src.infra.TradingConfig import TradingConfig
from src.Checks import Checks

from src.finalize_predictions import finalize_predictions
from src.logging_utils import setup_logging
from src.place_order import place_order
from src.prediction_to_orders import prediction_to_orders

import logging

# Global logger setup - will be reconfigured in main()
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Place market orders for symbols in the latest prediction batch."
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
        help="If specified, orders will be actually placed. By default, runs in dry-run mode.",
    )
    return parser.parse_args()


def main(args=None, dry_run_suffix="", setup_logs=True) -> list[OrderData]:
    if args is None:
        args = parse_args()
    
    config = TradingConfig(args.config)
    config.validate()

    # Set up logging based on configuration (only if requested)
    if setup_logs:
        log_file_path = setup_logging(
            log_dir=config.log_dir,
            log_level=config.log_level,
            log_format=config.log_format,
            log_datefmt=config.log_datefmt,
            script_name="place_prediction_orders"
        )

    predictions_dir = Path(config.predictions_dir)

    base = mtBase(args.account, config.credentials_path, config.mt5_config_path)
    base.mt5_init()
    pred_client = PredictionClient(base=base, predictions_dir=predictions_dir)
    pos_client = PositionClient(base=base)
    order_client = OrderClient(base=base)
    balance_manager = BudgetMgmt(
        base, 
        per_day_divisor=config.per_day_divisor, 
        max_budget_discrepancy=config.max_budget_discrepancy
    )

    ###########################
    ### INIT MT5 CONNECTION ###
    ###########################
    logger.info("Initializing MetaTrader 5 connection and loading positions...")
    base.mt5_init()
    
    ########################
    ### INIT PREDICTIONS ###
    ########################
    logger.info("Loading predictions...")
    predictions_list_all = pred_client.load_predictions(args.group)
    predictions_list, budget_list, volumedivisor_list = finalize_predictions(
        predictions_list_all, 
        budget_mgmt=balance_manager, 
        pred_client=pred_client,
        base=base,
    )

    # Sanity checks before placing orders
    pos_all = pos_client.get_positions()
    if Checks.preds_in_positions(predictions_list, pos_all):
        logger.error("Aborting: Some predictions already have open positions.")
        return
    if sum(budget_list) >= balance_manager.free_margin:
        logger.error("Aborting: Insufficient free margin for placing orders.")
        return
    if any(div <= 0 for div in volumedivisor_list):
        logger.error("Aborting: Invalid volume divisors detected.")
        return
    
    pred_client.log_predictions(predictions_list)
    
    pending_trade_queue = deque(zip(
        predictions_list, budget_list, volumedivisor_list, strict=True
    ))


    ####################
    ### PLACE ORDERS ###
    ####################
    logger.info(f"Placing orders for {len(predictions_list)} symbols...")

    start_time = dt.datetime.now(dt.timezone.utc)
    placed_orders: list[OrderData] = []
    while len(pending_trade_queue) != 0:
        if dt.datetime.now(dt.timezone.utc) - start_time > config.max_working_duration:
            logger.error("Max working duration exceeded. Stopping order placement.")
            break

        (pred, budget, volumedivisor) = pending_trade_queue.popleft()

        # Create orders from prediction
        orders: list[OrderData] = prediction_to_orders(
            pred=pred,
            budget=budget,
            vol_divisor=volumedivisor,
            base=base,
        )

        # Place each order
        logger.info(f"Placing orders for symbol: {pred.symbol}")
        
        for order in orders:
            order_client.log_orders(order, indent=2)

            if args.apply:
                status, msg = place_order(order, order_client, base, is_dry_run=False)
                if status == 0:
                    logger.info(msg)
                    placed_orders.append(order)
                else:
                    logger.warning(msg)
                    _, le = base.last_error()
                    logger.warning(f"MetaTrader5 error code: {le}")
            else:
                status, msg = place_order(order, order_client, base, is_dry_run=True)
                if status == 0:
                    logger.info(msg)
                    placed_orders.append(order)
                else:
                    logger.warning(msg)
                    _, le = base.last_error()
                    logger.warning(f"MetaTrader5 error code: {le}")

    ################
    ### FINALIZE ###
    ################
    logger.info("Finalizing...")
    
    # Log placed orders
    if not placed_orders or len(placed_orders) == 0:
        logger.info("No orders were placed successfully.")
    else:
        logger.info(f"Placed {len(placed_orders)} orders successfully.")
        for order in placed_orders:
            logger.info("Placed Order:\n %s", json.dumps(order.to_dict(), indent=2))

    # Save placed orders to JSON file
    formatted_date = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_prefix = "orders" if args.apply else "dry_run_orders"
    suffix = f"_{dry_run_suffix}" if dry_run_suffix else ""

    placed_orders_path = Path(config.artifacts_dir) / f"{file_prefix}_{formatted_date}{suffix}.json"
    with placed_orders_path.open("w", encoding="utf-8") as f:
        json.dump([order.to_dict() for order in placed_orders], f, indent=2, ensure_ascii=False)
    
    return placed_orders

if __name__ == "__main__":
    main()
