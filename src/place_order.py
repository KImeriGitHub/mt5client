import MetaTrader5 as mt5

from src.infra.OrderClient import OrderClient
from src.infra.OrderData import OrderData
from src.infra.mtBase import mtBase

import logging
logger = logging.getLogger(__name__)

def place_order(order: OrderData, order_client: OrderClient, base: mtBase, is_dry_run: bool = True) -> tuple[int, str]:
    sym = order.symbol
    req = order_client.to_request_dict(order)
            
    # Check order validity
    res_check: mt5.OrderCheckResult = base.order_check(req)
    if res_check is None:
        msg = f"Order check returned None for {sym}"
        return (1, msg)
    if res_check.retcode != 0:
        msg = f"Order check failed for {sym}: {res_check}"
        msg = "DRY RUN: " + msg if is_dry_run else msg
        return (1, msg)
    
    if is_dry_run:
        msg = f"DRY RUN: Order check passed for {sym}."
        return (0, msg)

    #Place Order
    logger.info(f"Placing order for {sym}...")
    res_placing = base.place_market_order(req)
    if res_placing is None:
        msg = f"Order placement returned None for {sym}"
        return (1, (msg))
    
    result_code = res_placing._asdict().get("retcode", -1)
    if result_code == -1:
        msg = f"Order placement returned unknown result for {sym}: {res_placing}"
        return (1, msg)
    if result_code != mt5.TRADE_RETCODE_DONE:
        msg = f"Order placement failed for {sym}: {res_placing}"
        return (1, msg)

    msg = f"Order placed successfully for {sym}: {res_placing}"
    return (0, msg)