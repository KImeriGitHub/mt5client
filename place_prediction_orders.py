#!/usr/bin/env python3
"""Place market orders for the newest prediction set."""

import argparse
import datetime
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from collections import deque
import polars as pl
import MetaTrader5 as mt5

from src.PredictionClient import PredictionClient
from src.MarketAccessClient import MarketAccessClient
from src.mtBase import mtBase

import logging
formatted_date = datetime.datetime.now().strftime("%d%b%y_%H%M")
logging.basicConfig(
    filename=f'logs/place_prediction_orders_{formatted_date}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt="%Y-%m-%d %H:%M"
)
logger = logging.getLogger(__name__)

MAX_WORKING_DURATION = datetime.timedelta(minutes=30)
CREDENTIALS_PATH = "secrets/mt5_acc_cred.yaml"
CONFIG_PATH = "secrets/mt5_config.ini"
PREDICTION_DIR = "predictions"

# On how many days should the equity be divided at most,
# if there is a lot of free margin on hand
PER_DAY_DIVISOR = 3
MAX_WAIT_SECONDS = 5
MAX_TICK_AGE_SECONDS = 5
CHECK_INTERVAL_SECONDS = 60

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Place market orders for symbols in the latest prediction batch."
    )
    parser.add_argument(
        "--account",
        required=True,
        help="Account key from the credentials YAML (e.g., 'mt5demo_acc').",
    )
    parser.add_argument(
        "--group",
        default=None,
        help="Optional group filter (matches prediction_<group>_*.json).",
    )
    parser.add_argument(
        "--log-subdir",
        default="orders",
        help="Subdirectory inside the predictions directory for execution logs.",
    )
    return parser.parse_args()


def compute_max_nominal(account_info, symbols_remaining: int) -> float:
    remaining = max(symbols_remaining, 1)

    available = getattr(account_info, "margin_free", None)
    if available is None:
        logger.warning("Warning: margin_free is unavailable; falling back to equity.")
        available = getattr(account_info, "equity", None)
    if available is None or available <= 0:
        raise RuntimeError("Account has no available cash information.")

    total_capital = getattr(account_info, "equity", None)
    if total_capital is None:
        total_capital = getattr(account_info, "balance", None)

    per_symbol = available / remaining
    if total_capital:
        per_symbol = min(per_symbol, total_capital / PER_DAY_DIVISOR)

    return per_symbol

def main() -> int:
    args = parse_args()
    predictions_dir = Path(PREDICTION_DIR)

    base = mtBase(args.account, CREDENTIALS_PATH, CONFIG_PATH)
    client = PredictionClient(base=base, predictions_dir=predictions_dir)


    ########################
    ### INIT PREDICTIONS ###
    ########################
    client.load_predictions(args.group)
    predictions_df = client.predictions_to_frame()
    if predictions_df.is_empty():
        logger.info("No predictions found.")
        return 1

    to_trade_df = client.latest_predictions(predictions_df)
    if to_trade_df.is_empty():
        logger.info("No predictions remain after filtering for the newest training day.")
        return 1
    

    ###########################
    ### INIT MT5 CONNECTION ###
    ###########################
    base.mt5_init()
    account_info = base.get_account_info()
    if account_info is None:
        logger.error("Failed to connect to MetaTrader 5. Check credentials and terminal path.")
        return 1
    
    try:
        positions_df = base.get_position_df()
    except RuntimeError as exc:
        logger.warning(f"Warning: could not retrieve positions ({exc}). Assuming no open positions.")
        positions_df = pl.DataFrame()


    ####################
    ### PREPARATIONS ###
    ####################
    market_access = MarketAccessClient(base)

    # Check that no prediction is already made
    if not positions_df.is_empty():
        if to_trade_df['magic'].is_in(positions_df['magic']).any():
            logger.info("All/some predictions already have open positions. No new orders to place.")
            return 1

    # Check all symbols are unique
    if to_trade_df['symbol'].n_unique() != to_trade_df.height:
        logger.error("Error: Duplicate symbols found in predictions. Aborting order placement.")
        return 1
    n_symbols = to_trade_df.height

    free_margin_per_symbol = compute_max_nominal(account_info, n_symbols)

    # Ensure required fields for order params:
    # If your DataFrame lacks 'buy_sell', derive it from score (>0 => BUY, else SELL).
    if 'buy_sell' not in to_trade_df.columns:
        to_trade_df = to_trade_df.with_columns(
            pl.when(pl.col('score') > 0).then(pl.lit('BUY')).otherwise(pl.lit('SELL')).alias('buy_sell')
        )

    # Fill defaults expected by to_market_order_params (symbol, max_nom_value, buy_sell are required)
    # (The helper enforces required keys: symbol, max_nom_value, buy_sell.)  # see PredictionClient
    toTrade_list = client.to_market_order_params(
        to_trade_df,
        defaults={
            "max_nom_value": float(free_margin_per_symbol),
            "buy_sell": "Buy",
        }
    )
    toTrade_queue = deque(toTrade_list)


    ####################
    ### PLACE ORDERS ###
    ####################
    return_code = 0

    def place_one(order: Dict[str, object]) -> int:
        sym = order["symbol"]
        # Wait for market access (guard MT5 calls)
        status = market_access.wait_for_market_access(
            symbol=sym,
            max_wait_seconds=MAX_WAIT_SECONDS,
            check_interval=CHECK_INTERVAL_SECONDS,
            max_tick_age_seconds=MAX_TICK_AGE_SECONDS,
        )

        if not status == 0:
            msg = f"market closed (status {status})"
            logger.info(f"Skipping {sym}: {msg}")
            return 1

        acct = base.get_account_info()
        if acct is None:
            msg = "account info unavailable before order placement"
            logger.error(f"Failed to place order for {order['symbol']}: {msg}")

        # Place the order (guard MT5 call)
        result = base.place_market_order(**order)

        if result is None:
            msg = "order helper returned None"
            logger.error(f"Order failed for {sym}: {msg}")
            return 1
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            msg = f"order failed with retcode {result.retcode}"
            logger.error(f"Order failed for {sym}: {msg}")
            return 1
        
        logger.info(f"Order placed for {sym}: {result}")
        return 0

    return_code = 0
    start_time = datetime.now(timezone.utc)
    while toTrade_queue:
        order = toTrade_queue.popleft()
        rc = place_one(order)
        if rc != 0:
            toTrade_queue.append(order)  # Re-queue failed order
        else:
            logger.info(f"Order placed successfully for {order['symbol']}")

        if datetime.now(timezone.utc) - start_time > MAX_WORKING_DURATION:
            logger.error("Max working duration exceeded. Stopping order placement.")
            return_code = 1
            break

    return return_code

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
